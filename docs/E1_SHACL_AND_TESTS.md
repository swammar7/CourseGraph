# CourseGraph E1 — SHACL rules and reproducible checks

## 1. Validation model

`coursegraph/graph_store.py:GraphStore.validate_graph(graph)` calls **real `pyshacl.validate`** with the constraints defined in `ontology/shapes.ttl`. It returns `(conforms: bool, report: str)`. An ingested candidate graph is validated *before* it is saved. If it fails, `GraphValidationError` prevents writing the candidate `graph.ttl`. Entirely image-only PDFs are rejected by the PDF text extraction step (there is no OCR in scope).

SHACL checks in the existing and expanded shapes include:

- Course has a SKOS course label; document belongs to a Course, has a non-empty source filename, and contains pages.
- Page belongs to a Document; page number is a **positive integer**.
- Chunk belongs to a Page; has positive `chunkPageNumber`, zero-or-higher `chunkIndex`, text, embedding JSON string, and associated SKOS concepts.
- Chunk text must be present, non-empty **and contain at least one non-whitespace character** (`sh:pattern "\\S"`).
- SKOS concepts must have a non-empty `skos:prefLabel`.

These shapes validate graph structure. They do **not** prove that embedding JSON is a valid numeric vector or that chunk page numbers equal their parent page numbers in every arbitrary imported graph. The ingestion code checks vector values and generates consistent page numbers. The Python E2 query also rejects corrupted embedding JSON. These checks are complementary rather than equivalent.

## 2. Automated tests

```powershell
python -m pytest -q
```

Core E1 regression cases:

- Existing E1 tests: PDF page preservation, RDF graph construction, upload endpoints, duplicate PDF behaviour, and SHACL page rejection.
- `tests/test_retriever_contract.py`: correct course filtering, topic filtering, complete citations, numeric embeddings, and SPARQL injection-safe topic binding; malformed stored vectors raise an error.
- `tests/test_shacl_rejections.py`: real **negative** pySHACL cases for missing chunk page number, missing Page page number, empty chunk text, whitespace-only text, missing text, missing page relationship, and missing SKOS topic label. The negative tests mutate **in-memory** graphs and assert the saved graph remains valid.
- `tests/test_app.py`: new HTTP chunks endpoint checks pagination, topic filter, default omission of embeddings, `include_embeddings=1`, and input error responses.

`pytest.importorskip("pyshacl")` and `pytest.importorskip("flask")` allow PDF/SPARQL-only tests to run in a minimal environment. **Any skipped tests mean SHACL/API integration has *not* been proven in that environment**. Your Windows `.venv` has already run the old 14 tests; the extra cases in this update must be rerun there before claiming full coverage.

## 3. Evidence using an actual uploaded RDF graph

First upload your course PDF via the app. Then stop the server or open a second terminal, and run:

```powershell
python scripts/verify_e1.py --course SEN0414
```

The script is **read-only** with respect to `data/graph.ttl`; its intentionally broken graphs exist only in memory. Expect statements like:

```text
Saved graph SHACL conforms: True
SPARQL chunks: <N> (course=SEN0414, topic=*)
  <PDF filename> p.<number>, chunk=<index>, embedding_dim=<dimension>
SHACL rejects missing chunk page number: True
SHACL rejects blank chunk text: True
SHACL rejects whitespace-only chunk text: True
```

Outputs above are *expected format*, not a claim that this verification was run on your private `data/graph.ttl` in this workspace. A failure returns a nonzero exit status.

## 4. Before the Git commit

```powershell
git status --short
git check-ignore -v data/graph.ttl
python -m pytest -q
python scripts/verify_e1.py --course SEN0414
git diff --check
```

Do not commit any `data/`, `models/` or `.venv/` files. Test results and true evidence belong in the Workbench work log with your own commit URL. Do not backdate entries.
