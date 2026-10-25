"""RDF/SPARQL smoke tests work without a pySHACL installation.

These tests deliberately stub validation; they do NOT prove SHACL conformance.
"""
import json

from rdflib.namespace import RDF, SKOS

from coursegraph.graph_store import CG, GraphStore, GraphValidationError


def test_rdf_structure_and_sparql_join(tmp_path, sample_pdf, fake_embedder):
    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    store.validate_graph = lambda _graph: (True, "SHACL stubbed for this test")
    store.ingest_pdf(pdf_bytes=sample_pdf, filename="class.pdf", course_id="SEN0414", embedder=fake_embedder)
    graph = store.load_graph()
    assert len(list(graph.subjects(RDF.type, CG.Document))) == 1
    assert len(list(graph.subjects(RDF.type, CG.Page))) == 2
    assert len(list(graph.subjects(RDF.type, CG.Chunk))) == 2

    q = '''PREFIX cg: <https://coursegraph.local/ontology#>
       PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
       SELECT ?pageNumber ?text ?embeddingJson WHERE {
         ?course a cg:Course ; skos:prefLabel ?label ; cg:hasDocument ?doc .
         FILTER(STR(?label) = "SEN0414")
         ?doc cg:hasPage ?page .
         ?page cg:pageNumber ?pageNumber ; cg:hasChunk ?chunk .
         ?chunk cg:text ?text ; cg:embeddingJson ?embeddingJson .
       }
       ORDER BY ?pageNumber'''
    results = list(graph.query(q))
    assert [int(row.pageNumber) for row in results] == [1, 2]
    assert all(len(json.loads(str(row.embeddingJson))) == 3 for row in results)
    assert graph.value(next(graph.subjects(RDF.type, CG.Course)), SKOS.prefLabel)


def test_failed_shacl_does_not_persist(tmp_path, sample_pdf, fake_embedder):
    import pytest
    store = GraphStore(tmp_path / "graph.ttl", tmp_path / "uploads")
    store.validate_graph = lambda _graph: (False, "missing chunkPageNumber")
    with pytest.raises(GraphValidationError):
        store.ingest_pdf(pdf_bytes=sample_pdf, filename="x.pdf", course_id="SEN0414", embedder=fake_embedder)
    assert not store.graph_path.exists()
    assert not list(store.upload_dir.glob("*.pdf"))
