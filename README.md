# CourseGraph

**CourseGraph** is a knowledge-graph-powered study assistant built for university course revision. It allows students to upload course lecture slide PDFs, indexes them into a structured knowledge graph, and answers questions using a local LLM while citing the exact source documents and page numbers.

---

## Current Status: Phase 1 (UI Skeleton & CI Setup)

This repository currently contains the **Phase 1** foundation:
- **Flask Web Interface:** Complete frontend UI with mock data for demonstration.
- **Upload & Query Forms:** Allows testing file validation, course code assignment, and query responses.
- **Answer Display with Citations:** UI cards ready to render citations (Document title, Page number, Source snippet).
- **Quality Report (`/report`):** Initial dashboard view for evaluation metrics (Recall@3, citation accuracy, median latency).
- **Automated Testing:** 15 pytest test cases verifying all route responses and form validations.
- **Continuous Integration (CI):** GitHub Actions pipeline configured to run tests automatically on every push.

---

## Project Structure

```text
├── app.py                      # Flask web application and mock service layer
├── requirements.txt            # Python dependencies (Flask, Pytest, etc.)
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI workflow
├── static/
│   └── style.css               # Main styling
├── templates/
│   ├── base.html               # Shared layout (navbar, footer, flash alerts)
│   ├── index.html              # Main page (upload, query, citation cards)
│   └── report.html             # /report evaluation metrics dashboard
└── tests/
    ├── conftest.py             # Pytest setup and test client fixtures
    └── test_routes.py          # 15 tests covering all routes and validations
```

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```
Open your browser at: `http://127.0.0.1:5000`

### 3. Run the Tests
```bash
pytest tests/ -v
```

---

## Integration Plan for Teammates (Next Steps)

* **Celal (PDF Ingestion & RDF Graph):**
  - In `app.py`, replace the mock logic in the `/upload` route with your `IngestService`.
  - Pass the uploaded PDF to the RDF graph builder and SHACL validator.

* **Melisa (Hybrid Retriever & Ollama LLM):**
  - In `app.py`, replace the `_mock_answer()` function in the `/ask` route with your `AnswerService`.
  - Return the top-3 retrieved chunks with exact page numbers and PROV-O metadata.
  - Connect live evaluation results to the `/report` template.
