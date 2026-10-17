# CourseGraph: a knowledge-graph assistant that answers questions from course PDFs with cited sources

SEN0414 Advanced Programming · 2026-2027 Fall · Proposal · Method: BRSF software-development profile · Self-assessed grade 98.1/100

## Team, roles and work distribution

| Member | Student number | E-mail | Administrative roles | Development roles | Planned share |
| --- | --- | --- | --- | --- | --- |
| Melisa Zeynep Sarıgüzel | 2300008095 | 2300008095@stu.iku.edu.tr | Team lead, Customer liaison, Documentation lead, Quality lead | Requirements analyst, AI and language-model engineer | 34% |
| Ahmet Celal Koç | 2200005171 | 2200005171@stu.iku.edu.tr | Process facilitator | Knowledge engineer, Back-end developer, Architect | 33% |
| M. Ammar Cashlan | 2200002676 | 2200002676@stu.iku.edu.tr | Work-log steward, Repository and release manager | Front-end developer, Test engineer, Release and operations | 33% |

### Modules and features

| Module or feature | Kind | What it does | Delivers epic | Responsible member | Second member |
| --- | --- | --- | --- | --- | --- |
| PDF ingestion and graph builder | Module | Reads uploaded PDFs, splits them into pages and chunks, and writes them to the RDF graph with their embeddings |  | Ahmet Celal Koç · 2200005171 | Melisa Zeynep Sarıgüzel · 2300008095 |
| Course ontology and SHACL shapes | Module | The document, page, chunk and topic model, the SKOS topic scheme and the shapes every uploaded file must pass |  | Ahmet Celal Koç · 2200005171 | M. Ammar Cashlan · 2200002676 |
| Hybrid retriever and answer service | Module | Filters chunks with SPARQL, ranks them by embedding similarity, asks the local LLM for an answer and attaches page citations |  | Melisa Zeynep Sarıgüzel · 2300008095 | Ahmet Celal Koç · 2200005171 |
| Quality report and evaluation set | Feature | The 50-question evaluation set and the /report page with Recall@3, citation accuracy and answer time |  | Melisa Zeynep Sarıgüzel · 2300008095 | M. Ammar Cashlan · 2200002676 |
| Student web interface | Feature | The single Flask page to upload PDFs, choose a course, ask a question and open each cited page |  | M. Ammar Cashlan · 2200002676 | Melisa Zeynep Sarıgüzel · 2300008095 |
|  | Module | pytest cases for every story and the GitHub Actions workflow that runs them and the SHACL check on every push |  | M. Ammar Cashlan · 2200002676 | Ahmet Celal Koç · 2200005171 |

### Process leads

- Mission analysis: Melisa Zeynep Sarıgüzel
- Stakeholder needs and requirements: Melisa Zeynep Sarıgüzel
- System/software requirements definition: Melisa Zeynep Sarıgüzel
- Architecture definition: Ahmet Celal Koç
- Design definition: Ahmet Celal Koç
- System analysis: Ahmet Celal Koç
- Integration: Ahmet Celal Koç
- Implementation: Ahmet Celal Koç
- Verification: M. Ammar Cashlan
- Transition: M. Ammar Cashlan
- Validation: Melisa Zeynep Sarıgüzel
- Operation: M. Ammar Cashlan
- Maintenance: M. Ammar Cashlan
- Disposal: M. Ammar Cashlan

### Work log

7 entries; chain intact; head fingerprint 9a8b0f9fdc36c8631092b7ff57c485b965b2f72ee732ad9c4c43bd2bdce8c338.

