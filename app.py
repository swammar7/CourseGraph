"""
CourseGraph – Flask web application
====================================
Student web interface for uploading course PDFs, asking questions,
and viewing answers with cited sources.

Phase 1: runs with mock data so the UI can be demonstrated and
tested before the RDF graph and retriever modules are ready.
"""

import os
import uuid
from datetime import datetime

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# ---------------------------------------------------------------------------
# In-memory mock data store (replaced by RDF graph in Phase 2)
# ---------------------------------------------------------------------------
UPLOADED_DOCS: list[dict] = []

MOCK_COURSES = ["SEN5016", "SEN4018", "MAT2031"]

MOCK_ANSWERS = {
    "default": {
        "text": (
            "Third Normal Form (3NF) requires that every non-prime attribute "
            "of a relation is non-transitively dependent on every candidate key. "
            "In simpler terms, a table is in 3NF if it is already in 2NF and "
            "no non-key column depends on another non-key column."
        ),
        "citations": [
            {"document": "Database_Lecture3.pdf", "page": 14, "chunk": "A relation R is in 3NF if for every functional dependency X → A ..."},
            {"document": "Database_Lecture3.pdf", "page": 15, "chunk": "To convert a relation to 3NF, decompose so that every determinant is a candidate key ..."},
            {"document": "Database_Lecture5.pdf", "page": 7, "chunk": "Normalization example: Student(ID, Name, DeptName, DeptHead) violates 3NF because ..."},
        ],
        "time_ms": 2340,
    },
    "no_source": {
        "text": "The uploaded documents do not cover this question. No answer was generated.",
        "citations": [],
        "time_ms": 580,
    },
}


def _mock_answer(question: str, course: str) -> dict:
    """Return a mock answer dict. Simulates the retriever + LLM pipeline."""
    # Simulate a "no source found" response for clearly off-topic questions
    off_topic_keywords = ["weather", "recipe", "football", "movie"]
    if any(kw in question.lower() for kw in off_topic_keywords):
        return MOCK_ANSWERS["no_source"]
    return MOCK_ANSWERS["default"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Main page: upload area, question form, uploaded documents list."""
    return render_template(
        "index.html",
        documents=UPLOADED_DOCS,
        courses=MOCK_COURSES,
        answer=None,
    )


@app.route("/upload", methods=["POST"])
def upload():
    """Handle PDF upload (mock: validates file extension, stores metadata)."""
    file = request.files.get("pdf_file")
    course = request.form.get("course_code", "").strip().upper()

    if not file or file.filename == "":
        flash("Please select a PDF file to upload.", "error")
        return redirect(url_for("index"))

    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files are accepted.", "error")
        return redirect(url_for("index"))

    if not course:
        flash("Please enter a course code.", "error")
        return redirect(url_for("index"))

    # Mock: simulate ingestion — in Phase 2 this calls the RDF ingest service
    doc = {
        "id": str(uuid.uuid4())[:8],
        "filename": file.filename,
        "course": course,
        "pages": 42,       # mock page count
        "chunks": 87,      # mock chunk count
        "status": "ready",
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    UPLOADED_DOCS.append(doc)
    flash(f"'{file.filename}' uploaded and indexed successfully ({doc['pages']} pages, {doc['chunks']} chunks).", "success")
    return redirect(url_for("index"))


@app.route("/ask", methods=["POST"])
def ask():
    """Handle a question (mock: returns a simulated answer with citations)."""
    question = request.form.get("question", "").strip()
    course = request.form.get("course_filter", "")

    if not question:
        flash("Please type a question.", "error")
        return redirect(url_for("index"))

    answer = _mock_answer(question, course)

    return render_template(
        "index.html",
        documents=UPLOADED_DOCS,
        courses=MOCK_COURSES,
        answer=answer,
        question=question,
        selected_course=course,
    )


@app.route("/report")
def report():
    """Quality report page (placeholder for Phase 3)."""
    # Mock evaluation metrics
    metrics = {
        "recall_at_3": 0.82,
        "citation_accuracy": 0.88,
        "median_time_ms": 2150,
        "total_questions": 50,
    }
    return render_template("report.html", metrics=metrics)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
