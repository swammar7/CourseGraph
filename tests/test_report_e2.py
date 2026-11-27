"""/report shows measured evaluation results, never placeholder numbers."""
import json

import pytest

pytest.importorskip("flask")
from app import create_app

RESULTS = {
    "generated_at": "2026-11-30T12:00:00+00:00",
    "settings": {"model": "qwen2.5:3b", "threshold": 0.35, "top_k": 3, "embedding_model": "all-MiniLM-L6-v2"},
    "summary": {
        "total_questions": 4, "answerable_questions": 3, "unanswerable_questions": 1,
        "recall_at_3": 0.667, "rejection_accuracy": 1.0, "median_time_ms": 3100, "p90_time_ms": 8200,
        "share_under_10s": 1.0, "llm_errors": 0, "citation_accuracy": None, "judge_agreement": None,
        "judged_answers": 0,
        "targets_met": {"recall_at_3": False, "citation_accuracy": False, "share_under_10s": True},
    },
    "questions": [
        {"id": "econ-01", "course": "COM7093", "question": "B/C formula?", "answerable": True,
         "expected": ["econ_bcr.pdf p.2"], "retrieved": ["econ_bcr.pdf p.2 (0.71)"], "hit_at_3": True,
         "covered": True},
        {"id": "econ-02", "course": "COM7093", "question": "Disbenefits?", "answerable": True,
         "expected": ["econ_bcr.pdf p.14"], "retrieved": ["econ_bcr.pdf p.16 (0.52)"], "hit_at_3": False,
         "covered": True},
        {"id": "arch-01", "course": "SEN5016", "question": "What is an NFP?", "answerable": True,
         "expected": ["sen5016_07.pdf p.2"], "retrieved": ["sen5016_07.pdf p.2 (0.80)"], "hit_at_3": True,
         "covered": True},
        {"id": "none-01", "course": "COM7093", "question": "What is IRR?", "answerable": False,
         "expected": [], "retrieved": [], "hit_at_3": None, "covered": False},
    ],
}


def _client(tmp_path, fake_embedder, results=None, raw=None):
    path = tmp_path / "results.json"
    if results is not None:
        path.write_text(json.dumps(results), encoding="utf-8")
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    app = create_app({"TESTING": True, "GRAPH_PATH": str(tmp_path / "graph.ttl"),
                      "UPLOAD_FOLDER": str(tmp_path / "uploads"), "EVAL_RESULTS": str(path)},
                     embedder=fake_embedder)
    return app.test_client()


def test_report_shows_measured_results(tmp_path, fake_embedder):
    html = _client(tmp_path, fake_embedder, RESULTS).get("/report").get_data(as_text=True)

    assert "67%" in html                       # Recall@3
    assert "Median 3100 ms" in html
    assert "not judged yet" in html            # citation accuracy pending
    assert "qwen2.5:3b" in html and "all-MiniLM-L6-v2" in html
    assert "COM7093" in html and "SEN5016" in html
    assert "1 / 2" in html and "2 / 2" not in html  # COM7093 found 1 of 2
    assert "econ-02" in html and "econ_bcr.pdf p.16 (0.52)" in html  # missed question is listed
    assert "85%" not in html and "placeholder" not in html


def test_report_without_results_shows_no_placeholder_numbers(tmp_path, fake_embedder):
    page = _client(tmp_path, fake_embedder).get("/report")
    html = page.get_data(as_text=True)

    assert page.status_code == 200
    assert "No evaluation has been run yet" in html
    assert "scripts/evaluate.py" in html
    assert "85%" not in html and "88%" not in html and "2150" not in html


def test_report_with_broken_results_file_explains_the_problem(tmp_path, fake_embedder):
    page = _client(tmp_path, fake_embedder, raw="{not json")
    response = page.get("/report")
    assert response.status_code == 200
    assert "could not be read" in response.get_data(as_text=True)


def test_report_shows_judged_citation_accuracy(tmp_path, fake_embedder):
    judged = json.loads(json.dumps(RESULTS))
    judged["summary"].update(citation_accuracy=0.9, judged_answers=3)
    judged["summary"]["targets_met"]["citation_accuracy"] = True
    html = _client(tmp_path, fake_embedder, judged).get("/report").get_data(as_text=True)

    assert "90%" in html and "two judges, 3 answers" in html
    assert "not judged yet" not in html
