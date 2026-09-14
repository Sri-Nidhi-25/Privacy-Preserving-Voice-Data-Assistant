"""
evaluation/reporting/tables.py - ASCII table generation for reports.
"""
from typing import List, Dict


def failure_matrix_table(rows: List[Dict]) -> str:
    header = f"{'case_id':<20} {'cat':<15} {'route':<7} {'tool':<6} {'args':<6} {'conn':<6} {'e2e':<5} {'fail_stage'}"
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r.get('case_id',''):<20} {r.get('category',''):<15} "
            f"{r.get('route_ok','?'):<7} {r.get('tool_ok','?'):<6} "
            f"{r.get('args_ok','?'):<6} {r.get('connector_ok','?'):<6} "
            f"{r.get('e2e','?'):<5} {r.get('failure_stage','—')}"
        )
    return "\n".join(lines)


def failure_examples_table(records: List[Dict], max_examples: int = 5) -> str:
    failures = [r for r in records if not r.get("end_to_end_success")]
    lines = [f"\nRepresentative Failures (first {min(max_examples, len(failures))} of {len(failures)}):"]
    lines.append("-" * 60)
    for r in failures[:max_examples]:
        lines.append(f"Case     : {r.get('case_id')}")
        lines.append(f"Category : {r.get('category')}")
        lines.append(f"Input    : {r.get('input_text')}")
        lines.append(f"Expected : route={r.get('expected_route')} tool={r.get('expected_tool')}")
        lines.append(f"Actual   : route={r.get('actual_route')} tool={r.get('actual_tool')}")
        lines.append(f"Failure  : {r.get('failure_stage')} — {r.get('failure_reason','')}")
        lines.append("-" * 60)
    return "\n".join(lines)
