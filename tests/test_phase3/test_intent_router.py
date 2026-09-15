"""Tests for app/services/intent_router.py"""
import pytest
from app.services.intent_router import classify_intent, is_data_query, Intent


class TestIntentClassification:
    def test_crm_queries(self):
        res = classify_intent("Show me all active customers")
        assert res.intent == Intent.CRM_QUERY
        assert res.route == "tool"
        assert res.target_tool == "get_crm_data"

        res2 = classify_intent("How many inactive accounts are registered?")
        assert res2.intent == Intent.CRM_QUERY
        assert res2.route == "tool"

    def test_support_queries(self):
        res = classify_intent("List all open high priority tickets")
        assert res.intent == Intent.SUPPORT_QUERY
        assert res.route == "tool"
        assert res.target_tool == "get_support_tickets"

        res2 = classify_intent("Show me the open items")
        assert res2.intent == Intent.SUPPORT_QUERY
        assert res2.route == "tool"

    def test_analytics_queries(self):
        res = classify_intent("What is the daily active users trend?")
        assert res.intent == Intent.ANALYTICS_QUERY
        assert res.route == "tool"
        assert res.target_tool == "get_analytics"

        res2 = classify_intent("Give me analytics data for last week")
        assert res2.intent == Intent.ANALYTICS_QUERY
        assert res2.route == "tool"

    def test_adversarial_queries_routed_direct(self):
        # Queries that contain domain words but are conversational/general
        adversarials = [
            "My customer service was excellent today",
            "I want to show my active participation in the meeting",
            "How many people were at the event",
            "Get me a glass of water",
            "Count the number of meetings we had",
        ]
        for query in adversarials:
            res = classify_intent(query)
            assert res.route == "direct", f"Failed for {query}: got {res.route}"
            assert res.intent == Intent.DIRECT

    def test_general_non_data_queries(self):
        generals = [
            "What is the capital of France?",
            "Tell me a joke",
            "What is the weather outside?",
            "Hello there",
            "What time is it right now?",
        ]
        for query in generals:
            res = classify_intent(query)
            assert res.route == "direct"
            assert is_data_query(query) is False

    def test_empty_query(self):
        res = classify_intent("")
        assert res.intent == Intent.DIRECT
        assert res.route == "direct"
