# CourseGraph E2: Hybrid Retrieval, Cited Answers and Provenance

**Owner:** Melisa (E2: hybrid retriever, Ollama answer service, citations, PROV-O)
**Builds on:** [E1 integration contract](E1_INTEGRATION.md) (Ahmet): `GraphStore.get_course_chunks()`
**Branch:** `feature/e2-retriever`

E2 turns a student's question into an answer that uses only the uploaded slides of the selected course. Each answer names the pages it is based on and is stored as PROV-O. The documents, the question and the answer never leave the computer.

## 1. Flow

```text
question + course
      │
      ▼
HybridRetriever ── SPARQL (E1) ──▶ chunks of that course (+ optional SKOS topic)
      │            local MiniLM ──▶ question vector
      │            cosine ranking ─▶ top-3 with score ≥ 0.35
      │
      ├── no chunk above threshold ──▶ "No source was found…"   (LLM is NOT called)
      ▼
AnswerService ── prompt with [1] [2] [3] ──▶ Ollama on localhost (qwen2.5:3b)
      │
      ├── model replies NO_ANSWER      ──▶ "No source was found…"
      ├── Ollama not reachable         ──▶ warning + matching pages are still shown
      ▼
answer text with [n] citations
      │
      ├──▶ ProvenanceRecorder ──▶ SHACL (E2 shapes) ──▶ data/provenance.ttl
      └──▶ web page: citation cards, "Open page ↗" ──▶ /documents/<key>.pdf#page=n
```

| Module | Responsibility |
|---|---|
| `coursegraph/retriever.py` | `HybridRetriever.retrieve(question, course_id, topic=None)` → `RetrievalResult` (hits, best score, `covered`) |
| `coursegraph/answer_service.py` | `OllamaClient` (localhost only), `AnswerService.answer()` → `Answer`, `Answer.to_view()` for the template |
| `coursegraph/provenance.py` | `ProvenanceRecorder.record(answer)`: builds PROV-O triples, validates them, appends to `data/provenance.ttl` |
| `app.py` | Wires the three together; `/documents/<key>.pdf` serves the cited PDF |
| `ontology/coursegraph.ttl`, `ontology/shapes.ttl` | E2 classes, properties and SHACL shapes (appended below E1) |

## 2. Retrieval

1. **Filter (SPARQL):** `store.get_course_chunks(course, topic=topic)` returns only the chunks of the selected course. Other courses' slides can never appear in an answer.
2. **Encode:** the question is encoded with the same local `all-MiniLM-L6-v2` model used during ingestion. A dimension mismatch raises an error instead of returning wrong results.
3. **Rank:** cosine similarity between the question vector and every candidate chunk; the order is stable for equal scores.
4. **Select:** the best `top_k = 3` chunks whose score is at least `min_similarity = 0.35`. If none qualify, `covered` is `False`.

The threshold `0.35` is a starting value for MiniLM cosine scores. It will be tuned with the 50-question evaluation set: too high rejects answerable questions, too low lets unrelated pages through.

## 3. Answer generation

- **Model:** `qwen2.5:3b` through Ollama (`http://127.0.0.1:11434/api/generate`, `stream: false`, `temperature: 0`). Small enough for a laptop and the 10-second target.
- **Prompt rules:** answer only from the numbered sources, cite after every sentence as `[1]`, `[2][3]`, reply exactly `NO_ANSWER` if the sources do not contain the answer, no outside knowledge, answer in the language of the question.
- **Grounding guarantees:**
  - no sources above the threshold → the model is not called at all;
  - model says `NO_ANSWER` → the same "no source" reply, no citations;
  - each citation records whether its number actually appears in the answer text (`cited` / `cg:usedInAnswerText`).
- **Privacy:** `OllamaClient` refuses any host other than `127.0.0.1`, `localhost` or `::1`.
- **Failure handling:** if Ollama is not running, the page shows a warning with the command to fix it (`ollama pull qwen2.5:3b`) and still lists the matching pages.

## 4. Provenance (PROV-O)

```text
cg:Question ──cg:askedForCourse──▶ cg:Course
     ▲
     │ prov:used                              prov:wasAssociatedWith
cg:AnswerGeneration ─────────────────────────────────────────▶ cg:LanguageModel (cg:modelName)
     │  prov:used ──▶ cg:Chunk (each cited chunk)
     │  cg:responseTimeMs
     ▲
     │ prov:wasGeneratedBy
cg:Answer ── cg:answerText, cg:covered, prov:generatedAtTime, cg:answersQuestion ──▶ cg:Question
     │
     └─cg:hasCitation──▶ cg:Citation ── cg:citationNumber (1–3), cg:similarityScore,
                                         cg:usedInAnswerText, cg:citesChunk ──▶ cg:Chunk
```

