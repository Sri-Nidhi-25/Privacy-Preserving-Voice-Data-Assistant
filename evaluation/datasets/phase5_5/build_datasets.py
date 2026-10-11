"""
evaluation/datasets/phase5_5/build_datasets.py

Generates the Phase 5.5 End-to-End Voice Reliability Evaluation Datasets.
Covers 6 distinct categories:
  A: Clean Operational Requests (N=10)
  B: Semantic Distractors (N=10)
  C: Ambiguous Requests (N=6)
  D: Linguistic Variation (N=6)
  E: Acoustic Perturbations (N=4 base queries evaluated across clean, 20dB, 10dB)
  F: Failure Injection / Boundary Cases (N=6)
Total: 40 structured test cases.
"""
from pathlib import Path
import json

BASE_DIR = Path("evaluation/datasets/phase5_5")
CLEAN_DIR = BASE_DIR / "clean"
DISTRACTOR_DIR = BASE_DIR / "semantic_distractors"
AMBIGUOUS_DIR = BASE_DIR / "ambiguous"
VARIATION_DIR = BASE_DIR / "linguistic_variation"
ACOUSTIC_DIR = BASE_DIR / "acoustic"
FAILURE_DIR = BASE_DIR / "failure_cases"

for d in [CLEAN_DIR, DISTRACTOR_DIR, AMBIGUOUS_DIR, VARIATION_DIR, ACOUSTIC_DIR, FAILURE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Category A: Clean Operational Requests (N=10)
CLEAN_CASES = [
    {
        "case_id": "e2e_clean_001",
        "category": "clean_operational",
        "input_text": "Show me the top five active customers",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active", "limit": 5},
        "notes": "Standard CRM query with status and limit constraints."
    },
    {
        "case_id": "e2e_clean_002",
        "category": "clean_operational",
        "input_text": "List all inactive accounts",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "inactive"},
        "notes": "CRM inactive query."
    },
    {
        "case_id": "e2e_clean_003",
        "category": "clean_operational",
        "input_text": "Show me the open support tickets",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "open"},
        "notes": "Support query for open tickets."
    },
    {
        "case_id": "e2e_clean_004",
        "category": "clean_operational",
        "input_text": "Fetch high priority tickets",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"priority": "high"},
        "notes": "Support query for high priority tickets."
    },
    {
        "case_id": "e2e_clean_005",
        "category": "clean_operational",
        "input_text": "Get daily active users for the last seven days",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_analytics",
        "expected_args": {"metric": "daily_active_users", "days": 7},
        "notes": "Analytics metric request with time window."
    },
    {
        "case_id": "e2e_clean_006",
        "category": "clean_operational",
        "input_text": "Display user metrics for the past thirty days",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_analytics",
        "expected_args": {"days": 30},
        "notes": "Analytics metric request with 30-day window."
    },
    {
        "case_id": "e2e_clean_007",
        "category": "clean_operational",
        "input_text": "List all closed support issues",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "closed"},
        "notes": "Support query for closed issues."
    },
    {
        "case_id": "e2e_clean_008",
        "category": "clean_operational",
        "input_text": "Retrieve ten customer profiles",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"limit": 10},
        "notes": "CRM query with limit."
    },
    {
        "case_id": "e2e_clean_009",
        "category": "clean_operational",
        "input_text": "Pull urgent support cases",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"priority": "high"},
        "notes": "Support query mapping urgent to high priority."
    },
    {
        "case_id": "e2e_clean_010",
        "category": "clean_operational",
        "input_text": "What is the capital of France",
        "expected_route": "direct",
        "expected_action": "DIRECT",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Factual non-domain query, direct LLM answer."
    },
]