| No. | Time (UTC) | Member | Process | Hours | What | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17 16:49 | Melisa Zeynep Sarıgüzel | System/software requirements definition | 1.25 | Talked to classmates about how they revise from course PDFs |  |
| 2 | 2026-10-17 16:50 | Melisa Zeynep Sarıgüzel | System/software requirements definition | 1.25 | Wrote the mission, problem, goals and stories in the proposal workbench |  |
| 3 | 2026-10-17 16:51 | Ahmet Celal Koç | System analysis | 1.5 | Reviewed the pdf-ai-query prototype code and listed what it cannot do |  |
| 4 | 2026-10-17 16:51 | Ahmet Celal Koç | Design definition | 1.5 | Drafted the document, page, chunk and topic classes for the graph |  |
| 5 | 2026-10-17 16:55 | M. Ammar Cashlan | Transition | 1 | Created the GitHub repository and invited the team and the instructor |  |
| 6 | 2026-10-17 16:55 | M. Ammar Cashlan | Verification | 1.5 | Wrote the definition of done and the test cases for each story |  |
| 7 | 2026-10-17 17:41 | Melisa Zeynep Sarıgüzel | Mission analysis | 1 | Defined the project mission, end users and scope for the CourseGraph proposal |  |

## 1. Mission

### Customer

| Customer (organisation or role) | Contact person or role | How and when you reached them | Relation | What they get from it |
| --- | --- | --- | --- | --- |
| Güray Tahan | Güray Tahan, Computer Engineering student at İKÜ | WhatsApp message and short follow-up chat, 10 October 2026 | Client who orders it | a study assistant that answers questions from their own course PDFs and shows the page each answer comes from |
| Hasan Mert Yıldırım | Hasan Mert Yıldırım, Computer Engineering student at İKÜ | WhatsApp message and short follow-up chat, 13 October 2026 | Client who orders it | a study assistant that answers questions from their own course PDFs and shows the page each answer comes from |
| Nida Akın | Nida Akın, Computer Engineering student at İKÜ | WhatsApp message and short follow-up chat, 15 October 2026 | Client who orders it | a study assistant that answers questions from their own course PDFs and shows the page each answer comes from |
| Mahfouz Khalil | Mahfouz Khalil, Computer Engineering student at İKÜ | WhatsApp message and short follow-up chat, 16 October 2026 | Client who orders it | a study assistant that answers questions from their own course PDFs and shows the page each answer comes from |

### End users

| User group (short name) | Who exactly | What they do with the system | How often | Device or channel |
| --- | --- | --- | --- | --- |
| Course student | İKÜ undergraduate students who study from the lecture slides and notes published on CATS | uploads the PDFs of a course and asks questions while revising, then opens the cited pages | Weekly | laptop browser |
| Study group lead | a student who organises a study group for one course and shares material with classmates | uploads the full PDF set of a course once and checks that answers cite the right slides | Weekly | laptop browser |

### Problem

Students in the Computer Engineering department revise from the lecture PDFs each course publishes on CATS. A fourth-year student typically takes five or six courses, and each course publishes around 10 to 14 slide decks and notes per term, so a single student revises from roughly 60 to 80 PDFs and several hundred pages. To find where a concept such as third normal form or a Fourier transform property is explained, students open files one by one and use the viewer's word search, which only finds exact words and misses slides that explain the idea in other terms. Classmates we talked to estimated that, in exam weeks, finding the right slide for one question takes about 5 to 10 minutes. General chatbots answer quickly but do not use the course's own material, mix in other definitions, and cannot show which slide an answer comes from, so students cannot trust them for the exam. Our earlier prototype indexes only one PDF placed in a folder, must be re-run by hand for every new file, and returns one matching paragraph without a generated answer or a page reference.

### Mission statement

Give every Course student and Study group lead at İKÜ a local assistant that turns their course PDFs into a knowledge graph of documents, pages and topics, answers their questions only from that graph with the page each statement comes from, and refuses when the documents do not cover the question.

Origin: Derived

### Outcome

A student uploads the PDFs of a course from one web page, asks a question in their own words and, within seconds, reads an answer whose every part links to the document and page it came from; when the material does not cover the question, the assistant says so instead of guessing.

## 2. Scope

### Areas

| Area | Where it lives | How big it is today |
| --- | --- | --- |
| Course-document knowledge graph | ingest/ and graph/ | prototype stores one PDF as a JSON list of vectors |
| Retrieval and grounded answering | assistant/ | prototype returns one matching chunk, no answer, no page reference |
| Web interface and quality report | web/ and tests/ | prototype has one Flask page; no tests, no metrics |

