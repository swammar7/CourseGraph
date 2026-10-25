"""E1 -> E2 SPARQL contract checks, runnable without an embedding model."""
import json

import pytest
from rdflib import Literal
from rdflib.namespace import RDF, XSD

from coursegraph.graph_store import CG, GraphStore


def _store(tmp_path):
    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    # The positive SPARQL contract is tested separately from actual pySHACL tests.
    store.validate_graph = lambda _graph: (True, "stub for SPARQL-only tests")
    return store


def test_course_filter_keeps_correct_pages_citations_and_embeddings(
    tmp_path, sample_pdf, fake_embedder,
):
    store = _store(tmp_path)
    for course, topics in [("SEN0414", ["RDF", "Python"]), ("SEN0415", ["Math"])]:
        store.ingest_pdf(
            pdf_bytes=sample_pdf, filename="lesson.pdf", course_id=course,
            topics=topics, embedder=fake_embedder,
        )

    chunks = store.get_course_chunks("SEN0414")
    assert len(chunks) == 2
    assert [row["page_number"] for row in chunks] == [1, 2]
    assert all(row["course_id"] == "SEN0414" for row in chunks)
    assert all(row["filename"] == "lesson.pdf" for row in chunks)
    assert all(row["chunk_uri"].startswith("https://coursegraph.local/resource/chunk/") for row in chunks)
    assert all(isinstance(row["embedding"], list) and len(row["embedding"]) == 3 for row in chunks)
    assert all(row["topics"] == ["Python", "RDF"] for row in chunks)
    assert all(row["text"] for row in chunks)
    assert not any(row["course_id"] == "SEN0415" for row in chunks)

    assert len(store.get_course_chunks("SEN0414", topic="RDF")) == 2
    assert store.get_course_chunks("SEN0414", topic="Math") == []
    assert len(store.get_course_chunks("SEN0415", topic="Math")) == 2
    assert store.get_course_chunks("UNKNOWN") == []


def test_topic_is_bound_not_injected_into_sparql(tmp_path, sample_pdf, fake_embedder):
    store = _store(tmp_path)
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="lesson.pdf", course_id="SEN0414", embedder=fake_embedder)
    assert store.get_course_chunks("SEN0414", topic='Genel" } UNION { ?s ?p ?o } #') == []
    with pytest.raises(ValueError, match="ders kodu"):
        store.get_course_chunks('SEN0414> . ?x ?y ?z . <')


def test_corrupted_embedding_is_not_silently_returned(tmp_path, sample_pdf, fake_embedder):
    store = _store(tmp_path)
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="lesson.pdf", course_id="SEN0414", embedder=fake_embedder)
    graph = store.load_graph()
    chunk = next(graph.subjects(RDF.type, CG.Chunk))
    graph.set((chunk, CG.embeddingJson, Literal(json.dumps([0.1, "bad"]), datatype=XSD.string)))
    graph.serialize(destination=store.graph_path, format="turtle")
    with pytest.raises(ValueError, match="Bozuk embeddingJson"):
        store.get_course_chunks("SEN0414")