# Category B: Semantic Distractors (N=10)
DISTRACTOR_CASES = [
    {
        "case_id": "e2e_dist_001",
        "category": "semantic_distractor",
        "input_text": "Customer feedback was overwhelmingly positive during the quarterly review",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Customer in sentiment statement."
    },
    {
        "case_id": "e2e_dist_002",
        "category": "semantic_distractor",
        "input_text": "The active customers attended the annual conference in Chicago",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Narrative sentence containing active customers."
    },
    {
        "case_id": "e2e_dist_003",
        "category": "semantic_distractor",
        "input_text": "The support tickets were discussed during the morning staff meeting",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Conversational mention of support tickets."
    },
    {
        "case_id": "e2e_dist_004",
        "category": "semantic_distractor",
        "input_text": "High priority tickets at the theater were sold out within five minutes",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Theater tickets with high priority."
    },
    {
        "case_id": "e2e_dist_005",
        "category": "semantic_distractor",
        "input_text": "Daily active users on social media often experience digital fatigue",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: General sociological remark containing DAU."
    },
    {
        "case_id": "e2e_dist_006",
        "category": "semantic_distractor",
        "input_text": "User metrics alone cannot capture the full emotional impact of artistic work",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Philosophical commentary on metrics."
    },
    {
        "case_id": "e2e_dist_007",
        "category": "semantic_distractor",
        "input_text": "Customer profiles on public networks can be vulnerable to phishing scams",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Cybersecurity discussion containing customer profiles."
    },
    {
        "case_id": "e2e_dist_008",
        "category": "semantic_distractor",
        "input_text": "Our emotional support dog greeted visitors at the hospital entrance",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Support animal context."
    },
    {
        "case_id": "e2e_dist_009",
        "category": "semantic_distractor",
        "input_text": "Speeding tickets were handed out along the highway yesterday morning",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Traffic tickets."
    },
    {
        "case_id": "e2e_dist_010",
        "category": "semantic_distractor",
        "input_text": "Active volunteers cleaned up the local community park over the weekend",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Distractor: Active volunteers community context."
    },
]

# Category C: Ambiguous Requests (N=6)
AMBIGUOUS_CASES = [
    {
        "case_id": "e2e_amb_001",
        "category": "ambiguous",
        "input_text": "Tell me about customers",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Broad, underspecified query with no retrieval directive."
    },
    {
        "case_id": "e2e_amb_002",
        "category": "ambiguous",
        "input_text": "Check the tickets",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Vague command missing status or priority filters."
    },
    {
        "case_id": "e2e_amb_003",
        "category": "ambiguous",
        "input_text": "Show me the analytics",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Underspecified metric request."
    },
    {
        "case_id": "e2e_amb_004",
        "category": "ambiguous",
        "input_text": "What about the metrics",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Incomplete conversational query without target metric."
    },
    {
        "case_id": "e2e_amb_005",
        "category": "ambiguous",
        "input_text": "Look into the customer tickets and user metrics",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Cross-domain conflict spanning CRM, Support, and Analytics."
    },
    {
        "case_id": "e2e_amb_006",
        "category": "ambiguous",
        "input_text": "Can we see some data from the database",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Generic data inquiry lacking domain target."
    },
]

# Category D: Linguistic Variation (N=6)
VARIATION_CASES = [
    {
        "case_id": "e2e_var_001",
        "category": "linguistic_variation",
        "input_text": "Could you please show me the active customers if you do not mind",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active"},
        "notes": "Polite phrasing with subjunctive clause."
    },
    {
        "case_id": "e2e_var_002",
        "category": "linguistic_variation",
        "input_text": "Um, could you like, list the open support tickets for me?",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "open"},
        "notes": "Conversational fillers ('um', 'like')."
    },
    {
        "case_id": "e2e_var_003",
        "category": "linguistic_variation",
        "input_text": "I'd really appreciate it if you could pull up daily active users for the last seven days",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_analytics",
        "expected_args": {"metric": "daily_active_users", "days": 7},
        "notes": "Complex sentence embedding imperative request."
    },
    {
        "case_id": "e2e_var_004",
        "category": "linguistic_variation",
        "input_text": "Let's see the closed support tickets please",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "closed"},
        "notes": "First-person plural cohortative framing ('Let's see')."
    },
    {
        "case_id": "e2e_var_005",
        "category": "linguistic_variation",
        "input_text": "Can you fetch the top five customers who are active right now?",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active", "limit": 5},
        "notes": "Relative clause syntax ('who are active right now')."
    },
    {
        "case_id": "e2e_var_006",
        "category": "linguistic_variation",
        "input_text": "Give me, uh, the high priority tickets, thanks",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"priority": "high"},
        "notes": "Imperative with interjection ('uh') and trailing courtesy."
    },
]

