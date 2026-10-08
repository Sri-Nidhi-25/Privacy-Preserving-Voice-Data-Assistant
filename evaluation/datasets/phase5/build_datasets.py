"""
evaluation/datasets/phase5/build_datasets.py - Constructs Phase 5 Datasets with Clean UTF-8 Formatting.
"""
import json
from pathlib import Path

BASE_DIR = Path("evaluation/datasets/phase5")


def write_jsonl(path: Path, records: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(records)} records to {path}")


def main():
    # 1. Distractors v1 (20 cases matching distractor taxonomy)
    distractor_cases = [
        {"case_id": "dis_001", "taxonomy_class": "DOMAIN_NOUN_ONLY", "input_text": "The customer.", "expected_route": "direct", "expected_tool": None, "notes": "Bare noun phrase"},
        {"case_id": "dis_002", "taxonomy_class": "DOMAIN_NOUN_ONLY", "input_text": "Tickets please.", "expected_route": "direct", "expected_tool": None, "notes": "Colloquial conductor phrase"},
        {"case_id": "dis_003", "taxonomy_class": "DOMAIN_NOUN_WITH_SENTIMENT", "input_text": "Customer feedback was overwhelmingly positive during the product launch", "expected_route": "direct", "expected_tool": None, "notes": "Sentiment description"},
        {"case_id": "dis_004", "taxonomy_class": "DOMAIN_NOUN_WITH_SENTIMENT", "input_text": "Our customer service received outstanding reviews from visitors", "expected_route": "direct", "expected_tool": None, "notes": "Positive sentiment"},
        {"case_id": "dis_005", "taxonomy_class": "DOMAIN_NOUN_IN_STORY", "input_text": "I bought a concert ticket for tomorrow night performance", "expected_route": "direct", "expected_tool": None, "notes": "Music ticket narrative"},
        {"case_id": "dis_006", "taxonomy_class": "DOMAIN_NOUN_IN_STORY", "input_text": "We booked a round-trip plane ticket to San Francisco last week", "expected_route": "direct", "expected_tool": None, "notes": "Travel ticket narrative"},
        {"case_id": "dis_007", "taxonomy_class": "DOMAIN_NOUN_IN_COMPARISON", "input_text": "Our active volunteers did better than the customer support team at the 5k run", "expected_route": "direct", "expected_tool": None, "notes": "Charity run comparison"},
        {"case_id": "dis_008", "taxonomy_class": "DOMAIN_NOUN_IN_COMPARISON", "input_text": "Comparing customer satisfaction across decades reveals interesting cultural shifts", "expected_route": "direct", "expected_tool": None, "notes": "Academic comparison"},
        {"case_id": "dis_009", "taxonomy_class": "DOMAIN_NOUN_IN_UNRELATED_REQUEST", "input_text": "Can you order two movie tickets online for the eight o clock show", "expected_route": "direct", "expected_tool": None, "notes": "Cinema ticket request"},
        {"case_id": "dis_010", "taxonomy_class": "DOMAIN_NOUN_IN_UNRELATED_REQUEST", "input_text": "Help me draft a warm thank-you note to a valued customer", "expected_route": "direct", "expected_tool": None, "notes": "Creative drafting"},
        {"case_id": "dis_011", "taxonomy_class": "MULTIPLE_DOMAIN_TERMS", "input_text": "Both the customer and the support agent attended the annual company gala", "expected_route": "direct", "expected_tool": None, "notes": "Social event narrative"},
        {"case_id": "dis_012", "taxonomy_class": "MULTIPLE_DOMAIN_TERMS", "input_text": "CRM systems and support ticket queues were discussed at the tech seminar", "expected_route": "direct", "expected_tool": None, "notes": "Educational discussion"},
        {"case_id": "dis_013", "taxonomy_class": "CROSS_DOMAIN_CONTEXT", "input_text": "The analytics seminar explored customer psychology in modern retail environments", "expected_route": "direct", "expected_tool": None, "notes": "Retail psychology"},
        {"case_id": "dis_014", "taxonomy_class": "CROSS_DOMAIN_CONTEXT", "input_text": "A support dog brings immense comfort to anxious hospital patients", "expected_route": "direct", "expected_tool": None, "notes": "Animal support context"},
        {"case_id": "dis_015", "taxonomy_class": "IMPLICIT_OPERATION", "input_text": "It would be wonderful to know what customers think about our branding", "expected_route": "direct", "expected_tool": None, "notes": "Vague desire"},
        {"case_id": "dis_016", "taxonomy_class": "IMPLICIT_OPERATION", "input_text": "I wonder if support has any free time this afternoon", "expected_route": "direct", "expected_tool": None, "notes": "Speculation"},
        {"case_id": "dis_017", "taxonomy_class": "NON_OPERATIONAL_QUESTION", "input_text": "What is the historical origin of customer loyalty programs?", "expected_route": "direct", "expected_tool": None, "notes": "History question"},
        {"case_id": "dis_018", "taxonomy_class": "NON_OPERATIONAL_QUESTION", "input_text": "Why do lottery tickets have such low odds of winning?", "expected_route": "direct", "expected_tool": None, "notes": "Lottery question"},
        {"case_id": "dis_019", "taxonomy_class": "CONVERSATIONAL_STATEMENT", "input_text": "She showed great enthusiasm for customer satisfaction", "expected_route": "direct", "expected_tool": None, "notes": "Conversational praise"},
        {"case_id": "dis_020", "taxonomy_class": "CONVERSATIONAL_STATEMENT", "input_text": "The active volcano erupted on the remote island yesterday", "expected_route": "direct", "expected_tool": None, "notes": "Geology news"},
    ]
    write_jsonl(BASE_DIR / "distractors/distractors_v1.jsonl", distractor_cases)

    # 2. Matched Pairs (10 pairs: operational x vs distractor T(x))
    pair_cases = [
        {"pair_id": "pair_01", "operational": "Show me the active customers", "distractor": "The active customers attended the annual conference", "domain": "crm", "op_tool": "get_crm_data"},
        {"pair_id": "pair_02", "operational": "List all inactive accounts", "distractor": "Inactive accounts in banks are subject to special regulatory audits", "domain": "crm", "op_tool": "get_crm_data"},
        {"pair_id": "pair_03", "operational": "List the open support tickets", "distractor": "The support tickets were discussed during the staff meeting", "domain": "support", "op_tool": "get_support_tickets"},
        {"pair_id": "pair_04", "operational": "Find high priority tickets", "distractor": "High priority tickets at the theater were sold out within minutes", "domain": "support", "op_tool": "get_support_tickets"},
        {"pair_id": "pair_05", "operational": "Get daily active users for last 7 days", "distractor": "Daily active users on social media often experience digital fatigue", "domain": "analytics", "op_tool": "get_analytics"},
        {"pair_id": "pair_06", "operational": "Display user metrics for past month", "distractor": "User metrics alone cannot capture the full emotional impact of art", "domain": "analytics", "op_tool": "get_analytics"},
        {"pair_id": "pair_07", "operational": "Fetch closed support issues", "distractor": "Closed support issues remain archived in compliance storage", "domain": "support", "op_tool": "get_support_tickets"},
        {"pair_id": "pair_08", "operational": "Retrieve 10 customer profiles", "distractor": "Customer profiles on social networks can be vulnerable to phishing", "domain": "crm", "op_tool": "get_crm_data"},
        {"pair_id": "pair_09", "operational": "Pull urgent support cases", "distractor": "Urgent support cases in emergency rooms require swift medical triage", "domain": "support", "op_tool": "get_support_tickets"},
        {"pair_id": "pair_10", "operational": "Show DAU numbers for past 30 days", "distractor": "DAU numbers fluctuate naturally over major holiday weekends", "domain": "analytics", "op_tool": "get_analytics"},
    ]
    write_jsonl(BASE_DIR / "distractors/matched_pairs_v1.jsonl", pair_cases)

    # 3. Ambiguity v1 (15 cases)
    amb_cases = [
        {"case_id": "amb_001", "input_text": "Tell me about customers", "expected_route": "direct", "notes": "Broad, no operational filter or verb"},
        {"case_id": "amb_002", "input_text": "What is happening with support?", "expected_route": "direct", "notes": "Conversational inquiry, no specific tool"},
        {"case_id": "amb_003", "input_text": "Show me data", "expected_route": "direct", "notes": "No domain or tool specified"},
        {"case_id": "amb_004", "input_text": "Tickets update", "expected_route": "direct", "notes": "Ambiguous fragment"},
        {"case_id": "amb_005", "input_text": "Can you look at analytics?", "expected_route": "direct", "notes": "Unspecified metric or timeframe"},
        {"case_id": "amb_006", "input_text": "Check status", "expected_route": "direct", "notes": "No entity specified"},
        {"case_id": "amb_007", "input_text": "Give me numbers", "expected_route": "direct", "notes": "Completely unspecified"},
        {"case_id": "amb_008", "input_text": "How are our accounts looking?", "expected_route": "direct", "notes": "Vague conversational question"},
        {"case_id": "amb_009", "input_text": "Customer stuff", "expected_route": "direct", "notes": "Slang fragment"},
        {"case_id": "amb_010", "input_text": "Look into support", "expected_route": "direct", "notes": "Vague task"},
        {"case_id": "amb_011", "input_text": "What about the users?", "expected_route": "direct", "notes": "Conversational pronoun follow-up"},
        {"case_id": "amb_012", "input_text": "Any new tickets?", "expected_route": "direct", "notes": "General question without filter"},
        {"case_id": "amb_013", "input_text": "Analytics overview", "expected_route": "direct", "notes": "Broad nominal phrase"},
        {"case_id": "amb_014", "input_text": "Are things active?", "expected_route": "direct", "notes": "Ambiguous predicate"},
        {"case_id": "amb_015", "input_text": "Find records", "expected_route": "direct", "notes": "No database domain specified"},
    ]
    write_jsonl(BASE_DIR / "ambiguity/ambiguity_v1.jsonl", amb_cases)

    # 4. Adversarial v1 (15 cases)
    adv_cases = [
        {"case_id": "adv_001", "input_text": "Our sales team crushed active customer targets this quarter", "expected_route": "direct", "notes": "Team performance narrative"},
        {"case_id": "adv_002", "input_text": "Customer responses from the product launch were incredible", "expected_route": "direct", "notes": "Launch sentiment"},
        {"case_id": "adv_003", "input_text": "Support tickets were flying in after the power outage yesterday", "expected_route": "direct", "notes": "Outage anecdote"},
        {"case_id": "adv_004", "input_text": "Clients are really engaged with our new CRM features", "expected_route": "direct", "notes": "Product engagement opinion"},
        {"case_id": "adv_005", "input_text": "The ticket inspector checked everyone on the commuter train", "expected_route": "direct", "notes": "Transit inspection"},
        {"case_id": "adv_006", "input_text": "Speeding ticket fines increased significantly in our county", "expected_route": "direct", "notes": "Traffic law"},
        {"case_id": "adv_007", "input_text": "Active volcanoes are monitored continuously by seismic sensors", "expected_route": "direct", "notes": "Geology science"},
        {"case_id": "adv_008", "input_text": "A support beam in the basement cracked during the earthquake", "expected_route": "direct", "notes": "Structural architecture"},
        {"case_id": "adv_009", "input_text": "Every customer in the coffee shop cheered for the barista", "expected_route": "direct", "notes": "Cafe story"},
        {"case_id": "adv_010", "input_text": "Golden tickets were hidden inside chocolate bars", "expected_route": "direct", "notes": "Willy Wonka allusion"},
        {"case_id": "adv_011", "input_text": "The analytics engine behind search algorithms is fascinating", "expected_route": "direct", "notes": "Technical admiration"},
        {"case_id": "adv_012", "input_text": "Support your local library by volunteering on weekends", "expected_route": "direct", "notes": "Community appeal"},
        {"case_id": "adv_013", "input_text": "Ticket scalpers were arrested outside the football stadium", "expected_route": "direct", "notes": "Crime report"},
        {"case_id": "adv_014", "input_text": "She has been an active member of the birdwatching society", "expected_route": "direct", "notes": "Club membership"},
        {"case_id": "adv_015", "input_text": "Customer service philosophies evolved dramatically over decades", "expected_route": "direct", "notes": "Philosophy history"},
    ]
    write_jsonl(BASE_DIR / "adversarial/adversarial_v1.jsonl", adv_cases)

    # 5. OOD v1 (15 cases)
    ood_cases = [
        {"case_id": "ood_001", "input_text": "Catalog every patron whose membership remains in good standing", "expected_route": "tool", "expected_tool": "get_crm_data", "notes": "Formal patron synonym for customer"},
        {"case_id": "ood_002", "input_text": "Surface any unresolved grievances marked high urgency", "expected_route": "tool", "expected_tool": "get_support_tickets", "notes": "Grievance synonym for ticket"},
        {"case_id": "ood_003", "input_text": "Tabulate platform engagement frequency over the fortnightly span", "expected_route": "tool", "expected_tool": "get_analytics", "notes": "Archaic/formal phrasing for 14 days"},
        {"case_id": "ood_004", "input_text": "I wonder if anyone filed an issue about the broken checkout button", "expected_route": "tool", "expected_tool": "get_support_tickets", "notes": "Indirect search intent"},
        {"case_id": "ood_005", "input_text": "Dig into the customer graveyard for deactivated corporate accounts", "expected_route": "tool", "expected_tool": "get_crm_data", "notes": "Metaphorical phrasing for inactive accounts"},
        {"case_id": "ood_006", "input_text": "Write a python script to simulate CRM customer retention", "expected_route": "direct", "expected_tool": None, "notes": "Code generation request"},
        {"case_id": "ood_007", "input_text": "Draft a formal apology letter to ticket holders of the canceled concert", "expected_route": "direct", "expected_tool": None, "notes": "Creative correspondence"},
        {"case_id": "ood_008", "input_text": "Explain the mathematical difference between median and mean in user metrics", "expected_route": "direct", "expected_tool": None, "notes": "Mathematical exposition"},
        {"case_id": "ood_009", "input_text": "What SQL query would join the customer table with the ticket table?", "expected_route": "direct", "expected_tool": None, "notes": "Database engineering query"},
        {"case_id": "ood_010", "input_text": "How do airlines overbook tickets without passenger rioting?", "expected_route": "direct", "expected_tool": None, "notes": "Aviation policy inquiry"},
        {"case_id": "ood_011", "input_text": "Inspect whether any client profiles lack a verified phone number", "expected_route": "tool", "expected_tool": "get_crm_data", "notes": "Inspection imperative"},
        {"case_id": "ood_012", "input_text": "Are there urgent technical hurdles logged by our tier two helpdesk?", "expected_route": "tool", "expected_tool": "get_support_tickets", "notes": "Helpdesk synonym"},
        {"case_id": "ood_013", "input_text": "Can you summarize user activity surges across the prior week?", "expected_route": "tool", "expected_tool": "get_analytics", "notes": "Activity surges synonym"},
        {"case_id": "ood_014", "input_text": "Summarize the GDPR compliance obligations for storing client records", "expected_route": "direct", "expected_tool": None, "notes": "Legal compliance inquiry"},
        {"case_id": "ood_015", "input_text": "Compare Zendesk with Salesforce Service Cloud for ticket workflows", "expected_route": "direct", "expected_tool": None, "notes": "Product comparison"},
    ]
    write_jsonl(BASE_DIR / "ood/ood_v1.jsonl", ood_cases)


if __name__ == "__main__":
    main()
