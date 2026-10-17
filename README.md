# CourseGraph

A local assistant that turns course PDFs into a knowledge graph and answers students' questions with the document and page each answer comes from.

SEN0414 Advanced Programming · İstanbul Kültür University · 2026–2027 Fall

## Team
- Melisa Zeynep Sarıgüzel (team lead, retrieval and answers)
- Ahmet Celal Koç (ingestion, ontology and SHACL shapes)
- M. Ammar Cashlan (web interface, tests and CI)

## What it does
1. Upload course PDFs from a web page.
2. Pages and chunks are stored in an RDF graph (documents, pages, chunks, SKOS topics) and checked with SHACL.
3. A question is answered from the top 3 chunks (SPARQL filter + embedding similarity) by a local LLM through Ollama.
4. Every answer shows its source document and page; if no source fits, it says so.
5. Answers are recorded with PROV-O; the /report page shows Recall@3, citation accuracy and answer time.

## Stack
Python · Flask · PyPDF · sentence-transformers · RDFLib · pySHACL · SPARQL · SKOS · PROV-O · Ollama · pytest · GitHub Actions

## Background
CourseGraph evolves from the earlier prototype [MelisaZS/pdf-ai-query](https://github.com/MelisaZS/pdf-ai-query), which searched a single PDF with Sentence Transformers.

## Repository layout (planned)
- `ingest/` PDF reading and chunking
- `graph/` ontology, SHACL shapes, graph store
- `assistant/` retrieval and answer service
- `web/` Flask interface and /report page
- `tests/` pytest suite and evaluation set
- `proposal/` course proposal files (Proposal Workbench)

## Status
Proposal stage. Milestones: graph and shapes (31 Oct), cited answers (21 Nov), web page and report (5 Dec), release v1.0.0 (19 Dec).