- `cg:Question` and `cg:Answer` are `prov:Entity`, `cg:AnswerGeneration` is a `prov:Activity`, `cg:LanguageModel` is a `prov:SoftwareAgent`.
- Records are stored in `data/provenance.ttl` (ignored by Git), separate from `data/graph.ttl`, so asking a question never rewrites the document graph.
- Before saving, only the E2 shapes are run (`QuestionShape`, `AnswerShape`, `CitationShape`, `AnswerGenerationShape`, `LanguageModelShape`). They require answer text and `covered`, at most three citations numbered 1–3, and that every citation points to an existing `cg:Chunk`.
- A record that fails validation is not saved; the answer is still shown and a warning is logged.

Trace an answer back to its pages (load `graph.ttl` and `provenance.ttl` into one RDFLib graph):

```sparql
PREFIX cg:   <https://coursegraph.local/ontology#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?question ?answer ?n ?filename ?page ?score ?model
WHERE {
  ?a a cg:Answer ; cg:answerText ?answer ; cg:answersQuestion ?q ;
     prov:wasGeneratedBy ?run ; cg:hasCitation ?c .
  ?q cg:questionText ?question .
  ?run prov:wasAssociatedWith ?m . ?m cg:modelName ?model .
  ?c cg:citationNumber ?n ; cg:similarityScore ?score ; cg:citesChunk ?chunk .
  ?chunk cg:chunkPageNumber ?page ; cg:belongsToPage/cg:belongsToDocument ?doc .
  ?doc cg:sourceFilename ?filename .
}
ORDER BY ?question ?n
```

## 5. Running it locally

```bash
pip install -r requirements.txt          # no new Python dependency for E2
ollama pull qwen2.5:3b                   # once
ollama serve                             # if Ollama is not already running
python app.py                            # http://127.0.0.1:5000
```

Optional environment variables: `COURSEGRAPH_OLLAMA_MODEL` (default `qwen2.5:3b`), `COURSEGRAPH_OLLAMA_HOST` (default `http://127.0.0.1:11434`, must stay local).

Choose a course, ask a question, and use **Open page ↗** on a citation card to open the PDF at the cited page.

## 6. Tests (Definition of Done)

All E2 tests run without Ollama: the model is replaced by a fake, and the HTTP client is tested with a mocked `urlopen`.

| Story | Tests |
|---|---|
| An answer that cites the slides it comes from | `test_retriever.py`, `test_answer_service.py`: `test_an_answer_that_cites_the_slides_it_comes_from` |
| The assistant says when my documents do not cover a question | `test_retriever.py`, `test_answer_service.py`: `test_the_assistant_says_when_my_documents_do_not_cover_a_question`; `test_model_saying_no_answer_becomes_no_source_reply` |
| To limit answers to one course | `test_retriever.py`: `test_to_limit_answers_to_one_course`; `test_app_e2.py`: `test_question_without_course_is_not_answered_or_recorded` |
| Open the cited page | `test_app_e2.py`: `test_citations_open_the_pdf_at_the_cited_page`, `test_pdf_route_rejects_invalid_keys` |
| Every answer is traceable to its sources | `test_provenance.py`, `test_app_e2.py`: `test_every_answer_is_traceable_to_its_sources`; `test_citation_to_unknown_chunk_is_rejected`; `test_more_than_three_citations_are_rejected` |
| Data stays on the computer | `test_answer_service.py`: `test_ollama_client_only_accepts_localhost`, `test_ollama_client_sends_local_request_and_reads_reply` |

```bash
python -m pytest -q
```

## 7. Known limitations and next steps

- The 0.35 threshold and `qwen2.5:3b` are not yet measured; the 50-question evaluation set (Recall@3, citation accuracy, median answer time, 90 % under 10 s) will decide both.
- `/report` still shows placeholder metrics until `scripts/evaluate.py` writes real results.
- Ranking is cosine-only within the SPARQL-filtered set; the topic filter is used only when a topic is passed.
- `data/provenance.ttl` grows with every question and is rewritten on each save; this is acceptable for one student's usage.
