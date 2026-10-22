"""
Tests for CourseGraph Flask routes.

Covers:
  - GET /         → home page loads
  - POST /upload  → file upload flow (success and validation errors)
  - POST /ask     → question answering (normal and off-topic)
  - GET /report   → quality report page loads
"""

import io


# ── Home page ────────────────────────────────────────────────────────────────

class TestHomePage:
    def test_home_returns_200(self, client):
        """GET / should return HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_home_contains_title(self, client):
        """Home page should contain the project name."""
        response = client.get("/")
        assert b"CourseGraph" in response.data

    def test_home_has_upload_form(self, client):
        """Home page should contain the PDF upload form."""
        response = client.get("/")
        assert b"Upload" in response.data
        assert b"pdf_file" in response.data

    def test_home_has_question_form(self, client):
        """Home page should contain the question form."""
        response = client.get("/")
        assert b"question" in response.data
        assert b"Ask" in response.data


# ── PDF Upload ───────────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_no_file_redirects(self, client):
        """POST /upload with no file should redirect with an error."""
        response = client.post("/upload", data={"course_code": "SEN5016"})
        assert response.status_code == 302

    def test_upload_no_course_redirects(self, client):
        """POST /upload with no course code should redirect with an error."""
        data = {
            "pdf_file": (io.BytesIO(b"%PDF-1.4 fake"), "test.pdf"),
        }
        response = client.post(
            "/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 302

    def test_upload_non_pdf_rejected(self, client):
        """POST /upload with a non-PDF file should redirect with an error."""
        data = {
            "pdf_file": (io.BytesIO(b"not a pdf"), "notes.txt"),
            "course_code": "SEN5016",
        }
        response = client.post(
            "/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 302

    def test_upload_success(self, client):
        """POST /upload with valid PDF and course should redirect to index."""
        data = {
            "pdf_file": (io.BytesIO(b"%PDF-1.4 fake content"), "lecture3.pdf"),
            "course_code": "SEN5016",
        }
        response = client.post(
            "/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 302

        # Follow the redirect and check the flash message
        follow = client.get("/")
        assert b"lecture3.pdf" in follow.data

    def test_upload_success_flash_message(self, client):
        """Successful upload should show a success flash message."""
        data = {
            "pdf_file": (io.BytesIO(b"%PDF-1.4 fake content"), "slides.pdf"),
            "course_code": "MAT2031",
        }
        client.post("/upload", data=data, content_type="multipart/form-data")
        response = client.get("/")
        assert b"uploaded and indexed successfully" in response.data


# ── Ask a Question ───────────────────────────────────────────────────────────

class TestAsk:
    def test_ask_empty_question_redirects(self, client):
        """POST /ask with an empty question should redirect."""
        response = client.post("/ask", data={"question": "", "course_filter": ""})
        assert response.status_code == 302

    def test_ask_returns_answer(self, client):
        """POST /ask with a valid question should return an answer."""
        response = client.post(
            "/ask",
            data={"question": "What is third normal form?", "course_filter": ""},
        )
        assert response.status_code == 200
        assert b"Answer" in response.data
        assert b"Third Normal Form" in response.data

    def test_ask_shows_citations(self, client):
        """Answer should include source citations with document and page."""
        response = client.post(
            "/ask",
            data={"question": "Explain normalization", "course_filter": "SEN5016"},
        )
        assert response.status_code == 200
        assert b"Page" in response.data
        assert b"Sources" in response.data

    def test_ask_off_topic_shows_no_source(self, client):
        """Off-topic question should return 'no source' response."""
        response = client.post(
            "/ask",
            data={"question": "What is the weather today?", "course_filter": ""},
        )
        assert response.status_code == 200
        assert b"do not cover this question" in response.data

    def test_ask_off_topic_has_no_citations(self, client):
        """Off-topic answer should have no citation cards."""
        response = client.post(
            "/ask",
            data={"question": "Tell me a movie recommendation", "course_filter": ""},
        )
        assert response.status_code == 200
        assert b"citation-card" not in response.data


# ── Report Page ──────────────────────────────────────────────────────────────

class TestReport:
    def test_report_returns_200(self, client):
        """GET /report should return HTTP 200."""
        response = client.get("/report")
        assert response.status_code == 200

    def test_report_contains_metrics(self, client):
        """Report page should display the evaluation metrics."""
        response = client.get("/report")
        assert b"Recall@3" in response.data
        assert b"Citation Accuracy" in response.data
        assert b"Median Answer Time" in response.data

    def test_report_shows_values(self, client):
        """Report should show the actual metric values."""
        response = client.get("/report")
        assert b"82%" in response.data   # recall
        assert b"88%" in response.data   # citation accuracy
        assert b"2150" in response.data  # median time
