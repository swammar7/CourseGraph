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

## 🧠 Status: E2 Hybrid Retrieval, Cited Answers & Provenance

E2 connects the knowledge graph to a local language model, so a question about a course is answered only from that course's slides:

- **Hybrid retriever (`coursegraph/retriever.py`):** SPARQL selects the chunks of the chosen course, the question is encoded with the same local MiniLM model, and the top-3 chunks by cosine similarity are kept if they score at least 0.35. Otherwise the assistant replies that no source was found.
- **Grounded answers (`coursegraph/answer_service.py`):** the three chunks are sent to **Ollama on localhost** (`qwen2.5:3b`), which must cite them as `[1]`, `[2]`, `[3]` or reply `NO_ANSWER`. Without sources the model is never called; if Ollama is down, the matching pages are still shown.
- **Page citations:** each citation card shows `[n] file.pdf — Page p` and an **Open page ↗** link (`/documents/<key>.pdf#page=p`).
- **PROV-O provenance (`coursegraph/provenance.py`):** every answer is stored with its question, cited chunks, scores, model and response time in `data/provenance.ttl`, after validation against the new E2 SHACL shapes.
- Details: [`docs/E2_RETRIEVAL.md`](docs/E2_RETRIEVAL.md).

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
│   ├── embeddings.py           # Local SentenceTransformer embedding wrapper
│   ├── retriever.py            # E2 hybrid retriever (SPARQL filter + cosine top-3 + threshold)
│   ├── answer_service.py       # E2 localhost Ollama client and cited answer generation
│   └── provenance.py           # E2 PROV-O answer records with SHACL validation
├── docs/
│   ├── E1_INTEGRATION.md       # E1 → E2 data contract
│   ├── E1_SHACL_AND_TESTS.md   # E1 SHACL rules and tests
│   └── E2_RETRIEVAL.md         # E2 retrieval, answering and provenance guide
├── ontology/
│   ├── coursegraph.ttl         # Core RDF/RDFS/OWL/SKOS ontology + E2 PROV-O classes
│   └── shapes.ttl              # pySHACL shapes (documents + E2 answers/citations)
├── static/
│   └── style.css               # Clean student interface styling
├── templates/
│   ├── base.html               # Base layout template
│   ├── index.html              # Main upload & query interface
│   └── report.html             # Quality report metrics page
└── tests/
    ├── conftest.py             # Shared fixtures & FakeEmbedder for fast offline testing
    ├── test_app.py             # API route tests
    ├── test_app_e2.py          # E2 web flow: cited pages, PDF links, provenance
    ├── test_answer_service.py  # E2 answer service with a fake model
    ├── test_graph_store.py     # GraphStore unit tests
    ├── test_pdf_processing.py  # PDF text extraction tests
    ├── test_provenance.py      # E2 PROV-O records and SHACL rejections
    ├── test_rdf_construction.py# RDF triple structure tests
    ├── test_retriever.py       # E2 ranking, threshold and course filter
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

### 2. Start the Local Language Model (Ollama)
Install [Ollama](https://ollama.com), then download the model once:
```bash
ollama pull qwen2.5:3b
```
Ollama must be running on `http://127.0.0.1:11434`. Another local model can be chosen with `COURSEGRAPH_OLLAMA_MODEL`.

### 3. Run the Application
```bash
python app.py
```
Open your browser at: **`http://127.0.0.1:5000`**

### 4. Run the Test Suite
The tests do not need Ollama; the model is replaced by a fake.
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
