# CourseGraph E1 → E2 Integration Contract

**Owner:** Ahmet (E1: PDF ingestion, RDF graph, ontology, SHACL)
**Consumer:** Melisa (E2: SPARQL / hybrid retriever, Ollama, citations)
**Target branch:** `semantic_knowledge_graph`
**Scope:** This is the E1 *data interface*. It does **not** implement GraphRAG ranking, Ollama answers, confidence thresholds, or PROV-O answer provenance.

## 1. What is persisted?

PDFs are processed page by page. The RDF graph is stored in `data/graph.ttl` (Turtle). Original PDFs are stored under `data/uploads/`. Both are ignored by Git. Chunk embeddings are computed locally and stored in RDF as a JSON array, in `cg:embeddingJson`.

```text
cg:Course --cg:hasDocument--> cg:Document --cg:hasPage--> cg:Page --cg:hasChunk--> cg:Chunk
                                        (PDF filename)      (pageNumber)    |text, chunkIndex,
                                                                           |chunkPageNumber,
                                                                           |embeddingJson
                                                                           +--cg:hasTopic--> skos:Concept
                                                                                              (skos:prefLabel)
```

Backlinks: `Document cg:belongsToCourse Course`, `Page cg:belongsToDocument Document`, `Chunk cg:belongsToPage Page`.

| RDF class | Required attributes used by E2 |
|---|---|
| `cg:Course` | `skos:prefLabel` (course code) |
| `cg:Document` | `cg:sourceFilename`, `cg:belongsToCourse`, `cg:hasPage` |
| `cg:Page` | `cg:pageNumber` (1-based), `cg:hasChunk` |
| `cg:Chunk` | `cg:text`, `cg:chunkIndex` (0-based within a page), `cg:chunkPageNumber` (1-based), `cg:embeddingJson`, `cg:hasTopic` |
| `skos:Concept` | `skos:prefLabel` (topic name entered during upload) |

**Important:** Topics are upload-provided labels attached to all the document's chunks. This E1 version does **not** detect or classify topics automatically. `skos:Concept` is part of SKOS, not a custom `cg:Topic` class.

## 2. Python contract (recommended for Melisa)

```python
from coursegraph.graph_store import GraphStore

store = GraphStore()  # reads data/graph.ttl in the repository working directory
chunks = store.get_course_chunks("SEN0414")
# Or restrict to a known SKOS topic label (exact match):
rdf_chunks = store.get_course_chunks("SEN0414", topic="RDF")

for item in chunks:
    document = item["filename"]       # e.g. lecture.pdf
    page_number = item["page_number"] # starts at 1
    text = item["text"]
    vector = item["embedding"]        # list[float], ready for a cosine scorer
    chunk_uri = item["chunk_uri"]     # stable RDF resource ID
    topics = item["topics"]           # sorted list[str]
```

Each returned item has exactly these fields:

```json
{
  "course_id": "SEN0414",
  "document_uri": "https://coursegraph.local/resource/document/<hash>",
  "filename": "lecture.pdf",
  "page_number": 3,
  "chunk_uri": "https://coursegraph.local/resource/chunk/<hash>/3/0",
  "chunk_index": 0,
  "text": "... extracted PDF text ...",
  "embedding": [0.12, -0.05, 0.30],
  "topics": ["RDF", "SPARQL"]
}
```

The three example embedding values above are illustrative, **not** the real model's dimension. Existing E1 uses the local `all-MiniLM-L6-v2` model; E2 **must use the same compatible model** to encode the user's question. `get_course_chunks()` returns all matching chunks **without cosine ranking**; E2 ranks and selects top-3 itself. The returned filename and page_number support citations such as `lecture.pdf, s. 3`; use `document_uri` and `chunk_uri` for provenance links.

**SPARQL safety:** The course resource and optional topic label are passed via RDFLib `initBindings`; they are never inserted as unsanitized text into the SPARQL query. Course codes must match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. Topic matching is case-sensitive and exact.

## 3. Raw SPARQL reference query

For someone using RDFLib directly, below is a fixed-code query for the course:

```sparql
PREFIX cg: <https://coursegraph.local/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?document ?filename ?pageNumber ?chunk ?chunkIndex ?text ?embeddingJson
WHERE {
    ?course a cg:Course ; skos:prefLabel "SEN0414" ; cg:hasDocument ?document .
    ?document cg:belongsToCourse ?course ; cg:sourceFilename ?filename ; cg:hasPage ?page .
    ?page cg:pageNumber ?pageNumber ; cg:hasChunk ?chunk .
    ?chunk cg:belongsToPage ?page ; cg:chunkIndex ?chunkIndex ;
           cg:text ?text ; cg:embeddingJson ?embeddingJson .
}
ORDER BY ?filename ?pageNumber ?chunkIndex ?chunk
```

Don't substitute untrusted user text directly into this string. For dynamic selections use `GraphStore.get_course_chunks()` or bound `initBindings` as in the implementation.

## 4. Flask HTTP API

The local Flask app currently exposes:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Local upload interface and legacy, non-E2 search form |
| `POST` | `/upload` | Form upload and redirect |
| `POST` | `/api/upload` | JSON outcome after PDF upload |
| `GET` | `/api/documents` | Documents with course/page/chunk counts |
| `GET` | `/api/courses/<course_id>/chunks` | **New:** course/topic-filtered, paginated chunk metadata |

**Upload request:** `multipart/form-data` with `pdf` file, `course_id` (e.g. `SEN0414`), optional `topics` (e.g. `RDF, SPARQL`). 201 means created; 200 means already exists; 422 indicates PDF/SHACL failure; 400 indicates invalid input; 503 indicates missing local model. **Default server binds `127.0.0.1:5000`, not an external interface.**

**New read API:**

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/api/courses/SEN0414/chunks?topic=RDF&limit=2&offset=0"
```

Response envelope (`embedding` is excluded by default to avoid large HTTP payloads):

```json
{
  "course_id": "SEN0414",
  "topic": "RDF",
  "total": 23,
  "limit": 1,
  "offset": 0,
  "items": [
    {
      "course_id": "SEN0414",
      "document_uri": "https://coursegraph.local/resource/document/<hash>",
      "filename": "lecture.pdf",
      "page_number": 1,
      "chunk_uri": "https://coursegraph.local/resource/chunk/<hash>/1/0",
      "chunk_index": 0,
      "text": "...",
      "topics": ["RDF"]
    }
  ]
}
```

Numbers and text in the sample are **illustrative**; they are not a live API response. `limit` is 1–200 (default 50), `offset` is nonnegative (default 0), and `include_embeddings=1` enables full vectors for paginated items. `total` is the count *after* the optional topic filter but *before* pagination. A missing course returns `total: 0` and an empty `items` array. For E2 in the same Python process, **prefer the Python contract** above to avoid pagination and HTTP overhead.

## 5. E1/E2 handoff boundaries

E1 guarantees, for successfully validated uploads: page-aware chunks, local vector generation, SKOS topic labels, a persistent RDF graph, and queryable data with source metadata. E2 remains responsible for question embedding, ranking top-3 (and minimum-similarity threshold), generating a grounded answer via Ollama, choosing and displaying citations, and recording PROV-O answer lineage. Multi-process RDF writes and authentication are outside this first local deployment.

Contact the E1 owner before changing the `cg:` URI namespace or the returned field names; such changes break the E2 retriever contract.
