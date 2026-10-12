import ollama
import json
import re
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.services.business_rules import apply_voice_limits
from app.services.voice_optimizer import summarize_if_large
from app.config import settings

SYSTEM_PROMPT = (
    "You are a voice assistant for internal company data: customers (CRM), "
    "support tickets, and usage analytics. "
    "You have access to tools/functions. To use a tool, you MUST call the "
    "function via the provided tool-calling interface. Do NOT output JSON "
    "or code blocks – use the tool-calling mechanism directly. "
    "ONLY use a tool if the user explicitly asks about customers, tickets, or metrics. "
    "If a question involves both customers and tickets (e.g., 'How many inactive customers have open high priority tickets?'), "
    "you can and should call MULTIPLE tools: call get_crm_data with the customer filters, and call get_support_tickets with the ticket filters. "
    "For general questions (like capital cities, jokes, weather), answer directly without tools. "
    "Always use the tool‑calling interface – never output JSON manually."
)

CORRECTION_PROMPT = (
    "You are a transcript correction assistant for a voice system that only "
    "understands queries about customers (CRM), support tickets, and usage "
    "analytics. The transcript below came from a speech-to-text system and "
    "may contain misheard or garbled words caused by audio distortion.\n\n"
    "Known domain vocabulary includes: customer, customers, active, "
    "inactive, ticket, tickets, support, open, closed, priority, low, "
    "medium, high, analytics, daily active users, average, count, how many, "
    "show me, list, get.\n\n"
    "If the transcript appears to be asking about this domain data, correct "
    "any garbled or misheard words to the closest sensible domain term, "
    "keeping the original sentence structure and intent as close to the "
    "original as possible. Do not add new information, do not answer the "
    "question, do not invent details that aren't implied by the transcript. "
    "If the transcript is clearly NOT about this domain (general knowledge, "
    "small talk, greetings), return it completely unchanged.\n\n"
    "Output ONLY the corrected transcript text. No explanation, no quotes, "
    "no preamble, no markdown."
)

_REFUSAL_MARKERS = (
    "i can't", "i cannot", "i can not", "i'm not able", "i am not able",
    "as an ai", "i apologize", "i'm sorry", "sorry, i", "i don't have the ability",
    "i do not have the ability", "as a language model", "i'm unable", "i am unable",
)


def _looks_like_refusal_or_commentary(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


def _word_overlap_ratio(a: str, b: str) -> float:
    """Fraction of a's words that also appear in b (case-insensitive).
    A real correction should share most of its words with the original --
    it's fixing a handful of garbled words, not rewriting the sentence."""
    a_words = set(re.findall(r"[a-z0-9']+", a.lower()))
    b_words = set(re.findall(r"[a-z0-9']+", b.lower()))
    if not a_words:
        return 1.0
    return len(a_words & b_words) / len(a_words)


from app.services.correction_guard import apply_correction_gate, CorrectionDecision


def correct_transcript(raw_transcript: str, model: str, client: Optional[Any] = None) -> dict:
    """
    Applies LLM transcript correction followed by deterministic reliability gate.

    Returns dict:
      text: str
      correction_attempted: bool
      correction_changed: bool
      correction_accepted: bool
      correction_rejected: bool
      fallback_used: bool
      decision: str
      rejection_reason: Optional[str]
    """
    text = raw_transcript.strip()
    res = {
        "text": raw_transcript,
        "correction_attempted": False,
        "correction_changed": False,
        "correction_accepted": False,
        "correction_rejected": False,
        "fallback_used": False,
        "decision": CorrectionDecision.KEEP_RAW.value,
        "rejection_reason": None,
    }
    if not text:
        return res

    res["correction_attempted"] = True
    chat_fn = client.chat if client is not None else ollama.chat

    try:
        response = chat_fn(
            model=model,
            messages=[
                {"role": "system", "content": CORRECTION_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        corrected = response["message"]["content"].strip()
    except Exception as exc:
        res["fallback_used"] = True
        res["rejection_reason"] = f"correction_call_failed: {exc}"
        return res

    # Apply the Phase 3 deterministic reliability gate
    decision, final_text, reason = apply_correction_gate(text, corrected)
    res["decision"] = decision.value
    res["rejection_reason"] = reason

    if decision == CorrectionDecision.ACCEPT_CORRECTION:
        res["text"] = final_text
        res["correction_changed"] = (final_text.lower() != text.lower())
        res["correction_accepted"] = True
    else:
        res["text"] = raw_transcript
        res["correction_rejected"] = True
        res["fallback_used"] = True

    return res


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_crm_data",
            "description": "Retrieve customer relationship data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "inactive"]},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_support_tickets",
            "description": "Retrieve support tickets with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["open", "closed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_analytics",
            "description": "Retrieve analytics metrics like daily active users.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["daily_active_users"]},
                    "days": {"type": "integer", "default": 7},
                },
            },
        },
    },
]

