"""CourseGraph Flask app: E1 upload + previous prototype's simple search.

E2 (GraphRAG/SPARQL/Ollama) will replace the temporary legacy search logic.
"""
from __future__ import annotations

from pathlib import Path
import json
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from coursegraph.embeddings import LocalEmbedder
from coursegraph.graph_store import GraphStore, GraphValidationError
from coursegraph.pdf_processing import PdfProcessingError


BASE_DIR = Path(__file__).resolve().parent


def create_app(config: dict | None = None, *, embedder=None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("COURSEGRAPH_SECRET_KEY", "local-development-key"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        GRAPH_PATH=str(BASE_DIR / "data" / "graph.ttl"),
        UPLOAD_FOLDER=str(BASE_DIR / "data" / "uploads"),
        MODEL_PATH=str(BASE_DIR / "models" / "all-MiniLM-L6-v2"),
        LEGACY_INDEX=str(BASE_DIR / "index.json"),
    )
    if config:
        app.config.update(config)
    local_embedder = embedder or LocalEmbedder(app.config["MODEL_PATH"])
    store = GraphStore(app.config["GRAPH_PATH"], app.config["UPLOAD_FOLDER"])

    def legacy_search(query: str) -> str:
        """Backwards-compatible nearest paragraph; not CourseGraph E2."""
        import numpy as np

        index_path = Path(app.config["LEGACY_INDEX"])
        if not index_path.is_file():
            return "Eski index.json bulunamadı. E2 arama servisi henüz eklenmedi."
        with index_path.open(encoding="utf-8") as infile:
            index = json.load(infile)
        chunks, vectors = index.get("chunks", []), index.get("embeddings", [])
        if not chunks or len(chunks) != len(vectors):
            return "Eski indeks boş veya bozuk."
        query_vector = np.asarray(local_embedder.encode([query])[0], dtype=float)
        vectors = np.asarray(vectors, dtype=float)
        if vectors.ndim != 2 or vectors.shape[1] != len(query_vector):
            return "Eski indeks ile yerel modelin boyutları eşleşmiyor."
        norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_vector)
        similarities = np.divide(vectors @ query_vector, norms, out=np.zeros(len(chunks)), where=norms != 0)
        return chunks[int(np.argmax(similarities))]

    @app.route("/", methods=["GET", "POST"])
    def home():
        answer = None
        if request.method == "POST":
            query = request.form.get("query", "").strip()
            if query:
                try:
                    answer = legacy_search(query)
                except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
                    answer = f"Arama şu an kullanılamıyor: {exc}"
        return render_template("index.html", answer=answer, documents=store.list_documents())

    @app.route("/api/documents", methods=["GET"])
    def list_documents():
        return jsonify(store.list_documents())

    @app.route("/api/upload", methods=["POST"])
    @app.route("/upload", methods=["POST"])
    def upload():
        wants_json = request.path.startswith("/api/")
        uploaded = request.files.get("pdf")
        course_id = request.form.get("course_id", "").strip().upper()
        raw_topics = request.form.get("topics", "")

        if not uploaded or not uploaded.filename:
            return _upload_error("Bir PDF dosyası seçin.", 400, wants_json)
        # Do not use the user-provided path as a server path.
        filename = secure_filename(uploaded.filename)
        if not filename or not filename.lower().endswith(".pdf"):
            return _upload_error("Dosyanın uzantısı .pdf olmalı.", 400, wants_json)
        try:
            result = store.ingest_pdf(
                pdf_bytes=uploaded.read(),
                filename=filename,
                course_id=course_id,
                embedder=local_embedder,
                topics=raw_topics.split(","),
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
            "PDF başarıyla yüklendi ve SHACL doğrulandı."
            if result["status"] == "created"
            else "Bu PDF bu ders için zaten kayıtlı.",
            "success",
        )
        return redirect(url_for("home"))

    @app.errorhandler(413)
    def too_large(_error):
        return _upload_error("PDF en fazla 20 MB olabilir.", 413, request.path.startswith("/api/"))

    def _upload_error(message: str, status: int, wants_json: bool):
        if wants_json:
            return jsonify({"error": message}), status
        flash(message, "error")
        return redirect(url_for("home"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
