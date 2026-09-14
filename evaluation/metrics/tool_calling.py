"""
evaluation/metrics/tool_calling.py - Tool selection and argument evaluation.
"""
from typing import Any, Dict, List, Optional, Tuple


def _coerce_value(v: Any) -> Any:
    """Normalize a value for semantic comparison (e.g. '10' == 10)."""
    if isinstance(v, str):
        stripped = v.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        try:
            return float(stripped)
        except ValueError:
            return stripped.lower()
    if isinstance(v, (int, float)):
        return v
    return v


def args_semantic_equal(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    """
    Check whether actual arguments are semantically equivalent to expected.
    - Coerces string ints to int (e.g. "10" == 10)
    - Case-insensitive string comparison
    - Extra unexpected keys in actual count as incorrect
    - Missing expected keys count as incorrect
    """
    for k, ev in expected.items():
        if k not in actual:
            return False
        if _coerce_value(ev) != _coerce_value(actual[k]):
            return False
    # Any extra key in actual that isn't in expected is a bad over-specification
    for k in actual:
        if k not in expected:
            return False
    return True


def args_field_accuracy(expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
    """
    Field-level accuracy: fraction of expected fields correctly present and valued.
    Extra fields in actual are counted as errors.
    """
    if not expected and not actual:
        return 1.0

    all_keys = set(expected.keys()) | set(actual.keys())
    if not all_keys:
        return 1.0

    correct = 0
    for k in all_keys:
        if k in expected and k in actual:
            if _coerce_value(expected[k]) == _coerce_value(actual[k]):
                correct += 1
        # missing in actual OR extra in actual = wrong

    return correct / len(all_keys)


def tool_selection_metrics(
    expected_tools: List[Optional[str]],
    actual_tools: List[Optional[str]],
) -> dict:
    """
    Compute tool selection accuracy for cases where a tool was expected.
    Only considers cases where expected_tool is not None.
    """
    tool_cases = [(e, a) for e, a in zip(expected_tools, actual_tools) if e is not None]
    if not tool_cases:
        return {"tool_accuracy": None, "n_tool_cases": 0}

    correct = sum(1 for e, a in tool_cases if e == a)
    wrong_tool = sum(1 for e, a in tool_cases if a is not None and e != a)
    no_tool = sum(1 for e, a in tool_cases if a is None)

    return {
        "tool_accuracy": round(correct / len(tool_cases), 4),
        "wrong_tool_rate": round(wrong_tool / len(tool_cases), 4),
        "no_tool_rate": round(no_tool / len(tool_cases), 4),
        "n_tool_cases": len(tool_cases),
        "correct": correct,
    }


def argument_metrics(
    expected_args_list: List[Dict],
    actual_args_list: List[Dict],
    expected_tools: List[Optional[str]],
    actual_tools: List[Optional[str]],
) -> dict:
    """
    Compute argument accuracy only for cases where tool selection was correct
    (misrouted cases are captured at the routing/tool stage).
    """
    correct_tool_cases = [
        (ea, aa)
        for et, at, ea, aa in zip(expected_tools, actual_tools, expected_args_list, actual_args_list)
        if et is not None and et == at and aa is not None
    ]

    if not correct_tool_cases:
        return {"args_exact_match_rate": None, "args_semantic_match_rate": None,
                "args_field_accuracy": None, "n_arg_cases": 0}

    exact = sum(1 for ea, aa in correct_tool_cases if ea == aa)
    semantic = sum(1 for ea, aa in correct_tool_cases if args_semantic_equal(ea, aa))
    field_acc = [args_field_accuracy(ea, aa) for ea, aa in correct_tool_cases]

    n = len(correct_tool_cases)
    return {
        "args_exact_match_rate": round(exact / n, 4),
        "args_semantic_match_rate": round(semantic / n, 4),
        "args_field_accuracy": round(sum(field_acc) / n, 4),
        "n_arg_cases": n,
    }
