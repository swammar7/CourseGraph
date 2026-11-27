"""E2 evaluation: Recall@3, rejection, answer time and citation accuracy.

Usage (from the repository root, Ollama running):

    python scripts/evaluate.py \
        --pdf COM7093=eval/pdfs/econ_bcr.pdf \
        --pdf SEN0414=eval/pdfs/sen0414_ch09.pdf \
        --pdf SEN5016=eval/pdfs/sen5016_07.pdf

    # retrieval only (no Ollama): adds --no-llm
    # after two members filled eval/citation_judgments.csv:
    python scripts/evaluate.py --judgments eval/citation_judgments.csv --summary-only

Inputs
    eval/questions.json  list of {"id", "course", "question",
                         "expected": [{"filename", "page"}], "answerable": true}
Outputs
    eval/results.json            summary + one row per question (read by /report)
    eval/citation_judgments.csv  sheet for two judges (created if missing)
    eval/results.xlsx            same rows for Excel (if openpyxl is installed)

The PDFs are ingested into a separate graph (data/eval/) so the student's own
graph is never changed. Page numbers in questions.json refer to these PDFs.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coursegraph.answer_service import AnswerService, OllamaClient, DEFAULT_MODEL  # noqa: E402
from coursegraph.retriever import DEFAULT_MIN_SIMILARITY, DEFAULT_TOP_K, HybridRetriever  # noqa: E402

TIME_LIMIT_MS = 10_000
TARGETS = {"recall_at_3": 0.8, "citation_accuracy": 0.8, "share_under_10s": 0.9}
JUDGE_COLUMNS = ["id", "course", "question", "answer", "citations", "judge_1", "judge_2", "note"]


def load_questions(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data["questions"] if isinstance(data, dict) else data
    seen = set()
    for q in questions:
        for key in ("id", "course", "question"):
            if not str(q.get(key, "")).strip():
                raise ValueError(f"Question {q!r} is missing '{key}'.")
        if q["id"] in seen:
            raise ValueError(f"Duplicate question id: {q['id']}")
        seen.add(q["id"])
        q.setdefault("answerable", True)
        q.setdefault("expected", [])
        if q["answerable"] and not q["expected"]:
            raise ValueError(f"Answerable question {q['id']} needs at least one expected page.")
    return questions


def evaluate(questions: list[dict], retriever, answer_service=None, clock=time.perf_counter) -> list[dict]:
    rows = []
    for q in questions:
        start = clock()
        if answer_service is None:
            result = retriever.retrieve(q["question"], q["course"])
            hits = [(h.filename, h.page_number, h.score) for h in result.hits]
            covered, text, error = result.covered, "", None
        else:
            answer = answer_service.answer(q["question"], q["course"])
            hits = [(c["filename"], c["page_number"], c["score"]) for c in answer.citations]
            covered, text, error = answer.covered, answer.text, answer.error
        elapsed_ms = int((clock() - start) * 1000)

        expected = {(e["filename"], int(e["page"])) for e in q["expected"]}
        found = {(name, page) for name, page, _score in hits}
        rows.append({
            "id": q["id"],
            "course": q["course"],
            "question": q["question"],
            "answerable": bool(q["answerable"]),
            "expected": sorted(f"{n} p.{p}" for n, p in expected),
            "retrieved": [f"{n} p.{p} ({s:.2f})" for n, p, s in hits],
            "hit_at_3": bool(expected & found) if q["answerable"] else None,
            "covered": covered,
            "answer": text,
            "error": error,
            "time_ms": elapsed_ms,
        })
    return rows


def summarize(rows: list[dict], judgments: dict[str, list[int]] | None = None) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    times = sorted(r["time_ms"] for r in rows)

    summary = {
        "total_questions": len(rows),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "recall_at_3": _ratio(sum(r["hit_at_3"] for r in answerable), len(answerable)),
        "rejection_accuracy": _ratio(sum(not r["covered"] for r in unanswerable), len(unanswerable)),
        "median_time_ms": int(statistics.median(times)) if times else None,
        "p90_time_ms": times[min(len(times) - 1, int(0.9 * len(times)))] if times else None,
        "share_under_10s": _ratio(sum(t < TIME_LIMIT_MS for t in times), len(times)),
        "llm_errors": sum(1 for r in rows if r["error"]),
        "citation_accuracy": None,
        "judge_agreement": None,
        "judged_answers": 0,
    }
    if judgments:
        scored = [scores for scores in judgments.values() if len(scores) == 2]
        if scored:
            summary["judged_answers"] = len(scored)
            summary["citation_accuracy"] = round(sum(sum(s) / 2 for s in scored) / len(scored), 3)
            summary["judge_agreement"] = _ratio(sum(s[0] == s[1] for s in scored), len(scored))
    summary["targets_met"] = {
        name: (summary[name] is not None and summary[name] >= target) for name, target in TARGETS.items()
    }
    return summary


def write_judging_sheet(rows: list[dict], path: Path) -> bool:
    """Creates the two-judge sheet once; never overwrites filled-in scores."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=JUDGE_COLUMNS)
        writer.writeheader()
        for r in rows:
            if r["covered"] and r["answer"]:
                writer.writerow({
                    "id": r["id"], "course": r["course"], "question": r["question"],
                    "answer": r["answer"], "citations": " | ".join(r["retrieved"]),
                    "judge_1": "", "judge_2": "", "note": "",
                })
    return True


