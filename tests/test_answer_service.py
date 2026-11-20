"""E2 answer service tests. Ollama is replaced by fakes, so no model is needed."""
import io
import json

import pytest

from coursegraph import answer_service
from coursegraph.answer_service import (
    NO_SOURCE_MESSAGE, AnswerService, OllamaClient, OllamaUnavailable, build_prompt,
)
from coursegraph.retriever import HybridRetriever
from test_retriever import CHUNKS, KeywordEmbedder, StubStore


class FakeLLM:
    model = "fake-model"

    def __init__(self, reply="Third normal form removes transitive dependencies [1].", fail=False):
        self.reply = reply
        self.fail = fail
        self.prompts = []

    def generate(self, prompt, system):
        self.prompts.append((prompt, system))
        if self.fail:
            raise OllamaUnavailable("Ollama is not running")
        return self.reply


def _service(llm):
    retriever = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), min_similarity=0.3)
    return AnswerService(retriever, llm)


def test_an_answer_that_cites_the_slides_it_comes_from():
    llm = FakeLLM()
    answer = _service(llm).answer("What is third normal form?", "COM3001")

    assert answer.covered
    assert answer.error is None
    assert "[1]" in answer.text
    first = answer.citations[0]
    assert (first["filename"], first["page_number"], first["cited"]) == ("databases.pdf", 7, True)
    assert all(not c["cited"] for c in answer.citations[1:])  # [2] was not used in the reply
    assert "(databases.pdf, page 7)" in llm.prompts[0][0]


def test_the_assistant_says_when_my_documents_do_not_cover_a_question():
    llm = FakeLLM()
    answer = _service(llm).answer("Explain the Fourier transform", "COM3001")

    assert not answer.covered
    assert answer.text == NO_SOURCE_MESSAGE
    assert answer.citations == []
    assert llm.prompts == []  # the model is never asked without sources


def test_model_saying_no_answer_becomes_no_source_reply():
    answer = _service(FakeLLM(reply="NO_ANSWER")).answer("What is third normal form?", "COM3001")
    assert not answer.covered
    assert answer.text == NO_SOURCE_MESSAGE
    assert answer.citations == []


def test_ollama_down_still_shows_matching_sources():
    answer = _service(FakeLLM(fail=True)).answer("What is third normal form?", "COM3001")
    assert answer.covered
    assert answer.error and "not running" in answer.error
    assert answer.citations and answer.citations[0]["page_number"] == 7


def test_view_shape_matches_the_template():
    view = _service(FakeLLM()).answer("What is third normal form?", "COM3001").to_view()
    assert set(view) == {"text", "covered", "error", "time_ms", "citations"}
    assert {"document", "page", "chunk", "number", "cited", "score"} <= set(view["citations"][0])
    assert isinstance(view["time_ms"], int)


def test_prompt_numbers_sources_and_keeps_pages():
    hits = HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), min_similarity=0.3) \
        .retrieve("normal form", "COM3001").hits
    prompt = build_prompt("normal form?", hits)
    assert prompt.startswith("Sources:\n[1] (databases.pdf, page ")
    assert "[2]" in prompt and prompt.rstrip().endswith("Answer:")


def test_ollama_client_only_accepts_localhost():
    with pytest.raises(ValueError, match="localhost"):
        OllamaClient(host="http://example.com:11434")
    OllamaClient(host="http://localhost:11434")


def test_ollama_client_sends_local_request_and_reads_reply(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        sent["url"] = req.full_url
        sent["body"] = json.loads(req.data.decode("utf-8"))
        return io.BytesIO(json.dumps({"response": " An answer [1]. "}).encode("utf-8"))

    monkeypatch.setattr(answer_service.request, "urlopen", fake_urlopen)
    reply = OllamaClient(model="qwen2.5:3b").generate("prompt", "system")

    assert reply == "An answer [1]."
    assert sent["url"] == "http://127.0.0.1:11434/api/generate"
    assert sent["body"]["model"] == "qwen2.5:3b"
    assert sent["body"]["stream"] is False
    assert sent["body"]["options"]["temperature"] == 0


def test_ollama_client_reports_unreachable_server(monkeypatch):
    def refuse(req, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(answer_service.request, "urlopen", refuse)
    with pytest.raises(OllamaUnavailable, match="ollama pull"):
        OllamaClient().generate("prompt", "system")