# Category E: Acoustic Base Phrases (N=4 phrases evaluated at clean, 20dB, 10dB)
ACOUSTIC_CASES = [
    {
        "case_id": "e2e_acoust_001",
        "category": "acoustic_perturbation",
        "input_text": "Show me all high priority open tickets",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "open", "priority": "high"},
        "notes": "Canonical acoustic phrase: support combined filter."
    },
    {
        "case_id": "e2e_acoust_002",
        "category": "acoustic_perturbation",
        "input_text": "How many active customers do we have",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active"},
        "notes": "Canonical acoustic phrase: CRM interrogative."
    },
    {
        "case_id": "e2e_acoust_003",
        "category": "acoustic_perturbation",
        "input_text": "What is the daily active users trend for the last seven days",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_analytics",
        "expected_args": {"metric": "daily_active_users", "days": 7},
        "notes": "Canonical acoustic phrase: Analytics trend."
    },
    {
        "case_id": "e2e_acoust_004",
        "category": "acoustic_perturbation",
        "input_text": "The active customers attended the annual conference",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Canonical acoustic distractor: tests whether noise alters abstention."
    },
]

# Category F: Failure Injection Cases (N=6)
FAILURE_CASES = [
    {
        "case_id": "e2e_fail_001",
        "category": "failure_injection",
        "injection_type": "transient_connector_error",
        "input_text": "Show me the active customers",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "active"},
        "notes": "Injected connector timeout / locked error to verify bounded retry."
    },
    {
        "case_id": "e2e_fail_002",
        "category": "failure_injection",
        "injection_type": "repeated_connector_error",
        "input_text": "Show me the open support tickets",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_support_tickets",
        "expected_args": {"status": "open"},
        "notes": "Persistent connector failure; must fail gracefully without fabricating empty results."
    },
    {
        "case_id": "e2e_fail_003",
        "category": "failure_injection",
        "injection_type": "malformed_arguments",
        "input_text": "Show me negative five customers",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"limit": -5},
        "notes": "Negative integer filter; must trigger argument validation rejection."
    },
    {
        "case_id": "e2e_fail_004",
        "category": "failure_injection",
        "injection_type": "empty_audio",
        "input_text": "",
        "expected_route": "direct",
        "expected_action": "ABSTAIN",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Zero-amplitude audio file; must trigger low-confidence STT abstention."
    },
    {
        "case_id": "e2e_fail_005",
        "category": "failure_injection",
        "injection_type": "invalid_audio_format",
        "input_text": "CORRUPT_BYTES",
        "expected_route": "error",
        "expected_action": "ERROR",
        "expected_tool": None,
        "expected_args": {},
        "notes": "Unparseable audio bytes; audio validation layer must reject safely."
    },
    {
        "case_id": "e2e_fail_006",
        "category": "failure_injection",
        "injection_type": "tts_synthesis_failure",
        "input_text": "List the inactive customers",
        "expected_route": "tool",
        "expected_action": "EXECUTE",
        "expected_tool": "get_crm_data",
        "expected_args": {"status": "inactive"},
        "notes": "Simulated TTS failure; text response must be preserved even if audio fails."
    },
]


def write_jsonl(filepath: Path, data: list):
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(data)} items to {filepath}")


def main():
    write_jsonl(CLEAN_DIR / "clean_v1.jsonl", CLEAN_CASES)
    write_jsonl(DISTRACTOR_DIR / "distractors_v1.jsonl", DISTRACTOR_CASES)
    write_jsonl(AMBIGUOUS_DIR / "ambiguous_v1.jsonl", AMBIGUOUS_CASES)
    write_jsonl(VARIATION_DIR / "variation_v1.jsonl", VARIATION_CASES)
    write_jsonl(ACOUSTIC_DIR / "acoustic_v1.jsonl", ACOUSTIC_CASES)
    write_jsonl(FAILURE_DIR / "failures_v1.jsonl", FAILURE_CASES)
    print("All Phase 5.5 evaluation datasets built successfully.")


if __name__ == "__main__":
    main()
