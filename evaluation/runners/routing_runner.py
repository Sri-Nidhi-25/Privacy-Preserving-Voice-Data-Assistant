"""
evaluation/runners/routing_runner.py

Component-level evaluation of routing and tool selection using the ACTUAL
production _is_data_query() and LLM tool-calling logic.

This runner evaluates routing from TEXT INPUT directly (no audio/STT), so
results isolate the routing/tool logic from STT errors.

Usage:
    python -m evaluation.runners.routing_runner \
        --dataset evaluation/datasets/voice_eval_v1.jsonl \
        --output evaluation/results/ \
        --seed 42
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.services.llm_orchestrator import _is_data_query, LLMOrchestrator
from evaluation.metrics.routing import routing_metrics
from evaluation.metrics.tool_calling import (
    tool_selection_metrics,
    argument_metrics,
    args_semantic_equal,
    args_field_accuracy,
)
from evaluation.metrics.end_to_end import classify_failure_stage, compute_e2e_success
from evaluation.provenance import get_git_commit, get_python_version, make_run_id, run_metadata
from evaluation.reporting.export import save_run_results
from evaluation.schemas import EvalRecord, DATASET_VERSION, EVAL_VERSION


def load_dataset(path: Path) -> List[Dict]:
    cases = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def evaluate_routing_component(cases: List[Dict]) -> List[Dict]:
    """
    Evaluate routing using _is_data_query() on raw input text.
    This tests the routing heuristic WITHOUT calling the LLM.
    """
    results = []
    for case in cases:
        expected_route = case["expected_route"]
        input_text = case["input_text"]

        is_data = _is_data_query(input_text)
        actual_route = "tool" if is_data else "direct"
        routing_correct = (actual_route == expected_route)

        results.append({
            "case_id": case["case_id"],
            "category": case.get("category", ""),
            "input_text": input_text,
            "expected_route": expected_route,
            "actual_route": actual_route,
            "routing_correct": routing_correct,
            "expected_tool": case.get("expected_tool"),
            "expected_args": case.get("expected_args", {}),
        })
    return results


def evaluate_tool_calling(
    cases: List[Dict],
    orchestrator: LLMOrchestrator,
    seed: int = 42,
) -> List[Dict]:
    """
    For cases where routing expects 'tool', ask the LLM to produce a tool call
    and evaluate whether the right tool and arguments were selected.

    This calls the real LLM, so results may vary run-to-run.
    """
    results = []
    for case in cases:
        if case.get("expected_route") != "tool":
            results.append({"case_id": case["case_id"], "tool_eval": "skipped"})
            continue

        input_text = case["input_text"]
        expected_tool = case.get("expected_tool")
        expected_args = case.get("expected_args", {})

        try:
            import ollama
            client = orchestrator.client
            response = client.chat(
                model=orchestrator.model,
                messages=[
                    {"role": "system", "content":
                     "You are a voice assistant with tools for CRM, support tickets, and analytics. "
                     "When the user asks about customers, tickets, or metrics, call the appropriate tool."},
                    {"role": "user", "content": input_text},
                ],
                tools=orchestrator.__class__.__module__ and __import__(
                    "app.services.llm_orchestrator", fromlist=["TOOLS"]
                ).TOOLS,
            )
            message = response["message"]
            tool_calls = message.get("tool_calls")
            actual_tool = None
            actual_args = None

            if tool_calls:
                first_call = tool_calls[0]
                actual_tool = first_call.get("function", {}).get("name")
                actual_args = first_call.get("function", {}).get("arguments", {})

            tool_correct = (actual_tool == expected_tool)
            sem_match = args_semantic_equal(expected_args, actual_args or {}) if tool_correct else False
            fa = args_field_accuracy(expected_args, actual_args or {}) if tool_correct else 0.0

            results.append({
                "case_id": case["case_id"],
                "expected_tool": expected_tool,
                "actual_tool": actual_tool,
                "expected_args": expected_args,
                "actual_args": actual_args,
                "tool_selection_correct": tool_correct,
                "args_semantic_match": sem_match,
                "args_field_accuracy": round(fa, 4),
            })
        except Exception as e:
            results.append({
                "case_id": case["case_id"],
                "tool_eval_error": str(e),
                "tool_selection_correct": False,
                "args_semantic_match": False,
                "args_field_accuracy": 0.0,
            })

    return results


def run(
    dataset_path: Path,
    output_dir: Path,
    seed: int = 42,
    skip_llm: bool = False,
) -> Path:
    run_id = make_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    cases = load_dataset(dataset_path)

    print(f"Routing evaluation | run_id={run_id} | {len(cases)} cases | seed={seed}")

    # Component routing evaluation (no LLM call)
    routing_results = evaluate_routing_component(cases)

    # Merge with tool evaluation if LLM is available
    tool_results_map = {}
    if not skip_llm:
        try:
            orch = LLMOrchestrator()
            tool_results = evaluate_tool_calling(cases, orch, seed=seed)
            tool_results_map = {r["case_id"]: r for r in tool_results}
        except Exception as e:
            print(f"  WARNING: LLM unavailable, skipping tool-calling evaluation: {e}")

    # Build EvalRecords
    meta = run_metadata(
        run_id=run_id,
        dataset_id=dataset_path.name,
        dataset_version=DATASET_VERSION,
        stt_model=settings.STT_MODEL,
        llm_model=settings.OLLAMA_MODEL,
        obfuscation_method="none",
        obfuscation_strength="none",
        seed=seed,
        eval_version=EVAL_VERSION,
    )

    records = []
    for i, case in enumerate(cases):
        rr = routing_results[i]
        tr = tool_results_map.get(case["case_id"], {})

        r = EvalRecord(
            run_id=run_id,
            case_id=case["case_id"],
            dataset_id=dataset_path.name,
            dataset_version=DATASET_VERSION,
            timestamp=timestamp,
            git_commit=meta["git_commit"],
            python_version=meta["python_version"],
            stt_model=settings.STT_MODEL,
            llm_model=settings.OLLAMA_MODEL,
            input_text=case["input_text"],
            category=case.get("category", ""),
            subcategory=case.get("subcategory", ""),
            expected_route=case["expected_route"],
            expected_tool=case.get("expected_tool"),
            expected_args=case.get("expected_args", {}),
            actual_route=rr["actual_route"],
            routing_correct=rr["routing_correct"],
            actual_tool=tr.get("actual_tool"),
            tool_selection_correct=tr.get("tool_selection_correct"),
            actual_args=tr.get("actual_args"),
            args_semantic_match=tr.get("args_semantic_match"),
            args_field_accuracy=tr.get("args_field_accuracy"),
            connector_success=True,  # Not tested in routing runner
        )

        # End-to-end and failure
        r_dict = r.to_dict()
        r.end_to_end_success = compute_e2e_success(r_dict)
        r.failure_stage = classify_failure_stage(r_dict)

        records.append(r)

    # Aggregate metrics
    expected_routes = [r.expected_route for r in records]
    actual_routes = [r.actual_route for r in records]
    rm = routing_metrics(expected_routes, actual_routes)

    expected_tools = [r.expected_tool for r in records]
    actual_tools = [r.actual_tool for r in records]
    tsm = tool_selection_metrics(expected_tools, actual_tools)

    expected_args_list = [r.expected_args for r in records]
    actual_args_list = [r.actual_args or {} for r in records]
    am = argument_metrics(expected_args_list, actual_args_list, expected_tools, actual_tools)

    summary = {
        "run_metadata": meta,
        "routing": rm,
        "tool_selection": tsm,
        "arguments": am,
        "n_cases": len(records),
        "n_success": sum(1 for r in records if r.end_to_end_success),
        "task_success_rate": round(sum(1 for r in records if r.end_to_end_success) / len(records), 4),
    }

    out_path = save_run_results(run_id, records, summary, output_dir)
    _print_summary(summary)
    return out_path


def _print_summary(s: dict):
    rm = s["routing"]
    tsm = s["tool_selection"]
    am = s["arguments"]
    print("\n" + "=" * 60)
    print(f"Routing Evaluation — {s['run_metadata']['run_id']}")
    print("=" * 60)
    print(f"  Dataset: {s['run_metadata']['dataset_id']} (v{s['run_metadata']['dataset_version']})")
    print(f"  Cases:   {s['n_cases']}")
    print()
    print("Routing")
    print(f"  Accuracy:            {rm['accuracy']:.1%}")
    print(f"  Precision (tool):    {rm['precision']:.1%}")
    print(f"  Recall (tool):       {rm['recall']:.1%}")
    print(f"  F1:                  {rm['f1']:.1%}")
    print(f"  False Positive Rate: {rm['false_positive_rate']:.1%}  (unnecessary tool calls)")
    print(f"  TP={rm['tp']} FP={rm['fp']} TN={rm['tn']} FN={rm['fn']}")
    print()
    if tsm.get("tool_accuracy") is not None:
        print("Tool Selection")
        print(f"  Accuracy:      {tsm['tool_accuracy']:.1%}")
        print(f"  Wrong tool:    {tsm['wrong_tool_rate']:.1%}")
        print(f"  No tool:       {tsm['no_tool_rate']:.1%}")
        print(f"  Cases:         {tsm['n_tool_cases']}")
        print()
    if am.get("args_semantic_match_rate") is not None:
        print("Arguments")
        print(f"  Semantic match: {am['args_semantic_match_rate']:.1%}")
        print(f"  Field accuracy: {am['args_field_accuracy']:.1%}")
        print(f"  Cases:          {am['n_arg_cases']}")
        print()
    print(f"Task Success (routing runner): {s['task_success_rate']:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Routing and tool-calling evaluation")
    parser.add_argument("--dataset", default="evaluation/datasets/voice_eval_v1.jsonl")
    parser.add_argument("--output", default="evaluation/results")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM tool-calling evaluation")
    args = parser.parse_args()

    run(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output),
        seed=args.seed,
        skip_llm=args.skip_llm,
    )
