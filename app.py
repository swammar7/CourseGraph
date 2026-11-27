"""CourseGraph Flask Application (Integrated Week 1 & 2)

Integrates:
- Real PDF ingestion, chunking, RDF graph store & SHACL validation (E1 - Ahmet)
- Modern UI templates with base layout, CSS styling & flash alerts (Ammar)
- E2 hybrid retriever + Ollama answer service with page citations (Melisa)
- Quality evaluation dashboard (/report) with DoD metrics (Ammar)
- REST APIs (/api/upload, /api/documents, /api/courses/<id>/chunks)
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import re

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from coursegraph.answer_service import AnswerService, OllamaClient
from coursegraph.embeddings import LocalEmbedder
from coursegraph.graph_store import GraphStore, GraphValidationError
from coursegraph.pdf_processing import PdfProcessingError
from coursegraph.provenance import ProvenanceError, ProvenanceRecorder
from coursegraph.retriever import HybridRetriever


BASE_DIR = Path(__file__).resolve().parent
_DOCUMENT_KEY = re.compile(r"^[0-9a-f]{64}$")


def create_app(config: dict | None = None, *, embedder=None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("COURSEGRAPH_SECRET_KEY", "local-development-key"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        GRAPH_PATH=str(BASE_DIR / "data" / "graph.ttl"),
        UPLOAD_FOLDER=str(BASE_DIR / "data" / "uploads"),
        MODEL_PATH=str(BASE_DIR / "models" / "all-MiniLM-L6-v2"),
        OLLAMA_MODEL=os.getenv("COURSEGRAPH_OLLAMA_MODEL", "qwen2.5:3b"),
        OLLAMA_HOST=os.getenv("COURSEGRAPH_OLLAMA_HOST", "http://127.0.0.1:11434"),
        OLLAMA_TIMEOUT=60.0,
        PROVENANCE_PATH=None,
        EVAL_RESULTS=str(BASE_DIR / "eval" / "results.json"),
    )
    if config:
        app.config.update(config)

    local_embedder = embedder or LocalEmbedder(app.config["MODEL_PATH"])
    store = GraphStore(app.config["GRAPH_PATH"], app.config["UPLOAD_FOLDER"])

    retriever = HybridRetriever(store, local_embedder)
    answer_service = AnswerService(
        retriever,
        OllamaClient(
            model=app.config["OLLAMA_MODEL"], host=app.config["OLLAMA_HOST"],
            timeout=app.config["OLLAMA_TIMEOUT"],
        ),
    )
    app.extensions["answer_service"] = answer_service
    app.extensions["provenance"] = ProvenanceRecorder(store, app.config["PROVENANCE_PATH"])

    def answer_query(query: str, course_filter: str | None = None) -> dict:
        """E2: hybrid retrieval (SPARQL + cosine top-3) and a cited local-LLM answer."""
        if not course_filter:
            return {"text": "Please choose a course before asking a question.",
                    "covered": False, "error": None, "citations": [], "time_ms": 0}
        try:
            result = app.extensions["answer_service"].answer(query, course_filter)
        except (ValueError, RuntimeError) as exc:
            return {"text": f"The question could not be answered: {exc}",
                    "covered": False, "error": str(exc), "citations": [], "time_ms": 0}

        # PROV-O record; a failed record is logged but never hides the answer.
        try:
            app.extensions["provenance"].record(result)
        except (ProvenanceError, OSError) as exc:
            app.logger.warning("Answer provenance was not saved: %s", exc)

        view = result.to_view()
        for cite_view, cite in zip(view["citations"], result.citations):
            document_key = cite["document_uri"].rsplit("/", 1)[-1]
            cite_view["pdf_url"] = (
                url_for("document_pdf", document_key=document_key) + f"#page={cite['page_number']}"
            )
        return view

    @app.route("/", methods=["GET", "POST"])
    def home():
        answer = None
        question = None
        selected_course = None
        documents = store.list_documents()
        courses = sorted(list(set(d["course"] for d in documents if "course" in d)))

        if request.method == "POST":
            question = request.form.get("query", "").strip() or request.form.get("question", "").strip()
            selected_course = request.form.get("course_filter", "").strip().upper() or None
            if question:
                answer = answer_query(question, selected_course)

        return render_template(
            "index.html",
            documents=documents,
            courses=courses,
            answer=answer,
            question=question,
            selected_course=selected_course,
        )

    @app.route("/documents/<document_key>.pdf", methods=["GET"])
    def document_pdf(document_key: str):
        """Serves an uploaded PDF so a citation can open it at the cited page."""
        if not _DOCUMENT_KEY.fullmatch(document_key):
            abort(404)
        return send_from_directory(
            Path(app.config["UPLOAD_FOLDER"]).resolve(), f"{document_key}.pdf",
            mimetype="application/pdf",
        )

    @app.route("/report", methods=["GET"])
    def report():
        """Quality report from eval/results.json, written by scripts/evaluate.py.

        No placeholder numbers: without a results file the page says so.
        """
        return render_template("report.html", report=load_evaluation(Path(app.config["EVAL_RESULTS"])))

    @app.route("/api/documents", methods=["GET"])
    def list_documents():
        return jsonify(store.list_documents())

    @app.route("/api/courses/<course_id>/chunks", methods=["GET"])
    def course_chunks(course_id: str):
        """Paginated read-only diagnostic API; E2 should prefer GraphStore directly."""
        course_id = course_id.strip().upper()
        topic = request.args.get("topic")
        include_embeddings = request.args.get("include_embeddings", "0")
        if include_embeddings not in {"0", "1"}:
            return jsonify({"error": "include_embeddings must be 0 or 1."}), 400
        try:
            limit = int(request.args.get("limit", "50"))
            offset = int(request.args.get("offset", "0"))
        except ValueError:
            return jsonify({"error": "limit and offset must be integers."}), 400
        if not 1 <= limit <= 200 or offset < 0:
            return jsonify({"error": "limit must be 1-200, offset >= 0."}), 400
        try:
            chunks = store.get_course_chunks(course_id, topic=topic)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        page = chunks[offset:offset + limit]
        if include_embeddings == "0":
            page = [{k: v for k, v in item.items() if k != "embedding"} for item in page]
        return jsonify({
            "course_id": course_id,
            "topic": topic or None,
            "total": len(chunks),
            "limit": limit,
            "offset": offset,
            "items": page,
        })

    @app.route("/api/upload", methods=["POST"])
    @app.route("/upload", methods=["POST"])
    def upload():
        wants_json = request.path.startswith("/api/")
        uploaded = request.files.get("pdf") or request.files.get("pdf_file")
        course_id = (request.form.get("course_id") or request.form.get("course_code") or "").strip().upper()
        raw_topics = request.form.get("topics", "")

        if not uploaded or not uploaded.filename:
            return _upload_error("Please select a PDF file.", 400, wants_json)

        filename = secure_filename(uploaded.filename)
        if not filename or not filename.lower().endswith(".pdf"):
            return _upload_error("File must have a .pdf extension.", 400, wants_json)

        try:
            topics_list = [t.strip() for t in raw_topics.split(",") if t.strip()] if raw_topics else None
            result = store.ingest_pdf(
                pdf_bytes=uploaded.read(),
                filename=filename,
                course_id=course_id,
                embedder=local_embedder,
                topics=topics_list,
            )
        except (PdfProcessingError, GraphValidationError) as exc:
            return _upload_error(str(exc), 422, wants_json)
        except ValueError as exc:
            return _upload_error(str(exc), 400, wants_json)
        except RuntimeError as exc:
            return _upload_error(str(exc), 503, wants_json)

        if wants_json:
            return jsonify(result), (201 if result["status"] == "created" else 200)

        flash(
            f"PDF '{filename}' successfully ingested and validated against SHACL shapes."
            if result["status"] == "created"
            else f"PDF '{filename}' is already recorded for course {course_id}.",
            "success",
        )
        return redirect(url_for("home"))

    @app.errorhandler(413)
    def too_large(_error):
        return _upload_error("PDF file exceeds maximum allowed size of 20 MB.", 413, request.path.startswith("/api/"))

    def _upload_error(message: str, status: int, wants_json: bool):
        if wants_json:
            return jsonify({"error": message}), status
        flash(message, "error")
        return redirect(url_for("home"))

    return app


def load_evaluation(path: Path) -> dict | None:
    """Reads the evaluation results and adds per-course recall and the missed questions."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        summary, rows = data["summary"], data["questions"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"error": f"{path.name} could not be read: {exc}"}

    courses = {}
    for row in rows:
        course = courses.setdefault(row["course"], {"course": row["course"], "answerable": 0, "hits": 0,
                                                     "unanswerable": 0, "rejected": 0})
        if row.get("answerable", True):
            course["answerable"] += 1
            course["hits"] += bool(row.get("hit_at_3"))
        else:
            course["unanswerable"] += 1
            course["rejected"] += not row.get("covered")
    for course in courses.values():
        course["recall"] = course["hits"] / course["answerable"] if course["answerable"] else None

    misses = [r for r in rows if r.get("answerable", True) and not r.get("hit_at_3")]
    false_answers = [r for r in rows if not r.get("answerable", True) and r.get("covered")]
    return {
        "summary": summary,
        "settings": data.get("settings", {}),
        "generated_at": data.get("generated_at"),
        "courses": sorted(courses.values(), key=lambda c: c["course"]),
        "misses": misses,
        "false_answers": false_answers,
    }


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