def read_judgments(path: Path) -> dict[str, list[int]]:
    """judge_1 / judge_2: 1 = citations support the answer, 0 = they do not."""
    judgments = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            scores = []
            for column in ("judge_1", "judge_2"):
                value = (row.get(column) or "").strip()
                if value:
                    if value not in {"0", "1"}:
                        raise ValueError(f"{column} for {row['id']} must be 0 or 1, got {value!r}.")
                    scores.append(int(value))
            judgments[row["id"]] = scores
    return judgments


def write_xlsx(rows: list[dict], summary: dict, path: Path) -> bool:
    try:
        from openpyxl import Workbook
    except ImportError:
        return False
    book = Workbook()
    sheet = book.active
    sheet.title = "questions"
    columns = ["id", "course", "question", "answerable", "expected", "retrieved", "hit_at_3",
               "covered", "time_ms", "answer", "error"]
    sheet.append(columns)
    for r in rows:
        sheet.append([", ".join(v) if isinstance(v, list) else v for v in (r[c] for c in columns)])
    summary_sheet = book.create_sheet("summary")
    for key, value in summary.items():
        summary_sheet.append([key, json.dumps(value) if isinstance(value, dict) else value])
    book.save(path)
    return True


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def _build(args):
    from coursegraph.embeddings import LocalEmbedder
    from coursegraph.graph_store import GraphStore

    store = GraphStore(args.work_dir / "graph.ttl", args.work_dir / "uploads")
    embedder = LocalEmbedder(args.model_dir)
    for spec in args.pdf:
        course, _, pdf_path = spec.partition("=")
        pdf_path = Path(pdf_path)
        if not course or not pdf_path.is_file():
            raise SystemExit(f"--pdf must look like COURSE=path/to/file.pdf (got {spec!r}).")
        status = store.ingest_pdf(pdf_bytes=pdf_path.read_bytes(), filename=pdf_path.name,
                                  course_id=course.strip().upper(), embedder=embedder)["status"]
        print(f"  {status:9} {course.upper():8} {pdf_path.name}")
    retriever = HybridRetriever(store, embedder, top_k=args.top_k, min_similarity=args.threshold)
    service = None if args.no_llm else AnswerService(retriever, OllamaClient(model=args.model))
    return retriever, service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CourseGraph E2 evaluation")
    parser.add_argument("--questions", type=Path, default=ROOT / "eval" / "questions.json")
    parser.add_argument("--pdf", action="append", default=[], metavar="COURSE=FILE.pdf")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "data" / "eval")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models" / "all-MiniLM-L6-v2")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MIN_SIMILARITY)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--no-llm", action="store_true", help="retrieval metrics only, no Ollama")
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "results.json")
    parser.add_argument("--judgments", type=Path, default=ROOT / "eval" / "citation_judgments.csv")
    parser.add_argument("--summary-only", action="store_true",
                        help="recompute the summary from an existing results.json and the judgments")
    args = parser.parse_args(argv)

    if args.summary_only:
        report = json.loads(args.out.read_text(encoding="utf-8"))
        rows = report["questions"]
    else:
        questions = load_questions(args.questions)
        print(f"Ingesting {len(args.pdf)} PDF(s) into {args.work_dir} ...")
        retriever, service = _build(args)
        print(f"Asking {len(questions)} questions ({'retrieval only' if service is None else args.model}) ...")
        rows = evaluate(questions, retriever, service)
        if service is not None and write_judging_sheet(rows, args.judgments):
            print(f"Created {args.judgments}: two members fill judge_1 / judge_2 with 1 or 0.")

    judgments = read_judgments(args.judgments) if args.judgments.exists() else None
    summary = summarize(rows, judgments)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {"model": None if args.no_llm else args.model, "threshold": args.threshold,
                     "top_k": args.top_k, "embedding_model": Path(args.model_dir).name},
        "summary": summary,
        "questions": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_xlsx(rows, summary, args.out.with_suffix(".xlsx")):
        print(f"Wrote {args.out.with_suffix('.xlsx')}")

    print(f"\nWrote {args.out}")
    for key in ("recall_at_3", "rejection_accuracy", "median_time_ms", "share_under_10s",
                "citation_accuracy", "judge_agreement", "llm_errors"):
        print(f"  {key:20} {summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