### Deliverables

| Deliverable | Area | Layer | Kind |
| --- | --- | --- | --- |
| PDF upload and ingestion into an RDF graph of documents, pages and chunks | Course-document knowledge graph | Product layer | Functional |
| Course ontology with a SKOS topic scheme and SHACL shapes | Course-document knowledge graph | Product layer | Functional |
| Hybrid retrieval (SPARQL filter plus embedding similarity) returning the top 3 chunks with page numbers | Retrieval and grounded answering | Product layer | Functional |
| Local LLM answer through Ollama with page citations and a PROV-O record | Retrieval and grounded answering | Product layer | Functional |
| An answer is returned in under 10 seconds for 90% of test questions on a student laptop | Retrieval and grounded answering | Product layer | Non-functional |
| Single web page for upload, questions and the /report quality page | Web interface and quality report | Product layer | Functional |
| pytest suite, 50-question evaluation set and GitHub Actions workflow | Web interface and quality report | Work layer | Non-functional |

### Exclusions

| Left out | Why |
| --- | --- |
| Cloud LLM APIs such as hosted chat models | documents and questions stay on the student's computer and the tool must be free to run |
| OCR of scanned PDFs without a text layer | text recognition is a separate problem; such files are refused with a clear message |
| User accounts and sharing between students | the tool runs locally for one student at a time |
| Publishing or redistributing course PDFs | the material belongs to the lecturers; files stay on the student's own machine |

### Domain entities

| Entity | What it is | Created? | Used? | Retired? |
| --- | --- | --- | --- | --- |
| Document | one uploaded course PDF with its course code, title and file fingerprint | Created — yes | Used — yes | Retired — yes |
| Page | one page of a document with its page number and extracted text | Created — yes | Used — yes | Retired — yes |
| Chunk | a passage of a page with its embedding, the unit that retrieval returns | Created — yes | Used — yes | Retired — yes |
| Topic | a SKOS concept of the course, such as normalization, linked to the chunks that discuss it | Created — yes | Used — yes | Retired — no |
| Answer | a generated reply to one question with the citations it rests on | Created — yes | Used — yes | Retired — no |

### Project kinds

Semantic search and question answering; Semantic search and question answering › Knowledge-graph assistant. Stack layers they need: AI and knowledge graphs, Query, Vocabularies and taxonomies.

### Semantic technologies, by stack layer

- AI and knowledge graphs: GraphRAG pattern
- Data model: RDFLib
- Provenance and metadata: PROV-O provenance ontology
- Query: SPARQL 1.1 and 1.2
- Serialisation: RDFLib
- Validation: SHACL shapes, pySHACL
- Vocabularies and taxonomies: SKOS concept schemes

RDFLib stores every document, page and chunk as RDF triples, so a chunk always knows its document, page and course. A SKOS concept scheme holds each course's topics and links them to chunks. SHACL shapes, run with pySHACL, refuse a file whose pages have no text or whose chunks miss a page number, so the assistant never cites a broken source. SPARQL selects the candidate chunks of the chosen course and topic before embedding similarity ranks them, which is the GraphRAG pattern. PROV-O records which chunks, model and question produced each answer, so any answer can be traced back.

## 3. Goals

| Goal | Facing | Covers area | Why this goal |
| --- | --- | --- | --- |
| Students get correct answers that cite the course page they come from | Mission-facing | Retrieval and grounded answering | this is the change our classmates asked for |
| Every uploaded PDF becomes a valid graph of pages, chunks and topics | Scope-facing | Course-document knowledge graph | an answer can only be as good as the graph behind it |
| Students upload, ask and see answer quality from one web page | Scope-facing | Web interface and quality report | the prototype needed scripts run by hand for each new file |
| No document, question or answer leaves the student's computer | Containment-facing | Retrieval and grounded answering | course material belongs to the lecturers and must not go to outside services |

