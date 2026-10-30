# CourseGraph

> **A Knowledge-Graph-Powered Study Assistant That Answers Questions from Course PDFs with Cited Sources**  
> *Course: SEN0414 — 2026–2027 Fall*

---

## 📌 Project Overview

CourseGraph helps university students revise effectively from lecture slides and course notes published on CATS. Instead of manually searching through dozens of PDF files or relying on external chatbots that hallucinate and lack source evidence, CourseGraph:
1. Ingests lecture slide PDFs into a structured **RDF Knowledge Graph** validated by **SHACL shapes**.
2. Organizes content around **SKOS concept schemes** (course codes & topics).
3. Uses a **hybrid retriever** (SPARQL course/topic filtering + local sentence embeddings) to identify the most relevant passages.
4. Generates grounded answers with exact **page citations** and records provenance via **PROV-O**.

---

## 🚀 Status: Week 2 Integration (Frontend, RDF Graph & CI)

This release delivers the complete **Week 2 integration**, connecting the backend RDF knowledge graph to the student-facing web interface:

- **Integrated Flask Web Application (`app.py`):**
  - Connected directly to `coursegraph.graph_store.GraphStore` for real-time PDF ingestion, chunking, and SHACL validation.
  - Live query interface with course filtering dropdown and styled citation display cards.
  - Complete REST API: `/api/upload`, `/api/documents`, and paginated `/api/courses/<id>/chunks`.
- **Modern Student Web Interface (`templates/`, `static/style.css`):**
  - `templates/base.html`: Common layout with responsive navigation, alert banners, and footer.
  - `templates/index.html`: Unified workspace for uploading PDFs with course/topic tags, viewing ingested documents with validation status, and asking revision questions.
  - `templates/report.html`: Quality evaluation dashboard tracking Recall@3, citation accuracy, and median response time.
- **Continuous Integration Pipeline (`.github/workflows/ci.yml`):**
  - Automated GitHub Actions workflow running tests on Ubuntu with Python 3.11 on every push and pull request.
- **Automated Test Suite (`tests/`):**
  - Unit and integration tests for RDF graph construction, SHACL rejection rules, SPARQL retrieval contracts, and UI routes.

---

## 📂 Project Structure

```text
├── app.py                      # Flask web application & REST endpoints
├── requirements.txt            # Production dependencies (Flask, rdflib, pyshacl, etc.)
├── requirements-dev.txt        # Development dependencies (pytest)
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI automated pipeline
├── coursegraph/
│   ├── graph_store.py          # RDFLib GraphStore, SPARQL queries & ingestion
│   ├── pdf_processing.py       # pypdf text extraction and page-aware chunking
│   └── embeddings.py           # Local SentenceTransformer embedding wrapper
├── ontology/
│   ├── coursegraph.ttl         # Core RDF/RDFS/OWL/SKOS course ontology
│   └── shapes.ttl              # pySHACL validation shapes
├── static/
│   └── style.css               # Clean student interface styling
├── templates/
│   ├── base.html               # Base layout template
│   ├── index.html              # Main upload & query interface
│   └── report.html             # Quality report metrics page
└── tests/
    ├── conftest.py             # Shared fixtures & FakeEmbedder for fast offline testing
    ├── test_app.py             # API route tests
    ├── test_graph_store.py     # GraphStore unit tests
    ├── test_pdf_processing.py  # PDF text extraction tests
    ├── test_rdf_construction.py# RDF triple structure tests
    ├── test_retriever_contract.py # SPARQL retrieval contract tests
    ├── test_shacl_rejections.py # SHACL validation negative tests
    └── test_ui_routes.py       # Web UI and template integration tests
```

---

## 🛠 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Run the Application
```bash
python app.py
```
Open your browser at: **`http://127.0.0.1:5000`**

### 3. Run the Test Suite
```bash
pytest -v
```

---

## 👥 Team Responsibilities & Workflow

| Member | Focus Area | Deliverables |
|---|---|---|
| **Ahmet Celal Koç** | PDF Ingestion & RDF Graph | `coursegraph/`, `ontology/`, SHACL validation, SPARQL interface |
| **M. Ammar Cashlan** | Web UI, Testing & CI/CD | `templates/`, `static/`, `app.py` integration, `/report`, GitHub Actions CI |
| **Melisa Zeynep Sarıgüzel** | Hybrid Retrieval & LLM Answering | SPARQL + cosine ranking, Ollama answer generation, citations, PROV-O |
