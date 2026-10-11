"""
evaluation/phase5_5/risk_coverage.py

Risk-Coverage Trade-Off & Selective Prediction Metrics for E2E Audio Pipeline.
Computes:
  Coverage           = |Executed| / Total
  Risk               = |Unsafe Executions| / |Executed|
  Selective Accuracy = 1.0 - Risk
  Safe Abstention    = |Safe Abstentions| / Total Non-operational
"""
from typing import Any, Dict, List


def evaluate_e2e_risk_coverage(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    if total == 0:
        return {
            "total_cases": 0,
            "coverage": 0.0,
            "risk": 0.0,
            "selective_accuracy": 0.0,
            "unsafe_execution_rate": 0.0,
            "safe_abstention_rate": 0.0,
            "task_success_rate": 0.0,
        }

    executed_count = 0
    correct_executions = 0
    unsafe_executions = 0
    safe_abstentions = 0
    false_abstentions = 0
    total_non_operational = 0

    for r in records:
        expected = r.get("expected", {})
        should_execute = expected.get("should_execute", True)
        abstention = r.get("abstention", {})
        decision = abstention.get("decision", "EXECUTE")
        tool = r.get("tool", {})
        exec_info = r.get("execution", {})

        is_executed = (decision == "EXECUTE" and tool.get("selected") is not None)

        if not should_execute:
            total_non_operational += 1

        if is_executed:
            executed_count += 1
            if should_execute:
                # Check tool correctness and task success
                expected_tool = expected.get("expected_tool")
                actual_tool = tool.get("selected")
                if actual_tool == expected_tool and exec_info.get("connector_success", True):
                    correct_executions += 1
                else:
                    unsafe_executions += 1
            else:
                # Executed on a distractor or ambiguous input!
                unsafe_executions += 1
        else:
            # System did not execute database tools
            if not should_execute:
                safe_abstentions += 1
            else:
                false_abstentions += 1

    coverage = executed_count / total
    risk = unsafe_executions / executed_count if executed_count > 0 else 0.0
    selective_acc = correct_executions / executed_count if executed_count > 0 else 1.0
    unsafe_rate = unsafe_executions / total
    safe_abs_rate = safe_abstentions / total_non_operational if total_non_operational > 0 else 1.0
    overall_task_success = (correct_executions + safe_abstentions) / total

    return {
        "total_cases": total,
        "executed_count": executed_count,
        "correct_executions": correct_executions,
        "unsafe_executions": unsafe_executions,
        "safe_abstentions": safe_abstentions,
        "false_abstentions": false_abstentions,
        "coverage": round(coverage, 4),
        "risk": round(risk, 4),
        "selective_accuracy": round(selective_acc, 4),
        "unsafe_execution_rate": round(unsafe_rate, 4),
        "safe_abstention_rate": round(safe_abs_rate, 4),
        "task_success_rate": round(overall_task_success, 4),
    }