### Specification

The system lets a student upload course PDFs from a web page, extracts the text of every page, splits pages into chunks, computes an embedding for each chunk and stores documents, pages, chunks and topics in an RDF graph validated by SHACL shapes. For each question it selects candidate chunks with SPARQL by course and topic, ranks them by embedding similarity, sends the top three to a local LLM through Ollama and returns an answer with the document and page of each cited chunk. It records every answer with PROV-O. When no chunk is similar enough it says that the documents do not cover the question and gives no answer.

### Test scenarios

| Kind | Scenario (Given / When / Then) |
| --- | --- |
| Nominal | Given a lecture PDF that explains normalization is uploaded, when the student asks what third normal form is, then the answer cites the document and pages of the three chunks it used |
| Rejection | Given uploaded PDFs of a databases course, when the student asks about a topic none of them covers, then the assistant says no source was found and gives no answer |
| Rejection | Given a scanned PDF with no text layer, when the student uploads it, then the file is refused and the message says it contains no text |

### Use cases

Course student: upload PDFs, ask a question, open a cited page. Study group lead: upload a course's PDF set, filter by course, read the quality report.

## 4. Objectives

| Objective | Goal | Measured by | How exactly it is measured | Now | Target | Direction |
| --- | --- | --- | --- | --- | --- | --- |
| Answers whose cited pages support the answer | Students get correct answers that cite the course page they come from | Judged | share of answers on the 50-question set where two team members agree the cited pages support the answer, % | 0 (the prototype cites no page) | 85 | Increase |
| Recall@3 on the evaluation set | Students get correct answers that cite the course page they come from | Derived | share of the 50 questions whose expected page is among the top 3 retrieved chunks, computed by the evaluation script | not measurable (the prototype returns only one chunk) | 0.80 | Increase |
| Test PDFs that pass the shapes | Every uploaded PDF becomes a valid graph of pages, chunks and topics | Counted | share of the 20 test PDFs with a text layer whose graph passes pySHACL, % | 0 | 100 | Increase |
| Steps from a new PDF to a cited answer | Students upload, ask and see answer quality from one web page | Counted | user actions needed to get an answer from a newly added PDF | 4 (copy file, run embed.py, restart app, ask) | 2 (upload, ask) | Decrease |
| Requests to outside services during a session | No document, question or answer leaves the student's computer | Counted | outgoing network connections other than to localhost logged during a full test run | 0 | 0 | Hold |

### Activity model

The student opens the page and uploads a PDF. The system extracts its text; if a page has no text the file is refused with a message. Otherwise it splits pages into chunks, computes embeddings, links chunks to topics and validates the graph with SHACL; on a violation the upload is rolled back and reported. The student chooses a course and asks a question. The retriever selects and ranks chunks; if none is similar enough the assistant says no source was found. Otherwise the LLM writes an answer from the top three chunks, citations are attached, the answer is recorded with PROV-O and shown.

### Sequence model

The web page sends the question and course to the answer service. The answer service sends a SPARQL query to the graph store and receives the candidate chunks of that course. It asks the embedding model for the question vector, ranks the candidates and keeps the top three. It sends the question and the three chunks to Ollama and receives the draft answer. It writes a PROV-O record to the graph and returns the answer with document titles and page numbers to the web page, which shows each citation as a link to the page.

## 5. Backlog

Kind of development: Evolutionary development

### Epics

| Epic | Pursues objective |
| --- | --- |
| Build the course-document knowledge graph | Test PDFs that pass the shapes |
| Answer questions with cited sources | Answers whose cited pages support the answer |
| One-page workflow and quality report | Steps from a new PDF to a cited answer |

### Stories

