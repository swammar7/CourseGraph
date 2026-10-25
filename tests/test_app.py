from io import BytesIO

import pytest

flask = pytest.importorskip("flask")
pytest.importorskip("pyshacl")
from app import create_app


def _client(tmp_path, fake_embedder):
    app = create_app(
        {"TESTING": True, "GRAPH_PATH": str(tmp_path / "graph.ttl"),
         "UPLOAD_FOLDER": str(tmp_path / "uploads"),
         "LEGACY_INDEX": str(tmp_path / "absent.json")},
        embedder=fake_embedder,
    )
    return app.test_client()


def test_upload_endpoint_and_documents(tmp_path, sample_pdf, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post("/api/upload", data={
        "pdf": (BytesIO(sample_pdf), "notes.pdf"),
        "course_id": "SEN0414", "topics": "RDF, Python",
    }, content_type="multipart/form-data")
    assert response.status_code == 201
    assert response.json["shacl_conforms"] is True
    docs = client.get("/api/documents")
    assert docs.status_code == 200
    assert len(docs.json) == 1
    assert docs.json[0]["course"] == "SEN0414"


def test_invalid_pdf_returns_error(tmp_path, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post("/api/upload", data={
        "pdf": (BytesIO(b"invalid"), "bad.pdf"), "course_id": "SEN0414",
    }, content_type="multipart/form-data")
    assert response.status_code == 422
    assert "error" in response.json


def test_missing_course_returns_400(tmp_path, sample_pdf, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post("/api/upload", data={
        "pdf": (BytesIO(sample_pdf), "doc.pdf"), "course_id": "",
    }, content_type="multipart/form-data")
    assert response.status_code == 400


def test_course_chunks_endpoint_filters_and_paginates(tmp_path, sample_pdf, fake_embedder):
    client = _client(tmp_path, fake_embedder)
    response = client.post("/api/upload", data={
        "pdf": (BytesIO(sample_pdf), "lesson.pdf"),
        "course_id": "SEN0414", "topics": "RDF, Python",
    }, content_type="multipart/form-data")
    assert response.status_code == 201

    response = client.get("/api/courses/SEN0414/chunks?topic=RDF&limit=1")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["page_number"] == 1
    assert body["items"][0]["filename"] == "lesson.pdf"
    assert "embedding" not in body["items"][0]

    response = client.get("/api/courses/SEN0414/chunks?offset=1&limit=1&include_embeddings=1")
    assert response.status_code == 200
    assert response.json["items"][0]["page_number"] == 2
    assert len(response.json["items"][0]["embedding"]) == 3

    assert client.get("/api/courses/SEN0414/chunks?topic=unrelated").json["total"] == 0
    assert client.get("/api/courses/SEN0414/chunks?limit=999").status_code == 400
    assert client.get("/api/courses/SEN0414/chunks?limit=0").status_code == 400
    assert client.get("/api/courses/SEN0414/chunks?offset=-1").status_code == 400
    assert client.get("/api/courses/SEN0414/chunks?include_embeddings=maybe").status_code == 400
