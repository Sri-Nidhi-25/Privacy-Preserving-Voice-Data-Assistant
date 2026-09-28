"""Tests for Phase 4 metamorphic relations and behavioral invariants."""
import pytest
from app.services.intent_router import classify_intent, Intent
from app.services.correction_guard import apply_correction_gate, CorrectionDecision

PARAPHRASE_GROUPS = [
    {
        "label": "crm_active",
        "expected_intent": Intent.CRM_QUERY,
        "inputs": [
            "Show me active customers",
            "List all active accounts",
            "Pull active client records",
            "Fetch active customer data",
            "Get active CRM entries",
        ],
    },
    {
        "label": "crm_inactive",
        "expected_intent": Intent.CRM_QUERY,
        "inputs": [
            "Show inactive customers",
            "List all inactive accounts",
            "Which customers are inactive",
            "Pull inactive client data",
        ],
    },
    {
        "label": "support_open",
        "expected_intent": Intent.SUPPORT_QUERY,
        "inputs": [
            "Show open tickets",
            "List unresolved support tickets",
            "What tickets are still open",
            "Get open support cases",
        ],
    },
    {
        "label": "support_high",
        "expected_intent": Intent.SUPPORT_QUERY,
        "inputs": [
            "Show high priority tickets",
            "List critical support tickets",
            "Get tickets with high priority",
            "Pull urgent support cases",
        ],
    },
    {
        "label": "analytics_recent",
        "expected_intent": Intent.ANALYTICS_QUERY,
        "inputs": [
            "Show analytics for last 30 days",
            "Get engagement data for the past month",
            "Pull 30-day analytics report",
            "What are the metrics for the last 30 days",
        ],
    },
    {
        "label": "direct_greeting",
        "expected_intent": Intent.DIRECT,
        "inputs": [
            "Hello",
            "Hi there",
            "Hey",
            "Good morning",
        ],
    },
    {
        "label": "direct_explanation",
        "expected_intent": Intent.DIRECT,
        "inputs": [
            "What is CRM",
            "Explain what analytics means",
            "Tell me about support tickets",
            "What does active status mean",
        ],
    },
    {
        "label": "direct_compliment",
        "expected_intent": Intent.DIRECT,
        "inputs": [
            "Our active sales team is doing great",
            "The analytics team is crushing it",
            "Support team resolved all tickets today",
        ],
    },
]

CORRECTION_TRAP_CASES = [
    ("fetch inactve customers", "fetch inactive customers", CorrectionDecision.ACCEPT_CORRECTION),
    ("show activ accounts", "show active accounts", CorrectionDecision.ACCEPT_CORRECTION),
    ("get active customers", "get inactive customers", CorrectionDecision.KEEP_RAW),
    ("open tickets please", "closed tickets please", CorrectionDecision.KEEP_RAW),
    ("list open tickets", "list all tickets", CorrectionDecision.ACCEPT_CORRECTION),
    ("get support tickets", "get crm data", CorrectionDecision.KEEP_RAW),
]


class TestMetamorphicRouting:
    @pytest.mark.parametrize("group", PARAPHRASE_GROUPS, ids=[g["label"] for g in PARAPHRASE_GROUPS])
    def test_group_consistency(self, group):
        expected = group["expected_intent"]
        failures = []
        for text in group["inputs"]:
            res = classify_intent(text)
            if res.intent != expected:
                failures.append(f"'{text}' -> {res.intent.value} (expected {expected.value})")
        assert not failures, f"Metamorphic failures in {group['label']}:\n" + "\n".join(failures)

    def test_cross_domain_isolation(self):
        crm_inputs = [
            "Show me active customers",
            "List all inactive accounts",
        ]
        for inp in crm_inputs:
            res = classify_intent(inp)
            assert res.intent == Intent.CRM_QUERY
            assert res.target_tool == "get_crm_data"

        support_inputs = [
            "Show open tickets",
            "List high priority tickets",
        ]
        for inp in support_inputs:
            res = classify_intent(inp)
            assert res.intent == Intent.SUPPORT_QUERY
            assert res.target_tool == "get_support_tickets"

    def test_direct_stability(self):
        direct_inputs = [
            "Hello",
            "What is CRM",
            "Tell me a joke",
            "What time is it",
        ]
        for inp in direct_inputs:
            res = classify_intent(inp)
            assert res.route == "direct"
            assert res.target_tool is None


class TestCorrectionInvariant:
    @pytest.mark.parametrize("raw,corrected,expected_decision", CORRECTION_TRAP_CASES)
    def test_correction_trap_cases(self, raw, corrected, expected_decision):
        decision, final_text, reason = apply_correction_gate(raw, corrected)
        assert decision == expected_decision, (
            f"Expected {expected_decision.value} for raw='{raw}', corr='{corrected}', got {decision.value} ({reason})"
        )