| Epic | As a | I want | So that | Acceptance (Given / When / Then) | Category | Design concern | Value 1–10 | Time 1–10 | Risk 1–10 | Size 1–10 | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Build the course-document knowledge graph | Course student (end user) | to upload a lecture PDF from the web page | I do not have to run scripts by hand for every new file | Given a 40-page lecture PDF When I upload it Then its pages and chunks are added to the graph and the page shows the file as ready | New capability | Interaction | 8 | 6 | 5 | 5 | 3.8 |
| Build the course-document knowledge graph | Study group lead (end user) | to be told when a file cannot be indexed | I can replace it with a version that has text | Given a scanned PDF with no text layer When I upload it Then it is refused and the message says the file contains no text | New capability | Data | 5 | 4 | 6 | 2 | 7.5 |
| Answer questions with cited sources | Course student (end user) | an answer that cites the slides it comes from | I can check it against the course material before the exam | Given an uploaded PDF that explains normalization When I ask what third normal form is Then the answer cites the document and page of each chunk it used | New capability | Architecture | 10 | 8 | 7 | 8 | 3.1 |
| Answer questions with cited sources | Course student (end user) | the assistant to say when my documents do not cover a question | I am never given an invented answer | Given uploaded PDFs of a databases course When I ask about a topic none of them covers Then the assistant says no source was found and gives no answer | New capability | Architecture | 9 | 6 | 8 | 3 | 7.7 |
| Answer questions with cited sources | Study group lead (end user) | to limit answers to one course | answers do not mix material from different courses | Given PDFs from two courses When I choose SEN5016 and ask a question Then every cited chunk comes from a SEN5016 document | New capability | Data | 6 | 4 | 4 | 4 | 3.5 |
| One-page workflow and quality report | Study group lead (end user) | a quality report of the assistant | I can tell my group how far to trust it | Given the 50-question evaluation set When I open the report page Then I see Recall@3, citation accuracy and median answer time | New capability | User interface | 6 | 3 | 5 | 3 | 4.7 |

### Definition of done

| Criterion | How it is checked |
| --- | --- |
| All tests pass in continuous integration | GitHub Actions run pytest on every push |
| The graph built from the test PDFs conforms to the shapes | pySHACL report in the pipeline log |
| The story's acceptance criterion is shown working | a test named after the story or a short recorded demo |

### Class model

Document has a course code, a title, a file fingerprint and many Pages. Page has a page number and text and belongs to one Document. Chunk has text, an embedding and a position and belongs to one Page; a Chunk may discuss several Topics. Topic is a skos:Concept in the course's concept scheme. Question has a text and a chosen course. Answer has a text, a model name and many Citations, and is a prov:Entity generated from one Question. Citation links an Answer to one Chunk.

### Test cases

| For story | Test case | Test data |
| --- | --- | --- |
| to upload a lecture PDF from the web page | upload a 40-page sample PDF and count pages and chunks in the graph | one sample lecture PDF |
| to be told when a file cannot be indexed | upload a scanned PDF and expect a refusal naming the missing text | one image-only PDF |
| an answer that cites the slides it comes from | ask ten questions with known pages and check every answer cites a retrieved chunk | ten questions from the evaluation set |
| the assistant to say when my documents do not cover a question | ask five off-topic questions and expect the no-source reply | five questions outside the uploaded PDFs |
| to limit answers to one course | upload PDFs of two courses, filter one and check all citations | two small course PDF sets |
| a quality report of the assistant | run the evaluation and compare the report figures with the script output | the 50-question evaluation set |

### Architecture — Component diagram

Design-level class diagram: Document, Page, Chunk, Topic (skos:Concept), Question, Answer (prov:Entity) and Citation as in the class model; DocumentShape requires a course code and at least one Page, PageShape requires non-empty text and a page number, ChunkShape requires a Page and an embedding.

### Data — Class diagram

Component diagram: WebPage (Flask) calls IngestService and AnswerService; IngestService uses PyPDF, the embedding model and Validator (pySHACL) and writes to GraphStore (RDFLib); AnswerService queries GraphStore with SPARQL, calls the embedding model and the local LLM through Ollama, and writes PROV-O records; Evaluator runs the question set through AnswerService.

### Interaction — Sequence diagram

