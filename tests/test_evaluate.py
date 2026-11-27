"""Tests for scripts/evaluate.py (no Ollama, no embedding model needed)."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

from coursegraph.answer_service import AnswerService, OllamaUnavailable
from coursegraph.retriever import HybridRetriever
from test_retriever import CHUNKS, KeywordEmbedder, StubStore

_SPEC = importlib.util.spec_from_file_location(
    "evaluate", Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py")
ev = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ev)

QUESTIONS = [
    {"id": "q1", "course": "COM3001", "question": "What is third normal form?",
     "expected": [{"filename": "databases.pdf", "page": 7}]},
    {"id": "q2", "course": "COM3001", "question": "Explain sql connector in python",
     "expected": [{"filename": "databases.pdf", "page": 2}]},  # wrong page on purpose
    {"id": "q3", "course": "COM3001", "question": "Explain the Fourier transform", "answerable": False},
]


class FakeLLM:
    model = "fake"

    def __init__(self, fail=False):
        self.fail = fail

    def generate(self, prompt, system):
        if self.fail:
            raise OllamaUnavailable("down")
        return "Answer [1]."


class StepClock:
    """Each question takes exactly `step` seconds."""

    def __init__(self, steps):
        self.values = iter(v for step in steps for v in (0.0, step))

    def __call__(self):
        return next(self.values)


def _retriever():
    return HybridRetriever(StubStore(CHUNKS), KeywordEmbedder(), min_similarity=0.3)


def _write(tmp_path, questions):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(questions), encoding="utf-8")
    return path


def test_recall_at_3_counts_questions_whose_page_is_in_the_top_3(tmp_path):
    questions = ev.load_questions(_write(tmp_path, QUESTIONS))
    rows = ev.evaluate(questions, _retriever())

    assert [r["hit_at_3"] for r in rows] == [True, False, None]
    summary = ev.summarize(rows)
    assert summary["recall_at_3"] == 0.5
    assert summary["answerable_questions"] == 2


def test_unanswerable_questions_measure_the_no_source_reply(tmp_path):
    rows = ev.evaluate(ev.load_questions(_write(tmp_path, QUESTIONS)), _retriever())
    assert rows[2]["covered"] is False
    assert ev.summarize(rows)["rejection_accuracy"] == 1.0


def test_answer_times_median_p90_and_share_under_10_seconds(tmp_path):
    questions = ev.load_questions(_write(tmp_path, QUESTIONS))
    service = AnswerService(_retriever(), FakeLLM())
    rows = ev.evaluate(questions, _retriever(), service, clock=StepClock([2.0, 4.0, 12.0]))

    assert [r["time_ms"] for r in rows] == [2000, 4000, 12000]
    summary = ev.summarize(rows)
    assert summary["median_time_ms"] == 4000
    assert summary["p90_time_ms"] == 12000
    assert summary["share_under_10s"] == pytest.approx(0.667)
    assert summary["targets_met"]["share_under_10s"] is False


def test_llm_errors_are_counted(tmp_path):
    questions = ev.load_questions(_write(tmp_path, QUESTIONS))
    rows = ev.evaluate(questions, _retriever(), AnswerService(_retriever(), FakeLLM(fail=True)))
    assert ev.summarize(rows)["llm_errors"] == 2  # q3 never reaches the model


def test_citation_accuracy_from_two_judges(tmp_path):
    questions = ev.load_questions(_write(tmp_path, QUESTIONS))
    rows = ev.evaluate(questions, _retriever(), AnswerService(_retriever(), FakeLLM()))
    sheet = tmp_path / "judgments.csv"

    assert ev.write_judging_sheet(rows, sheet) is True
    with sheet.open(newline="", encoding="utf-8") as handle:
        filled = list(csv.DictReader(handle))
    assert [r["id"] for r in filled] == ["q1", "q2"]  # only answered questions are judged
    filled[0].update(judge_1="1", judge_2="1")
    filled[1].update(judge_1="1", judge_2="0")
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ev.JUDGE_COLUMNS)
        writer.writeheader()
        writer.writerows(filled)

    summary = ev.summarize(rows, ev.read_judgments(sheet))
    assert summary["citation_accuracy"] == 0.75
    assert summary["judge_agreement"] == 0.5
    assert summary["judged_answers"] == 2
    assert ev.write_judging_sheet(rows, sheet) is False  # filled scores are never overwritten


def test_judgments_must_be_zero_or_one(tmp_path):
    sheet = tmp_path / "judgments.csv"
    sheet.write_text("id,judge_1,judge_2\nq1,yes,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="0 or 1"):
        ev.read_judgments(sheet)


def test_question_file_is_validated(tmp_path):
    with pytest.raises(ValueError, match="expected page"):
        ev.load_questions(_write(tmp_path, [{"id": "a", "course": "X", "question": "q?"}]))
    with pytest.raises(ValueError, match="Duplicate"):
        ev.load_questions(_write(tmp_path, [QUESTIONS[0], QUESTIONS[0]]))
    with pytest.raises(ValueError, match="missing 'course'"):
        ev.load_questions(_write(tmp_path, [{"id": "a", "question": "q?", "answerable": False}]))


def test_summary_only_recomputes_from_saved_results(tmp_path):
    rows = ev.evaluate(ev.load_questions(_write(tmp_path, QUESTIONS)), _retriever())
    out = tmp_path / "results.json"
    out.write_text(json.dumps({"questions": rows}), encoding="utf-8")

    assert ev.main(["--summary-only", "--out", str(out), "--judgments", str(tmp_path / "none.csv"),
                    "--no-llm"]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["recall_at_3"] == 0.5
    assert report["settings"]["model"] is None
    assert len(report["questions"]) == 3
