"""E2 web flow: ask a question, see cited pages, open the PDF, answer is recorded."""
from io import BytesIO

import pytest

pytest.importorskip("flask")
pytest.importorskip("pyshacl")
from app import create_app
from coursegraph.provenance import ProvenanceError


class FakeLLM:
    model = "qwen2.5:3b"

    def generate(self, prompt, system):
        return "The slide explains it [1]."


def _app(tmp_path, fake_embedder, sample_pdf):
    app = create_app(
        {"TESTING": True, "GRAPH_PATH": str(tmp_path / "graph.ttl"),
         "UPLOAD_FOLDER": str(tmp_path / "uploads")},
        embedder=fake_embedder,
    )
    service = app.extensions["answer_service"]
    service.llm = FakeLLM()
    service.retriever.min_similarity = 0.0
    client = app.test_client()
    response = client.post("/api/upload", data={
        "pdf": (BytesIO(sample_pdf), "lesson.pdf"), "course_id": "SEN5016",
    }, content_type="multipart/form-data")
    assert response.status_code == 201
    return app, client


def test_citations_open_the_pdf_at_the_cited_page(tmp_path, fake_embedder, sample_pdf):
    app, client = _app(tmp_path, fake_embedder, sample_pdf)

    page = client.post("/", data={"query": "What is on the page?", "course_filter": "SEN5016"})
    html = page.get_data(as_text=True)

    assert page.status_code == 200
    assert "The slide explains it [1]." in html
    assert "[1] lesson.pdf" in html and "Open page" in html
    link = html.split('class="citation-link" href="', 1)[1].split('"', 1)[0]
    assert link.startswith("/documents/") and "#page=" in link

    pdf = client.get(link.split("#", 1)[0])
    assert pdf.status_code == 200
    assert pdf.mimetype == "application/pdf"
    assert pdf.data == sample_pdf


def test_every_answer_is_traceable_to_its_sources(tmp_path, fake_embedder, sample_pdf):
    app, client = _app(tmp_path, fake_embedder, sample_pdf)

    client.post("/", data={"query": "What is on the page?", "course_filter": "SEN5016"})

    recorder = app.extensions["provenance"]
    assert recorder.path == tmp_path / "provenance.ttl"
    assert recorder.answer_count() == 1


def test_question_without_course_is_not_answered_or_recorded(tmp_path, fake_embedder, sample_pdf):
    app, client = _app(tmp_path, fake_embedder, sample_pdf)

    html = client.post("/", data={"query": "What is on the page?"}).get_data(as_text=True)

    assert "Please choose a course" in html
    assert app.extensions["provenance"].answer_count() == 0


def test_failed_provenance_does_not_hide_the_answer(tmp_path, fake_embedder, sample_pdf):
    app, client = _app(tmp_path, fake_embedder, sample_pdf)

    def broken_record(_answer):
        raise ProvenanceError("SHACL failed")

    app.extensions["provenance"].record = broken_record
    page = client.post("/", data={"query": "What is on the page?", "course_filter": "SEN5016"})

    assert page.status_code == 200
    assert "The slide explains it [1]." in page.get_data(as_text=True)


@pytest.mark.parametrize("key", ["../graph", "abc", "Z" * 64])
def test_pdf_route_rejects_invalid_keys(tmp_path, fake_embedder, sample_pdf, key):
    _app_, client = _app(tmp_path, fake_embedder, sample_pdf)
    assert client.get(f"/documents/{key}.pdf").status_code == 404


def test_pdf_route_returns_404_for_unknown_document(tmp_path, fake_embedder, sample_pdf):
    _app_, client = _app(tmp_path, fake_embedder, sample_pdf)
    assert client.get(f"/documents/{'0' * 64}.pdf").status_code == 404
