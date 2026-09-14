"""
evaluation/reporting/export.py - Save evaluation results to JSON/CSV/JSONL.

Every run gets its own timestamped directory under evaluation/results/.
Previous runs are never overwritten.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from evaluation.schemas import EvalRecord


def _run_dir(run_id: str, output_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = output_dir / f"{ts}_{run_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_run_results(
    run_id: str,
    records: List[EvalRecord],
    summary: dict,
    output_dir: Path,
) -> Path:
    """
    Save a complete evaluation run.
    Returns the path to the run directory.
    """
    run_dir = _run_dir(run_id, output_dir)
    dicts = [r.to_dict() for r in records]

    # metadata.json
    (run_dir / "metadata.json").write_text(
        json.dumps(summary.get("run_metadata", {}), indent=2, default=str), encoding="utf-8"
    )

    # cases.jsonl
    with open(run_dir / "cases.jsonl", "w", encoding="utf-8") as f:
        for d in dicts:
            f.write(json.dumps(d, default=str) + "\n")

    # summary.json
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    # results.csv
    if dicts:
        keys = list(dicts[0].keys())
        with open(run_dir / "results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            for d in dicts:
                # Flatten nested dicts for CSV
                flat = {}
                for k, v in d.items():
                    if isinstance(v, dict):
                        flat[k] = json.dumps(v, default=str)
                    else:
                        flat[k] = v
                writer.writerow(flat)

    print(f"\n  Results saved to: {run_dir}")
    return run_dir
