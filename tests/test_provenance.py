"""E2 provenance tests: every answer is stored as PROV-O and SHACL-checked."""
import pytest

pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")

from rdflib import URIRef
from rdflib.namespace import RDF

from coursegraph.answer_service import Answer, AnswerService
from coursegraph.graph_store import CG, GraphStore
from coursegraph.provenance import PROV, ProvenanceError, ProvenanceRecorder
from coursegraph.retriever import HybridRetriever


class FakeLLM:
    model = "qwen2.5:3b"

    def generate(self, prompt, system):
        return "This page explains the topic [1]."


@pytest.fixture
def store(tmp_path, sample_pdf, fake_embedder):
    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    store.validate_graph = lambda _graph: (True, "stub: E1 SHACL is tested in E1 tests")
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="lesson.pdf", course_id="SEN5016",
                     embedder=fake_embedder)
    return store


def _answer(store, fake_embedder):
    retriever = HybridRetriever(store, fake_embedder, min_similarity=0.0)
    return AnswerService(retriever, FakeLLM()).answer("What is on this page?", "SEN5016")


def test_every_answer_is_traceable_to_its_sources(store, fake_embedder):
    graph_before = store.graph_path.read_bytes()
    answer = _answer(store, fake_embedder)
    recorder = ProvenanceRecorder(store)

    answer_uri = URIRef(recorder.record(answer))
    g = recorder.load()

    assert (answer_uri, RDF.type, CG.Answer) in g
    assert g.value(answer_uri, CG.covered).toPython() is True
    generation = g.value(answer_uri, PROV.wasGeneratedBy)
    assert (generation, RDF.type, CG.AnswerGeneration) in g

    question = g.value(answer_uri, CG.answersQuestion)
    assert str(g.value(question, CG.questionText)) == "What is on this page?"
    assert (generation, PROV.used, question) in g

    cited_chunks = {URIRef(c["chunk_uri"]) for c in answer.citations}
    assert cited_chunks and cited_chunks <= set(g.objects(generation, PROV.used))
    model = g.value(generation, PROV.wasAssociatedWith)
    assert str(g.value(model, CG.modelName)) == "qwen2.5:3b"

    citations = list(g.objects(answer_uri, CG.hasCitation))
    assert len(citations) == len(answer.citations) <= 3
    assert recorder.path.name == "provenance.ttl"
    assert store.graph_path.read_bytes() == graph_before  # document graph is not rewritten


def test_no_source_reply_is_recorded_without_citations(store):
    recorder = ProvenanceRecorder(store)
    answer = Answer("Explain quantum physics", "SEN5016",
                    "No source was found in the uploaded documents for this question.",
                    covered=False, model="qwen2.5:3b", time_ms=12)

    answer_uri = URIRef(recorder.record(answer))
    g = recorder.load()

    assert g.value(answer_uri, CG.covered).toPython() is False
    assert list(g.objects(answer_uri, CG.hasCitation)) == []


def test_citation_to_unknown_chunk_is_rejected(store, fake_embedder):
    answer = _answer(store, fake_embedder)
    answer.citations[0]["chunk_uri"] = "https://coursegraph.local/resource/chunk/does-not-exist"
    recorder = ProvenanceRecorder(store)

    with pytest.raises(ProvenanceError, match="SHACL"):
        recorder.record(answer)
    assert not recorder.path.exists()


def test_more_than_three_citations_are_rejected(store, fake_embedder):
    answer = _answer(store, fake_embedder)
    base = answer.citations[0]
    answer.citations = [dict(base, number=n) for n in range(1, 5)]

    with pytest.raises(ProvenanceError):
        ProvenanceRecorder(store).record(answer)


def test_answers_accumulate_in_the_provenance_file(store, fake_embedder):
    recorder = ProvenanceRecorder(store)
    recorder.record(_answer(store, fake_embedder))
    recorder.record(_answer(store, fake_embedder))

    assert recorder.answer_count() == 2
    assert ProvenanceRecorder(store).answer_count() == 2  # survives a restart
