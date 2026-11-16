"""E2 provenance: store every answer as PROV-O in a local RDF file.

Each answer becomes:
    cg:Question       (question text, course)
    cg:AnswerGeneration  prov:used the question and the cited chunks,
                         prov:wasAssociatedWith the cg:LanguageModel
    cg:Answer         prov:wasGeneratedBy the generation, cg:hasCitation ...
    cg:Citation       one per retrieved chunk (number, score, used in text)

Answers are kept in data/provenance.ttl, next to graph.ttl, so asking a
question never rewrites the document graph. Before saving, the new triples are
validated against the E2 shapes (QuestionShape, AnswerShape, CitationShape,
AnswerGenerationShape, LanguageModelShape) from ontology/shapes.ttl.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import tempfile
import uuid

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SH, XSD

from .graph_store import CG, _LOCK, _resource

PROV = Namespace("http://www.w3.org/ns/prov#")
E2_CLASSES = (CG.Question, CG.Answer, CG.Citation, CG.AnswerGeneration, CG.LanguageModel)


class ProvenanceError(ValueError):
    """The answer record did not pass the E2 SHACL shapes."""


class ProvenanceRecorder:
    def __init__(self, store, provenance_path: str | Path | None = None) -> None:
        self.store = store
        self.path = Path(provenance_path or Path(store.graph_path).with_name("provenance.ttl"))
        self._shapes = None

    def load(self) -> Graph:
        graph = Graph()
        graph.bind("cg", CG)
        graph.bind("prov", PROV)
        if self.path.exists():
            graph.parse(self.path, format="turtle")
        return graph

    def answer_count(self) -> int:
        return sum(1 for _ in self.load().subjects(RDF.type, CG.Answer))

    def record(self, answer, *, generated_at: datetime | None = None) -> str:
        """Validate and append one answer; returns the answer URI."""
        new = self._build(answer, generated_at or datetime.now(timezone.utc))
        self._validate(new)
        with _LOCK:
            graph = self.load()
            graph += new
            self._save(graph)
        return str(next(new.subjects(RDF.type, CG.Answer)))

    def _build(self, answer, generated_at: datetime) -> Graph:
        g = Graph()
        run_id = uuid.uuid4().hex
        question_uri = _resource("question", run_id)
        answer_uri = _resource("answer", run_id)
        generation_uri = _resource("generation", run_id)
        model_name = str(answer.model or "unknown")
        model_uri = _resource("model", hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:16])
        course_uri = _resource("course", answer.course_id)

        g.add((question_uri, RDF.type, CG.Question))
        g.add((question_uri, CG.questionText, Literal(answer.question, datatype=XSD.string)))
        g.add((question_uri, CG.askedForCourse, course_uri))

        g.add((model_uri, RDF.type, CG.LanguageModel))
        g.add((model_uri, CG.modelName, Literal(model_name, datatype=XSD.string)))

        g.add((generation_uri, RDF.type, CG.AnswerGeneration))
        g.add((generation_uri, PROV.used, question_uri))
        g.add((generation_uri, PROV.wasAssociatedWith, model_uri))
        g.add((generation_uri, CG.responseTimeMs,
               Literal(max(int(answer.time_ms), 0), datatype=XSD.nonNegativeInteger)))

        g.add((answer_uri, RDF.type, CG.Answer))
        g.add((answer_uri, CG.answerText, Literal(answer.text, datatype=XSD.string)))
        g.add((answer_uri, CG.covered, Literal(bool(answer.covered), datatype=XSD.boolean)))
        g.add((answer_uri, CG.answersQuestion, question_uri))
        g.add((answer_uri, PROV.wasGeneratedBy, generation_uri))
        g.add((answer_uri, PROV.generatedAtTime, Literal(generated_at.isoformat(), datatype=XSD.dateTime)))

        for citation in answer.citations:
            citation_uri = _resource("citation", f"{run_id}/{citation['number']}")
            chunk_uri = URIRef(citation["chunk_uri"])
            g.add((citation_uri, RDF.type, CG.Citation))
            g.add((citation_uri, CG.citesChunk, chunk_uri))
            g.add((citation_uri, CG.citationNumber,
                   Literal(int(citation["number"]), datatype=XSD.positiveInteger)))
            g.add((citation_uri, CG.similarityScore,
                   Literal(Decimal(str(citation["score"])), datatype=XSD.decimal)))
            g.add((citation_uri, CG.usedInAnswerText, Literal(bool(citation["cited"]), datatype=XSD.boolean)))
            g.add((answer_uri, CG.hasCitation, citation_uri))
            g.add((generation_uri, PROV.used, chunk_uri))
        return g

    def _validate(self, new: Graph) -> None:
        from pyshacl import validate

        # sh:class needs the types of the course and chunks that live in graph.ttl.
        data = Graph()
        data += new
        documents = self.store.load_graph()
        for linked in set(new.objects(None, CG.citesChunk)) | set(new.objects(None, CG.askedForCourse)):
            for rdf_type in documents.objects(linked, RDF.type):
                data.add((linked, RDF.type, rdf_type))

        conforms, _report, text = validate(
            data_graph=data, shacl_graph=self._e2_shapes(), inference="none",
            abort_on_first=False, allow_infos=False, allow_warnings=False,
        )
        if not conforms:
            raise ProvenanceError("Answer provenance failed SHACL validation:\n" + str(text))

    def _e2_shapes(self) -> Graph:
        """Only the E2 shapes, so document shapes do not run on every question."""
        if self._shapes is None:
            full = Graph().parse(self.store.shapes_path, format="turtle")
            shapes = Graph()
            for target in E2_CLASSES:
                for shape in full.subjects(SH.targetClass, target):
                    shapes += full.cbd(shape)
            self._shapes = shapes
        return self._shapes

    def _save(self, graph: Graph) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".provenance-", suffix=".ttl", dir=self.path.parent, delete=False,
            ) as target:
                temp_name = target.name
            graph.serialize(destination=temp_name, format="turtle", encoding="utf-8")
            os.replace(temp_name, self.path)
        except Exception:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
            raise