Sequence of an upload: the student drops a PDF on the page; the page sends it to IngestService; IngestService extracts the text, builds pages and chunks, validates them and either stores them and returns ready, or rolls back and returns the reason; the page updates the document's status.

### User interface — design model

One page in three parts: an upload area listing each document with its course and status (ready or refused with the reason); a question box with a course filter and the answer below it, each citation shown as document title and page number; a report tab with Recall@3, citation accuracy and median answer time.

## 6. Course-specific

### Python libraries and course topics

Python libraries: PyPDF for text extraction, sentence-transformers for embeddings, RDFLib and pySHACL for the graph and its validation, Flask for the web page, the ollama client for the local model, and pytest for tests. Course topics applied: files and paths (pathlib) for the document folder, regular expressions to clean extracted text and read course codes from file names, reading PDF documents, web pages with Flask, multithreading to index several PDFs at once, and openpyxl to export the evaluation results.

## Plan and risks

| Date | Deliverable | Lead |
| --- | --- | --- |
| 2026-10-31 | Ingestion into the RDF graph with ontology and SHACL shapes | Ahmet Celal Koç |
| 2026-11-20 | Hybrid retrieval and cited answers through Ollama | Melisa Zeynep Sarıgüzel |
| 2026-12-04 | Web page and /report quality page with the evaluation set | M. Ammar Cashlan |
| 2026-12-06 | Tagged release v1.0.0 with test report | M. Ammar Cashlan |

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| The local LLM is too slow on student laptops | Medium | Medium | use a small model, cache embeddings and measure answer time on every release |
| The LLM states things the cited chunks do not support | High | High | answer only from the top three chunks, refuse below a similarity threshold, and judge citation accuracy on the evaluation set |
| Extracted PDF text is messy (tables, formulas, slide layouts) | Medium | Medium | clean text with regular expressions and test with PDFs from three different courses |
| A member has less time near exam weeks | Medium | Medium | every module has an owner and a second member who can take it over |

Repository: https://github.com/swammar7/PDF-AI-Query-PDF-Sorgulama-Sistemi — Confirmed on GitHub 2026-10-17 (public, created 2026-10-17)

## References

1. Sarıgüzel, M. Z. (2025). pdf-ai-query: semantic search over a PDF with Sentence Transformers. GitHub repository, https://github.com/MelisaZS/pdf-ai-query (prototype this project evolves from).
2. Sweigart, A. (2025). Automate the Boring Stuff with Python, 3rd ed. No Starch Press.
3. Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. Advances in Neural Information Processing Systems 33 (NeurIPS 2020).
4. Reimers, N. & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. Proceedings of EMNLP-IJCNLP 2019.
5. W3C (2014). RDF 1.1 Concepts and Abstract Syntax. W3C Recommendation.
6. W3C (2017). Shapes Constraint Language (SHACL). W3C Recommendation.
7. W3C (2013). PROV-O: The PROV Ontology. W3C Recommendation.

## Self-assessment

| Part | Weight | Grade | Criteria met |
| --- | --- | --- | --- |
| Team and work | 10% | 81/100 | 10 of 12 |
| Mission | 20% | 100/100 | 7 of 7 |
| Scope | 15% | 100/100 | 8 of 8 |
| Goal | 15% | 100/100 | 7 of 7 |
| Objective | 10% | 100/100 | 3 of 3 |
| Backlog | 20% | 100/100 | 10 of 10 |
| Course-specific | 5% | 100/100 | 1 of 1 |
| Plan and references | 5% | 100/100 | 3 of 3 |
| Overall | 100% | 98.1/100 |  |

### Member grades (Proposal)

Project grade 100 (60%), team grade 81 (20%), individual contribution (20%).

| Member | Student number | Individual | Member grade |
| --- | --- | --- | --- |
| Melisa Zeynep Sarıgüzel | 2300008095 | 100 | 96.2 |
| Ahmet Celal Koç | 2200005171 | 100 | 96.2 |
| M. Ammar Cashlan | 2200002676 | 100 | 96.2 |

