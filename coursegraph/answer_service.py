"""E2 answer service: grounded answers from the top-3 chunks via local Ollama.

The service never answers from outside the course material:
- if the retriever finds no chunk above the threshold, the LLM is not called
  and the "no source" reply is returned;
- the prompt only contains the retrieved chunks and asks the model to cite
  them as [1], [2], [3];
- if the model says the chunks do not contain the answer, the reply is the
  same "no source" message.
Ollama is only reached on localhost, so no document or question leaves the
student's computer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import time
from urllib import error, request
from urllib.parse import urlparse

DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_HOST = "http://127.0.0.1:11434"
NO_SOURCE_MESSAGE = "No source was found in the uploaded documents for this question."
NO_ANSWER_TOKEN = "NO_ANSWER"
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

SYSTEM_PROMPT = (
    "You are a study assistant for university course material. "
    "Answer ONLY with information from the numbered sources you are given. "
    "After every sentence, cite the source numbers you used, like [1] or [2][3]. "
    f"If the sources do not contain the answer, reply exactly {NO_ANSWER_TOKEN}. "
    "Do not use outside knowledge. Answer in the language of the question."
)


class OllamaUnavailable(RuntimeError):
    """The local Ollama server could not be reached or returned an error."""


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST, timeout: float = 60.0) -> None:
        if urlparse(host).hostname not in _LOCAL_HOSTS:
            raise ValueError("Ollama must run on localhost; course data must not leave the computer.")
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, system: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": 0},
        }).encode("utf-8")
        req = request.Request(
            f"{self.host}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise OllamaUnavailable(
                f"Local model '{self.model}' is not reachable at {self.host}. "
                "Start Ollama and run 'ollama pull " + self.model + "'."
            ) from exc
        if "error" in body:
            raise OllamaUnavailable(str(body["error"]))
        return str(body.get("response", "")).strip()


@dataclass
class Answer:
    question: str
    course_id: str
    text: str
    covered: bool
    model: str
    citations: list[dict] = field(default_factory=list)
    time_ms: int = 0
    error: str | None = None

    def to_view(self) -> dict:
        """Shape expected by templates/index.html."""
        return {
            "text": self.text,
            "covered": self.covered,
            "error": self.error,
            "time_ms": self.time_ms,
            "citations": [
                {"number": c["number"], "document": c["filename"], "page": c["page_number"],
                 "chunk": c["snippet"], "cited": c["cited"], "score": c["score"]}
                for c in self.citations
            ],
        }


class AnswerService:
    def __init__(self, retriever, llm: OllamaClient | None = None) -> None:
        self.retriever = retriever
        self.llm = llm or OllamaClient()

    def answer(self, question: str, course_id: str, *, topic: str | None = None) -> Answer:
        start = time.perf_counter()
        result = self.retriever.retrieve(question, course_id, topic=topic)
        model = getattr(self.llm, "model", "unknown")

        if not result.covered:
            return Answer(result.question, result.course_id, NO_SOURCE_MESSAGE, False, model,
                          time_ms=_elapsed(start))

        citations = [
            {"number": n, "chunk_uri": hit.chunk_uri, "document_uri": hit.document_uri,
             "filename": hit.filename, "page_number": hit.page_number, "score": hit.score,
             "snippet": hit.text[:200] + ("..." if len(hit.text) > 200 else ""), "cited": False}
            for n, hit in enumerate(result.hits, start=1)
        ]
        try:
            raw = self.llm.generate(build_prompt(result.question, result.hits), SYSTEM_PROMPT)
        except OllamaUnavailable as exc:
            return Answer(result.question, result.course_id,
                          "The answer could not be generated, but these sources match your question.",
                          True, model, citations, _elapsed(start), error=str(exc))

        if not raw or raw.strip().upper().startswith(NO_ANSWER_TOKEN):
            return Answer(result.question, result.course_id, NO_SOURCE_MESSAGE, False, model,
                          time_ms=_elapsed(start))

        used = {int(n) for n in re.findall(r"\[(\d+)\]", raw)}
        for citation in citations:
            citation["cited"] = citation["number"] in used
        return Answer(result.question, result.course_id, raw, True, model, citations, _elapsed(start))


def build_prompt(question: str, hits) -> str:
    sources = "\n\n".join(
        f"[{n}] ({hit.filename}, page {hit.page_number})\n{hit.text}"
        for n, hit in enumerate(hits, start=1)
    )
    return f"Sources:\n{sources}\n\nQuestion: {question}\nAnswer:"


def _elapsed(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
