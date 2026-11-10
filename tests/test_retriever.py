"""E2 retriever tests, named after the proposal stories (Definition of Done)."""
import re

import pytest

from coursegraph.retriever import HybridRetriever

VOCAB = ["normal", "form", "fourier", "transform", "sql", "python"]


class KeywordEmbedder:
    """Bag-of-words vectors: deterministic and offline, enough to test ranking."""

    def encode(self, texts):
        vectors = []
        for text in texts:
            words = re.findall(r"[a-z]+", text.lower())
            vectors.append([float(words.count(word)) for word in VOCAB])
        return vectors


def _chunk(course, filename, page, text, embedder=KeywordEmbedder()):
    return {
        "course_id": course,
        "document_uri": f"https://coursegraph.local/resource/document/{course}-{filename}",
        "filename": filename,
        "page_number": page,
        "chunk_uri": f"https://coursegraph.local/resource/chunk/{course}-{filename}/{page}/0",
        "chunk_index": 0,
        "text": text,
        "embedding": embedder.encode([text])[0],
        "topics": ["Genel"],
    }


class StubStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def get_course_chunks(self, course_id, *, topic=None):
        self.calls.append((course_id, topic))
        return [c for c in self.chunks if c["course_id"] == course_id]


CHUNKS = [
    _chunk("COM3001", "databases.pdf", 4, "SQL select queries and joins"),
    _chunk("COM3001", "databases.pdf", 7, "third normal form: a normal form without transitive dependency"),
    _chunk("COM3001", "databases.pdf", 8, "normal form with sql examples"),
    _chunk("COM3001", "databases.pdf", 9, "python sql connector"),
    _chunk("SEN5016", "architecture.pdf", 2, "normal form normal form normal form"),
    _chunk("EE2001", "signals.pdf", 5, "fourier transform properties"),
]


def test_an_answer_that_cites_the_slides_it_comes_from():
    retriever = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), min_similarity=0.3)
    result = retriever.retrieve("What is third normal form?", "COM3001")

    assert result.covered
    assert len(result.hits) <= 3
    assert result.hits[0].page_number == 7  # the slide that explains 3NF
    assert result.hits[0].citation_label() == "databases.pdf, p. 7"
    scores = [hit.score for hit in result.hits]
    assert scores == sorted(scores, reverse=True)


def test_the_assistant_says_when_my_documents_do_not_cover_a_question():
    retriever = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), min_similarity=0.3)
    result = retriever.retrieve("Explain the Fourier transform", "COM3001")

    assert not result.covered
    assert result.hits == []
    assert result.candidate_count == 4


def test_to_limit_answers_to_one_course():
    store = StubStore(CHUNKS)
    retriever = HybridRetriever(store, KeywordEmbedder(), min_similarity=0.0)
    result = retriever.retrieve("normal form", "sen5016")

    assert store.calls == [("SEN5016", None)]
    assert result.hits and all(hit.filename == "architecture.pdf" for hit in result.hits)


def test_top_k_is_respected_and_low_scores_are_dropped():
    retriever = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), top_k=2, min_similarity=0.5)
    result = retriever.retrieve("normal form", "COM3001")

    assert len(result.hits) == 2
    assert all(hit.score >= 0.5 for hit in result.hits)


def test_unknown_course_returns_no_source():
    result = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder()).retrieve("normal form", "XYZ999")
    assert not result.covered and result.candidate_count == 0


def test_empty_question_and_missing_course_are_rejected():
    retriever = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder())
    with pytest.raises(ValueError):
        retriever.retrieve("   ", "COM3001")
    with pytest.raises(ValueError):
        retriever.retrieve("normal form", "")


def test_embedding_dimension_mismatch_is_reported():
    class ShortEmbedder:
        def encode(self, texts):
            return [[1.0, 0.0] for _ in texts]

    with pytest.raises(ValueError, match="same model"):
        HybridRetriever(StubStore(CHUNKS), ShortEmbedder()).retrieve("normal form", "COM3001")


def test_retriever_works_on_the_real_rdf_graph(tmp_path, sample_pdf, fake_embedder):
    pytest.importorskip("rdflib")
    from coursegraph.graph_store import GraphStore

    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    store.validate_graph = lambda _graph: (True, "stub: SHACL is tested in E1 tests")
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="lesson.pdf", course_id="SEN5016",
                     embedder=fake_embedder)
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="other.pdf", course_id="COM3001",
                     embedder=fake_embedder)

    result = HybridRetriever(store, fake_embedder, min_similarity=0.0).retrieve("page", "SEN5016")

    assert result.covered
    assert result.candidate_count == 2
    assert all(hit.document_uri for hit in result.hits)
    assert {hit.page_number for hit in result.hits} <= {1, 2}
