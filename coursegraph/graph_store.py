"""Atomic local RDF ingestion for CourseGraph's E1 milestone."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Iterable

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS, XSD

from .pdf_processing import chunk_pages, extract_pages

CG = Namespace("https://coursegraph.local/ontology#")
RESOURCE = "https://coursegraph.local/resource/"
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# A process-local lock is appropriate for a local, single-worker Flask app. A
# multi-worker production deployment would need a transactional RDF store.
_LOCK = threading.RLock()
_COURSE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class GraphValidationError(ValueError):
    """The SHACL report identified an invalid candidate graph."""


def _resource(kind: str, identifier: str) -> URIRef:
    return URIRef(f"{RESOURCE}{kind}/{identifier}")


def _safe_topics(topics: Iterable[str] | None) -> list[str]:
    if isinstance(topics, str):
        topics = topics.split(",")
    cleaned = []
    for topic in topics or []:
        topic = " ".join(topic.split()).strip()
        if topic and len(topic) <= 100 and topic.casefold() not in [s.casefold() for s in cleaned]:
            cleaned.append(topic)
    return cleaned or ["Genel"]


class GraphStore:
    def __init__(
        self,
        graph_path: str | Path = "data/graph.ttl",
        upload_dir: str | Path = "data/uploads",
        ontology_path: str | Path = _PACKAGE_ROOT / "ontology/coursegraph.ttl",
        shapes_path: str | Path = _PACKAGE_ROOT / "ontology/shapes.ttl",
    ) -> None:
        self.graph_path = Path(graph_path)
        self.upload_dir = Path(upload_dir)
        self.ontology_path = Path(ontology_path)
        self.shapes_path = Path(shapes_path)

    def load_graph(self) -> Graph:
        g = Graph()
        g.bind("cg", CG)
        g.bind("skos", SKOS)
        if self.graph_path.exists():
            g.parse(self.graph_path, format="turtle")
        else:
            g.parse(self.ontology_path, format="turtle")
        return g

    def validate_graph(self, graph: Graph) -> tuple[bool, str]:
        # Import at usage rather than import time to allow PDF-only workflows.
        from pyshacl import validate

        conforms, _report_graph, report_text = validate(
            data_graph=graph,
            shacl_graph=str(self.shapes_path),
            inference="none",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
        )
        return bool(conforms), str(report_text)

    def list_documents(self) -> list[dict]:
        graph = self.load_graph()
        output = []
        for doc in graph.subjects(RDF.type, CG.Document):
            filename = graph.value(doc, CG.sourceFilename)
            course = graph.value(doc, CG.belongsToCourse)
            page_count = sum(1 for _ in graph.objects(doc, CG.hasPage))
            chunk_count = sum(
                1 for page in graph.objects(doc, CG.hasPage)
                for _ in graph.objects(page, CG.hasChunk)
            )
            output.append({
                "document_uri": str(doc),
                "filename": str(filename or ""),
                "course": str(graph.value(course, SKOS.prefLabel) or ""),
                "page_count": page_count,
                "chunk_count": chunk_count,
            })
        return sorted(output, key=lambda d: (d["course"], d["filename"]))

    def ingest_pdf(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        course_id: str,
        embedder,
        topics: Iterable[str] | None = None,
        words_per_chunk: int = 450,
        overlap: int = 50,
    ) -> dict:
        if not _COURSE_ID.fullmatch(course_id):
            raise ValueError("Ders kodu harf/rakam, '-' veya '_' içermeli (en fazla 64 karakter).")
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Yalnızca .pdf uzantılı dosyalar kabul edilir.")
        if not pdf_bytes:
            raise ValueError("PDF dosyası boş.")
        pages = extract_pages(pdf_bytes)
        chunks = chunk_pages(pages, words_per_chunk=words_per_chunk, overlap=overlap)
        if not chunks:
            raise ValueError("PDF'de indekslenecek metin bulunamadı.")

        digest = hashlib.sha256(pdf_bytes).hexdigest()
        document_key = hashlib.sha256(f"{course_id}:{digest}".encode("utf-8")).hexdigest()
        doc_uri = _resource("document", document_key)
        course_uri = _resource("course", course_id)
        topics = _safe_topics(topics)

        with _LOCK:
            candidate = self.load_graph()
            if (doc_uri, RDF.type, CG.Document) in candidate:
                return {
                    "status": "already_exists", "document_uri": str(doc_uri),
                    "course": course_id,
                    "message": "Bu PDF bu ders için zaten yüklenmiş.",
                }

            # Embedding happens exactly once; vectors remain local and are stored
            # on their respective RDF chunks for Melisa's subsequent retriever.
            vectors = embedder.encode([chunk.text for chunk in chunks])
            if len(vectors) != len(chunks):
                raise ValueError("Embedding sonucu ile chunk sayısı eşleşmiyor.")
            clean_vectors: list[list[float]] = []
            dimension = None
            for vector in vectors:
                values = [float(value) for value in vector]
                if not values or not all(math.isfinite(v) for v in values):
                    raise ValueError("Embedding boş veya geçersiz değer içeriyor.")
                if dimension is None:
                    dimension = len(values)
                if len(values) != dimension:
                    raise ValueError("Embedding boyutları tutarsız.")
                clean_vectors.append(values)

            candidate.add((course_uri, RDF.type, CG.Course))
            candidate.add((course_uri, SKOS.prefLabel, Literal(course_id, datatype=XSD.string)))
            candidate.add((course_uri, CG.hasDocument, doc_uri))
            candidate.add((doc_uri, RDF.type, CG.Document))
            candidate.add((doc_uri, CG.belongsToCourse, course_uri))
            candidate.add((doc_uri, CG.sourceFilename, Literal(filename, datatype=XSD.string)))
            candidate.add((doc_uri, CG.contentSha256, Literal(digest, datatype=XSD.string)))

            for page in pages:
                page_uri = _resource("page", f"{document_key}/{page.number}")
                candidate.add((page_uri, RDF.type, CG.Page))
                candidate.add((page_uri, CG.belongsToDocument, doc_uri))
                candidate.add((page_uri, CG.pageNumber, Literal(page.number, datatype=XSD.positiveInteger)))
                candidate.add((doc_uri, CG.hasPage, page_uri))

            for chunk, vector in zip(chunks, clean_vectors):
                page_uri = _resource("page", f"{document_key}/{chunk.page_number}")
                chunk_uri = _resource("chunk", f"{document_key}/{chunk.page_number}/{chunk.chunk_index}")
                candidate.add((chunk_uri, RDF.type, CG.Chunk))
                candidate.add((chunk_uri, CG.belongsToPage, page_uri))
                candidate.add((page_uri, CG.hasChunk, chunk_uri))
                candidate.add((chunk_uri, CG.chunkPageNumber, Literal(chunk.page_number, datatype=XSD.positiveInteger)))
                candidate.add((chunk_uri, CG.chunkIndex, Literal(chunk.chunk_index, datatype=XSD.nonNegativeInteger)))
                candidate.add((chunk_uri, CG.text, Literal(chunk.text, datatype=XSD.string)))
                candidate.add((chunk_uri, CG.embeddingJson, Literal(json.dumps(vector), datatype=XSD.string)))
                for topic in topics:
                    # Stable IDs; Turkish/Unicode labels are retained verbatim.
                    topic_id = hashlib.sha256(topic.casefold().encode("utf-8")).hexdigest()[:24]
                    topic_uri = _resource("topic", topic_id)
                    candidate.add((topic_uri, RDF.type, SKOS.Concept))
                    candidate.add((topic_uri, SKOS.prefLabel, Literal(topic, datatype=XSD.string)))
                    candidate.add((chunk_uri, CG.hasTopic, topic_uri))

            conforms, report = self.validate_graph(candidate)
            if not conforms:
                raise GraphValidationError("RDF grafı SHACL kontrolünden geçemedi:\n" + report)

            self.graph_path.parent.mkdir(parents=True, exist_ok=True)
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            stored_pdf = self.upload_dir / f"{document_key}.pdf"
            # Never replace an existing PDF; document identity is content-based.
            created_pdf = not stored_pdf.exists()
            temp_name = None
            try:
                if created_pdf:
                    with stored_pdf.open("xb") as out:
                        out.write(pdf_bytes)
                with tempfile.NamedTemporaryFile(
                    mode="wb", prefix=".graph-", suffix=".ttl",
                    dir=self.graph_path.parent, delete=False,
                ) as target:
                    temp_name = target.name
                candidate.serialize(destination=temp_name, format="turtle", encoding="utf-8")
                os.replace(temp_name, self.graph_path)
            except Exception:
                if temp_name is not None:
                    Path(temp_name).unlink(missing_ok=True)
                if created_pdf:
                    stored_pdf.unlink(missing_ok=True)
                raise

            return {
                "status": "created", "course": course_id,
                "document_uri": str(doc_uri), "filename": filename,
                "page_count": len(pages), "chunk_count": len(chunks),
                "topic_count": len(topics), "embedding_dimension": dimension,
                "shacl_conforms": True,
            }
