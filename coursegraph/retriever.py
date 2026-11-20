"""E2 hybrid retriever: SPARQL course/topic filter + embedding similarity.

Flow:
1. ``GraphStore.get_course_chunks`` selects the candidate chunks of the chosen
   course (and optional topic) with SPARQL.
2. The question is encoded with the same local model used during ingestion.
3. Candidates are ranked by cosine similarity; the best ``top_k`` that reach
   ``min_similarity`` are returned.
4. If no candidate reaches the threshold, ``covered`` is False and the answer
   service must reply that no source was found instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DEFAULT_TOP_K = 3
# Starting value for all-MiniLM-L6-v2 cosine scores; tune it with the
# evaluation set (scripts/evaluate.py) once the 50 questions exist.
DEFAULT_MIN_SIMILARITY = 0.35


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_uri: str
    document_uri: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    topics: list[str]
    score: float

    def citation_label(self) -> str:
        return f"{self.filename}, p. {self.page_number}"


@dataclass(frozen=True)
class RetrievalResult:
    question: str
    course_id: str
    topic: str | None
    hits: list[RetrievedChunk] = field(default_factory=list)
    best_score: float | None = None
    candidate_count: int = 0

    @property
    def covered(self) -> bool:
        """True when at least one chunk is similar enough to answer from."""
        return bool(self.hits)


class HybridRetriever:
    def __init__(
        self,
        store,
        embedder,
        *,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1 and 1.")
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.min_similarity = min_similarity

    def retrieve(self, question: str, course_id: str, *, topic: str | None = None) -> RetrievalResult:
        question = " ".join((question or "").split())
        if not question:
            raise ValueError("Question must not be empty.")
        course_id = (course_id or "").strip().upper()
        if not course_id:
            raise ValueError("A course must be selected.")

        # Step 1 (SPARQL): only chunks of the selected course/topic.
        candidates = self.store.get_course_chunks(course_id, topic=topic)
        if not candidates:
            return RetrievalResult(question, course_id, topic)

        # Step 2: question vector with the same local model as ingestion.
        query_vector = np.asarray(self.embedder.encode([question])[0], dtype=float)
        matrix = np.asarray([c["embedding"] for c in candidates], dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != query_vector.shape[0]:
            raise ValueError(
                "Question and chunk embedding dimensions differ; "
                "ingestion and retrieval must use the same model."
            )

        # Step 3: cosine similarity and ranking.
        scores = _cosine(matrix, query_vector)
        order = np.argsort(-scores, kind="stable")
        best_score = float(scores[order[0]])

        hits = []
        for index in order[: self.top_k]:
            score = float(scores[index])
            if score < self.min_similarity:
                break  # Sorted, so every remaining score is lower too.
            item = candidates[index]
            hits.append(RetrievedChunk(
                chunk_uri=item["chunk_uri"],
                document_uri=item["document_uri"],
                filename=item["filename"],
                page_number=int(item["page_number"]),
                chunk_index=int(item["chunk_index"]),
                text=item["text"],
                topics=list(item.get("topics", [])),
                score=round(score, 4),
            ))

        return RetrievalResult(
            question=question,
            course_id=course_id,
            topic=topic,
            hits=hits,
            best_score=round(best_score, 4),
            candidate_count=len(candidates),
        )


def _cosine(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(vector)
    return np.divide(matrix @ vector, norms, out=np.zeros(len(matrix)), where=norms != 0)