SOURCE_LABELS = {
    "get_crm_data": "crm",
    "get_support_tickets": "support",
    "get_analytics": "analytics",
}

SCHEMA = {
    "get_crm_data": {
        "properties": {
            "status": {"type": "string", "enum": ["active", "inactive"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        }
    },
    "get_support_tickets": {
        "properties": {
            "status": {"type": "string", "enum": ["open", "closed"]},
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            "limit": {"type": "integer", "minimum": 0, "maximum": 100},
        }
    },
    "get_analytics": {
        "properties": {
            "metric": {"type": "string", "enum": ["daily_active_users"]},
            "days": {"type": "integer", "minimum": 0, "maximum": 365},
        }
    },
}

# Entity-grounded intent routing
from app.services.intent_router import is_data_query, classify_intent, Intent
from app.services.abstention_router import evaluate_abstention, Decision

# Preserved for backward compatibility
DATA_KEYWORDS = [
    "customer", "ticket", "support", "analytics", "active", "inactive",
    "open", "closed", "priority", "daily", "users", "metric", "average",
    "count", "how many", "show me", "list", "get"
]

def _is_data_query(text: str) -> bool:
    return is_data_query(text)

def _validate_args(func_name: str, args: dict) -> tuple[bool, str]:
    schema = SCHEMA.get(func_name)
    if not schema:
        return False, f"Unknown function {func_name}"
    for key, value in args.items():
        prop = schema["properties"].get(key)
        if not prop:
            return False, f"Unexpected argument '{key}'"
        if prop["type"] == "integer":
            if not isinstance(value, int):
                return False, f"'{key}' must be an integer"
            if "minimum" in prop and value < prop["minimum"]:
                return False, f"'{key}' must be at least {prop['minimum']}"
            if "maximum" in prop and value > prop["maximum"]:
                return False, f"'{key}' must be at most {prop['maximum']}"
        if prop["type"] == "string" and "enum" in prop:
            if value not in prop["enum"]:
                return False, f"'{key}' must be one of {prop['enum']}"
    return True, ""

def _coerce_args(func_name: str, args: dict) -> dict:
    """
    Ollama's tool-calling occasionally returns numeric arguments as strings
    (e.g. {"days": "2"} instead of {"days": 2}), which _validate_args then
    rejects outright since it does a strict isinstance(value, int) check.
    Coerce clean numeric strings to int before validation so a correctly-
    intentioned tool call doesn't fail purely on JSON typing, while leaving
    genuinely malformed values (e.g. "two", "2.5") to fail validation as
    they should.
    """
    schema = SCHEMA.get(func_name)
    if not schema:
        return args
    coerced = dict(args)
    for key, value in list(coerced.items()):
        prop = schema["properties"].get(key)
        if prop and prop["type"] == "integer" and isinstance(value, str):
            stripped = value.strip()
            if stripped.lstrip("-").isdigit():
                coerced[key] = int(stripped)
    return coerced


def _empty_metadata() -> dict:
    return {
        "data_sources_used": [],
        "result_count": 0,
        "freshness": "unknown",
        "freshness_status": "unknown",
        "freshness_warning": None,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_last_updated": "unknown",
        "tool_calls": [],
        "correction_attempted": False,
        "correction_changed": False,
        "correction_accepted": False,
        "correction_rejected": False,
        "fallback_used": False,
        "retry_attempted": False,
        "retry_count": 0,
        "retry_succeeded": False,
        "retry_reason": None,
    }


def _extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract one or more JSON tool-call objects from the text.
    Returns a list of dicts, each with keys "name" and "arguments".
    """
    def extract_object(s: str, start: int) -> Optional[str]:
        brace_count = 0
        in_string = False
        escape = False
        for i, ch in enumerate(s[start:], start):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    return s[start:i+1]
        return None

    results = []
    for i, ch in enumerate(text):
        if ch == '{':
            obj_str = extract_object(text, i)
            if obj_str:
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict) and "name" in obj and "arguments" in obj:
                        results.append(obj)
                    elif isinstance(obj, dict) and "function" in obj and isinstance(obj["function"], dict):
                        func = obj["function"]
                        if "name" in func and "arguments" in func:
                            results.append({"name": func["name"], "arguments": func["arguments"]})
                except:
                    pass

    return results


class LLMOrchestrator:
    def __init__(self, model: Optional[str] = None):
        self.model = (model or settings.OLLAMA_MODEL).strip()
        self.client = ollama.Client(timeout=settings.LLM_TIMEOUT_SECONDS)
        self.connector_map = {
            "get_crm_data": CRMConnector(),
            "get_support_tickets": SupportConnector(),
            "get_analytics": AnalyticsConnector(),
        }

    def _execute_tool_calls(
        self,
        tool_calls: List[Dict],
        detected_intent: Optional[Intent] = None,
    ) -> tuple[str, dict]:
        """Process a list of tool calls and return (answer_text, metadata)."""
        INTENT_TOOL_MAP = {
            Intent.CRM_QUERY: ["get_crm_data"],
            Intent.SUPPORT_QUERY: ["get_support_tickets"],
            Intent.ANALYTICS_QUERY: ["get_analytics"],
            Intent.MULTI_DOMAIN_QUERY: ["get_crm_data", "get_support_tickets", "get_analytics"],
        }

        answers = []
        sources_used = []
        total_results = 0
        call_log = []
        collected_data_by_tool = {}
        source_timestamps = []
        latest_freshness_status = "unknown"
        freshness_warnings = []
        overall_retry_attempted = False
        overall_retry_count = 0
        overall_retry_succeeded = False

        for call in tool_calls:
            func_name = call["function"]["name"]

            # Intent vs Tool alignment check (Section 17)
            if detected_intent in INTENT_TOOL_MAP:
                allowed_tools = INTENT_TOOL_MAP[detected_intent]
                if func_name not in allowed_tools:
                    err_meta = _empty_metadata()
                    err_meta.update({
                        "tool_selection_error": f"Tool '{func_name}' is incompatible with detected intent '{detected_intent.value}'",
                        "failure_type": "tool_selection_mismatch",
                    })
                    return f"Sorry, tool {func_name} is incompatible with your request.", err_meta

            args = _coerce_args(func_name, call["function"]["arguments"])

            valid, error_msg = _validate_args(func_name, args)
            if not valid:
                err_meta = _empty_metadata()
                err_meta.update({
                    "validation_error": error_msg,
                    "invalid_args": args,
                    "failure_type": "invalid_tool_arguments",
                })
                return f"Sorry, I couldn't interpret that filter: {error_msg}", err_meta

            connector = self.connector_map.get(func_name)
            if not connector:
                continue

            # Bounded retry policy for transient connector failures (Sections 19, 20)
            retry_count = 0
            max_retries = getattr(settings, "MAX_RETRIES", 2)
            conn_result = connector.fetch_result(**args)

            while not conn_result.success and retry_count < max_retries:
                err_str = str(conn_result.error or "").lower()
                is_transient = any(w in err_str for w in ["timeout", "temporary", "connection", "locked", "busy"])
                if not is_transient:
                    break
                retry_count += 1
                conn_result = connector.fetch_result(**args)

            if retry_count > 0:
                overall_retry_attempted = True
                overall_retry_count += retry_count
                if conn_result.success:
                    overall_retry_succeeded = True

            # Zero-fabrication guarantee (Section 31): failed connector never fabricates empty data
            if not conn_result.success:
                err_meta = _empty_metadata()
                err_meta.update({
                    "connector_error": conn_result.error,
                    "tool_calls": call_log,
                    "retry_attempted": overall_retry_attempted,
                    "retry_count": overall_retry_count,
                    "retry_succeeded": overall_retry_succeeded,
                    "failure_type": "connector_failed",
                })
                return f"Sorry, could not retrieve data from {func_name}: {conn_result.error}", err_meta

            raw_data = conn_result.data
            collected_data_by_tool[func_name] = raw_data

            if conn_result.source_last_updated:
                source_timestamps.append(conn_result.source_last_updated)
            if conn_result.freshness_status != "unknown":
                latest_freshness_status = conn_result.freshness_status
            if conn_result.freshness_warning:
                freshness_warnings.append(conn_result.freshness_warning)

            optimized = apply_voice_limits(summarize_if_large(raw_data))
            ans = self._format_answer(optimized, func_name)
            answers.append(ans)
            sources_used.append(SOURCE_LABELS.get(func_name, func_name))
            total_results += len(raw_data)
            call_log.append({
                "source": SOURCE_LABELS.get(func_name, func_name),
                "args": args,
                "result_count": len(raw_data),
                "freshness_status": conn_result.freshness_status,
            })

        if not answers:
            return "Sorry, I couldn't find the right data source.", _empty_metadata()

        # Cross-domain correlation synthesis: if both CRM and Support data were retrieved, perform join
        final_answer_text = " ".join(answers)
        if "get_crm_data" in collected_data_by_tool and "get_support_tickets" in collected_data_by_tool:
            c_data = collected_data_by_tool["get_crm_data"]
            s_data = collected_data_by_tool["get_support_tickets"]
            c_ids = {c.get("customer_id") for c in c_data if "customer_id" in c}
            correlated_tickets = [t for t in s_data if t.get("customer_id") in c_ids]
            unique_customers_with_tickets = {t.get("customer_id") for t in correlated_tickets}
            final_answer_text = (
                f"Across {len(c_data)} matching customers and {len(s_data)} tickets, "
                f"there are {len(correlated_tickets)} tickets belonging to {len(unique_customers_with_tickets)} of those customers."
            )

        source_last_updated = max(source_timestamps) if source_timestamps else "unknown"
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = {
            "data_sources_used": sources_used,
            "result_count": total_results,
            "retrieved_at": now_iso,
            "source_last_updated": source_last_updated,
            "freshness": f"Source last updated: {source_last_updated}" if source_last_updated != "unknown" else "unknown",
            "freshness_status": latest_freshness_status,
            "freshness_warning": "; ".join(freshness_warnings) if freshness_warnings else None,
            "tool_calls": call_log,
            "retry_attempted": overall_retry_attempted,
            "retry_count": overall_retry_count,
            "retry_succeeded": overall_retry_succeeded,
        }
        return final_answer_text, metadata

    def process_query(self, user_text: str, enable_abstention: bool = True) -> dict:
        # --- Correction pass: fix likely STT garbling against known domain
        # vocabulary before any routing decision is made. ---
        t_corr_start = time.perf_counter()
        corr = correct_transcript(user_text, self.model, client=self.client)
        corr_latency_ms = int((time.perf_counter() - t_corr_start) * 1000)
        corrected_text = corr["text"]

        def _apply_corr_meta(meta: dict) -> dict:
            meta["raw_transcript"] = user_text
            meta["corrected_transcript"] = corrected_text
            meta["correction_attempted"] = corr["correction_attempted"]
            meta["correction_changed"] = corr["correction_changed"]
            meta["correction_accepted"] = corr["correction_accepted"]
            meta["correction_rejected"] = corr["correction_rejected"]
            meta["fallback_used"] = corr["fallback_used"]
            meta["transcript_was_corrected"] = corr["correction_changed"]
            meta["correction_latency_ms"] = corr_latency_ms
            if "decision" in corr:
                meta["correction_decision"] = corr["decision"]
            if corr.get("rejection_reason"):
                meta["correction_rejection_reason"] = corr["rejection_reason"]
            return meta

        try:
            t_rout_start = time.perf_counter()
            abstention_latency_ms = 0

            if enable_abstention:
                abs_res = evaluate_abstention(corrected_text, threshold=0.50)
                abstention_latency_ms = int((time.perf_counter() - t_rout_start) * 1000)
                routing_latency_ms = abstention_latency_ms
                detected_intent = abs_res.intent

                # Check if selective abstention withheld tool execution
                if abs_res.decision == Decision.ABSTAIN:
                    metadata = _apply_corr_meta(_empty_metadata())
                    metadata.update({
                        "classified_intent": detected_intent.value,
                        "abstention_decision": "ABSTAIN",
                        "abstention_reason": abs_res.reason,
                        "abstention_confidence": abs_res.confidence,
                        "execution_prevented_by_abstention": True,
                        "correction_latency_ms": corr_latency_ms,
                        "routing_latency_ms": routing_latency_ms,
                        "abstention_latency_ms": abstention_latency_ms,
                        "tool_latency_ms": 0,
                    })
                    answer = f"I cannot run a data query for this request: {abs_res.reason}"
                    return {
                        "answer": answer,
                        "metadata": metadata
                    }

                if abs_res.decision == Decision.DIRECT:
                    # Non-domain query, direct conversation without tools
                    t_llm_start = time.perf_counter()
                    response = self.client.chat(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": corrected_text + " (Answer directly, no tools or APIs.)"}
                        ],
                    )
                    metadata = _apply_corr_meta(_empty_metadata())
                    metadata.update({
                        "classified_intent": detected_intent.value,
                        "abstention_decision": "DIRECT",
                        "abstention_reason": abs_res.reason,
                        "abstention_confidence": abs_res.confidence,
                        "execution_prevented_by_abstention": False,
                        "correction_latency_ms": corr_latency_ms,
                        "routing_latency_ms": routing_latency_ms,
                        "abstention_latency_ms": abstention_latency_ms,
                        "tool_latency_ms": 0,
                    })
                    return {
                        "answer": response["message"]["content"],
                        "metadata": metadata
                    }

                # Decision is EXECUTE
                abs_meta = {
                    "abstention_decision": "EXECUTE",
                    "abstention_reason": abs_res.reason,
                    "abstention_confidence": abs_res.confidence,
                    "execution_prevented_by_abstention": False,
                    "abstention_latency_ms": abstention_latency_ms,
                }
            else:
                # Baseline Phase 4.6 routing without abstention
                intent_res = classify_intent(corrected_text)
                routing_latency_ms = int((time.perf_counter() - t_rout_start) * 1000)
                detected_intent = intent_res.intent
                should_execute_tool = (intent_res.route == "tool")
                abs_meta = {
                    "abstention_decision": "BASELINE_NO_ABSTENTION",
                    "abstention_reason": "Selective abstention disabled (Baseline mode).",
                    "abstention_confidence": 1.0,
                    "execution_prevented_by_abstention": False,
                    "abstention_latency_ms": 0,
                }

                if not should_execute_tool:
                    response = self.client.chat(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": corrected_text + " (Answer directly, no tools or APIs.)"}
                        ],
                    )
                    metadata = _apply_corr_meta(_empty_metadata())
                    metadata.update(abs_meta)
                    metadata.update({
                        "classified_intent": detected_intent.value,
                        "correction_latency_ms": corr_latency_ms,
                        "routing_latency_ms": routing_latency_ms,
                        "tool_latency_ms": 0,
                    })
                    return {
                        "answer": response["message"]["content"],
                        "metadata": metadata
                    }

            # Authorized to execute tools
            t_tool_start = time.perf_counter()
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": corrected_text},
                ],
                tools=TOOLS,
            )
            message = response["message"]
            tool_calls = message.get("tool_calls")

            if tool_calls:
                answer, metadata = self._execute_tool_calls(tool_calls, detected_intent=detected_intent)
                tool_latency_ms = int((time.perf_counter() - t_tool_start) * 1000)
                metadata.update(abs_meta)
                metadata["classified_intent"] = detected_intent.value
                metadata["correction_latency_ms"] = corr_latency_ms
                metadata["routing_latency_ms"] = routing_latency_ms
                metadata["tool_latency_ms"] = tool_latency_ms
                return {"answer": answer, "metadata": _apply_corr_meta(metadata)}

            content = message.get("content", "")
            extracted_calls = _extract_json_from_text(content)
            if extracted_calls:
                synthetic_calls = [
                    {"function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in extracted_calls
                ]
                answer, metadata = self._execute_tool_calls(synthetic_calls, detected_intent=detected_intent)
                tool_latency_ms = int((time.perf_counter() - t_tool_start) * 1000)
                metadata.update(abs_meta)
                metadata["classified_intent"] = detected_intent.value
                metadata["correction_latency_ms"] = corr_latency_ms
                metadata["routing_latency_ms"] = routing_latency_ms
                metadata["tool_latency_ms"] = tool_latency_ms
                return {"answer": answer, "metadata": _apply_corr_meta(metadata)}

            tool_latency_ms = int((time.perf_counter() - t_tool_start) * 1000)
            metadata = _apply_corr_meta(_empty_metadata())
            metadata.update(abs_meta)
            metadata["classified_intent"] = detected_intent.value
            metadata["correction_latency_ms"] = corr_latency_ms
            metadata["routing_latency_ms"] = routing_latency_ms
            metadata["tool_latency_ms"] = tool_latency_ms
            return {
                "answer": content if content else "I didn't understand that query.",
                "metadata": metadata
            }
        except Exception as exc:
            metadata = _apply_corr_meta(_empty_metadata())
            metadata["llm_error"] = str(exc)
            metadata["failure_type"] = "orchestrator_exception"
            return {
                "answer": "Sorry, I am currently unable to process your request with the language model.",
                "metadata": metadata,
            }

    @staticmethod
    def _format_answer(data, func_name) -> str:
        if not data:
            return "No data found."
        
        # Check if this is a summary dict (produced by summarize_if_large)
        if len(data) == 1 and "summary" in data[0]:
            return data[0]["summary"]   # e.g., "50 records found. Showing first 10."
        
        if func_name == "get_crm_data":
            return f"Found {len(data)} customers."
        if func_name == "get_support_tickets":
            return f"Found {len(data)} support tickets."
        if func_name == "get_analytics" and "value" in data[0]:
            avg = sum(d["value"] for d in data) / len(data)
            return f"Average value over the period is {avg:.0f}."
        return str(data)[:200]