import json

import pytest
from rdflib import Literal
from rdflib.namespace import RDF, SKOS

from coursegraph.graph_store import CG, GraphStore


def _store(tmp_path):
    return GraphStore(graph_path=tmp_path / "graph.ttl", upload_dir=tmp_path / "uploads")


def test_rdf_document_pages_chunks_and_topics(tmp_path, sample_pdf, fake_embedder):
    pytest.importorskip("pyshacl")
    store = _store(tmp_path)
    outcome = store.ingest_pdf(
        pdf_bytes=sample_pdf, filename="lecture.pdf", course_id="SEN0414",
        topics=["RDF", "Ontology"], embedder=fake_embedder,
        words_per_chunk=5, overlap=1,
    )
    assert outcome["status"] == "created"
    assert outcome["shacl_conforms"] is True
    assert outcome["page_count"] == 2
    assert outcome["chunk_count"] >= 2
    assert fake_embedder.calls == 1
    graph = store.load_graph()
    documents = list(graph.subjects(RDF.type, CG.Document))
    assert len(documents) == 1
    pages = list(graph.objects(documents[0], CG.hasPage))
    assert len(pages) == 2
    assert sorted(int(graph.value(page, CG.pageNumber)) for page in pages) == [1, 2]
    chunks = list(graph.subjects(RDF.type, CG.Chunk))
    assert len(chunks) == outcome["chunk_count"]
    assert all(len(json.loads(str(graph.value(c, CG.embeddingJson)))) == 3 for c in chunks)
    assert all(list(graph.objects(c, CG.hasTopic)) for c in chunks)
    assert "RDF" in [str(x) for x in graph.objects(None, SKOS.prefLabel)]
    assert list((tmp_path / "uploads").glob("*.pdf"))


def test_invalid_chunk_page_number_fails_shacl(tmp_path, sample_pdf, fake_embedder):
    pytest.importorskip("pyshacl")
    store = _store(tmp_path)
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="doc.pdf", course_id="SEN0414", embedder=fake_embedder)
    graph = store.load_graph()
    chunk = next(graph.subjects(RDF.type, CG.Chunk))
    graph.remove((chunk, CG.chunkPageNumber, None))
    conforms, report = store.validate_graph(graph)
    assert conforms is False
    assert "chunkPageNumber" in report


def test_duplicate_pdf_is_not_reembedded(tmp_path, sample_pdf, fake_embedder):
    pytest.importorskip("pyshacl")
    store = _store(tmp_path)
    kwargs = dict(pdf_bytes=sample_pdf, filename="doc.pdf", course_id="SEN0414", embedder=fake_embedder)
    assert store.ingest_pdf(**kwargs)["status"] == "created"
    assert store.ingest_pdf(**kwargs)["status"] == "already_exists"
    assert fake_embedder.calls == 1
    assert len(store.list_documents()) == 1


def test_scanned_pdf_does_not_write_data(tmp_path, fake_embedder):
    from pypdf import PdfWriter
    from io import BytesIO
    from coursegraph.pdf_processing import PdfProcessingError
    writer = PdfWriter()
    writer.add_blank_page(300, 300)
    buf = BytesIO()
    writer.write(buf)
    store = _store(tmp_path)
    with pytest.raises(PdfProcessingError):
        store.ingest_pdf(pdf_bytes=buf.getvalue(), filename="scan.pdf", course_id="ABC", embedder=fake_embedder)
    assert not store.graph_path.exists()
    assert not (tmp_path / "uploads").exists()
