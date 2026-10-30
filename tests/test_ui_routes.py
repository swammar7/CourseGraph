"""UI and Integration route tests for CourseGraph Flask application."""
from io import BytesIO

import pytest

flask = pytest.importorskip("flask")
pytest.importorskip("pyshacl")
from app import create_app


def _client(tmp_path, fake_embedder):
    app = create_app(
        {
            "TESTING": True,
            "GRAPH_PATH": str(tmp_path / "graph.ttl"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "LEGACY_INDEX": str(tmp_path / "absent.json"),
        },
        embedder=fake_embedder,
    )
    return app.test_client()


def test_home_page_loads_with_status_200(tmp_path, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.get("/")
    assert response.status_code == 200
    assert b"CourseGraph" in response.data
    assert b"Ingest Course PDF" in response.data


def test_report_page_loads_with_metrics(tmp_path, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.get("/report")
    assert response.status_code == 200
    assert b"Quality Report" in response.data
    assert b"Recall@3" in response.data
    assert b"Citation Accuracy" in response.data
    assert b"Median Answer Time" in response.data


def test_upload_pdf_form_and_redirect(tmp_path, sample_pdf, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post(
        "/upload",
        data={
            "pdf": (BytesIO(sample_pdf), "lecture_slides.pdf"),
            "course_id": "SEN0414",
            "topics": "RDF, Ontologies",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    follow = client.get("/")
    assert b"lecture_slides.pdf" in follow.data
    assert b"SEN0414" in follow.data


def test_query_post_returns_answer_structure(tmp_path, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post(
        "/",
        data={"query": "What is normalization?", "course_filter": ""},
    )
    assert response.status_code == 200
    assert b"Answer" in response.data
