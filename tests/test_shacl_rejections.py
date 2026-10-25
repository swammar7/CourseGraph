"""Real pySHACL negative controls: intentionally corrupt RDF, expect failure."""
import pytest
from rdflib import Literal
from rdflib.namespace import RDF, SKOS, XSD

from coursegraph.graph_store import CG, GraphStore


def _make_store(tmp_path, sample_pdf, fake_embedder):
    pytest.importorskip("pyshacl")
    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    result = store.ingest_pdf(
        pdf_bytes=sample_pdf, filename="lesson.pdf", course_id="SEN0414",
        embedder=fake_embedder, topics=["RDF"],
    )
    assert result["shacl_conforms"] is True
    return store


@pytest.mark.parametrize("mutation,property_name", [
    ("missing_chunk_page", "chunkPageNumber"),
    ("missing_page_number", "pageNumber"),
    ("blank_chunk", "text"),
    ("whitespace_chunk", "text"),
    ("missing_chunk_text", "text"),
    ("missing_page_relationship", "belongsToPage"),
    ("missing_topic_label", "prefLabel"),
])
def test_invalid_rdf_is_rejected_and_disk_graph_stays_valid(
    tmp_path, sample_pdf, fake_embedder, mutation, property_name,
):
    store = _make_store(tmp_path, sample_pdf, fake_embedder)
    graph = store.load_graph()
    chunk = next(graph.subjects(RDF.type, CG.Chunk))
    page = next(graph.subjects(RDF.type, CG.Page))
    topic = next(graph.subjects(RDF.type, SKOS.Concept))

    if mutation == "missing_chunk_page":
        graph.remove((chunk, CG.chunkPageNumber, None))
    elif mutation == "missing_page_number":
        graph.remove((page, CG.pageNumber, None))
    elif mutation == "blank_chunk":
        graph.set((chunk, CG.text, Literal("", datatype=XSD.string)))
    elif mutation == "whitespace_chunk":
        graph.set((chunk, CG.text, Literal("  \t\n", datatype=XSD.string)))
    elif mutation == "missing_chunk_text":
        graph.remove((chunk, CG.text, None))
    elif mutation == "missing_page_relationship":
        graph.remove((chunk, CG.belongsToPage, None))
    elif mutation == "missing_topic_label":
        graph.remove((topic, SKOS.prefLabel, None))
    else:
        raise AssertionError(f"Unhandled mutation: {mutation}")

    conforms, report = store.validate_graph(graph)
    assert conforms is False, mutation
    assert property_name in report, report

    # No corruption is committed to disk by these in-memory negative tests.
    conforms_on_disk, _ = store.validate_graph(store.load_graph())
    assert conforms_on_disk is True
