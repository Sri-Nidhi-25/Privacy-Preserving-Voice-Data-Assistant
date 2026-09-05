import ollama
import json
import re
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


def correct_transcript(raw_transcript: str, model: str) -> tuple[str, bool]:
    """
    Returns (corrected_text, was_changed). Falls back to the raw transcript
    on any failure or suspicious output, since a bad correction is worse
    than no correction -- it would silently replace what was actually said.
    """
    text = raw_transcript.strip()
    if not text:
        return raw_transcript, False

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": CORRECTION_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        corrected = response["message"]["content"].strip()
    except Exception:
        # If the correction call itself fails (model down, timeout, etc.),
        # don't let that take down the whole query -- just skip correction.
        return raw_transcript, False

    # Guardrails: reject corrections that look like the model went off-script
    # (empty, wildly longer/shorter, contains refusal/meta language, or
    # shares too few words with the original to plausibly be "the same
    # sentence with a few words fixed"). Any one of these firing means we
    # trust the raw transcript over the "corrected" one.
    if not corrected:
        return raw_transcript, False
    if len(corrected) > len(text) * 2 or len(corrected) < len(text) * 0.4:
        return raw_transcript, False
    if _looks_like_refusal_or_commentary(corrected):
        return raw_transcript, False
    if _word_overlap_ratio(text, corrected) < 0.5:
        return raw_transcript, False

    return corrected, corrected.lower() != text.lower()


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

# Keywords that indicate a data query
DATA_KEYWORDS = [
    "customer", "ticket", "support", "analytics", "active", "inactive",
    "open", "closed", "priority", "daily", "users", "metric", "average",
    "count", "how many", "show me", "list", "get"
]

def _is_data_query(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in DATA_KEYWORDS)

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
    return {"data_sources_used": [], "result_count": 0, "freshness": "unknown", "tool_calls": []}

def _extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract one or more JSON tool-call objects from the text.
    Returns a list of dicts, each with keys "name" and "arguments".
    """
    # Helper: find a balanced JSON object starting at a given position
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
        self.model = model or settings.OLLAMA_MODEL
        self.connector_map = {
            "get_crm_data": CRMConnector(),
            "get_support_tickets": SupportConnector(),
            "get_analytics": AnalyticsConnector(),
        }

    def _execute_tool_calls(self, tool_calls: List[Dict]) -> tuple[str, dict]:
        """Process a list of tool calls and return (answer_text, metadata)."""
        answers = []
        sources_used = []
        total_results = 0
        call_log = []

        for call in tool_calls:
            func_name = call["function"]["name"]
            args = _coerce_args(func_name, call["function"]["arguments"])

            valid, error_msg = _validate_args(func_name, args)
            if not valid:
                return (
                    f"Sorry, I couldn't interpret that filter: {error_msg}",
                    {
                        "data_sources_used": [],
                        "result_count": 0,
                        "freshness": "unknown",
                        "validation_error": error_msg,
                        "invalid_args": args,
                    }
                )

            connector = self.connector_map.get(func_name)
            if not connector:
                continue

            raw_data = connector.fetch(**args)
            # optimized = summarize_if_large(apply_voice_limits(raw_data))
            optimized = apply_voice_limits(summarize_if_large(raw_data))
            answers.append(self._format_answer(optimized, func_name))
            sources_used.append(SOURCE_LABELS.get(func_name, func_name))
            total_results += len(raw_data)
            call_log.append({
                "source": SOURCE_LABELS.get(func_name, func_name),
                "args": args,
                "result_count": len(raw_data),
            })

        if not answers:
            return "Sorry, I couldn't find the right data source.", _empty_metadata()

        metadata = {
            "data_sources_used": sources_used,
            "result_count": total_results,
            "freshness": f"Data as of {datetime.now(timezone.utc).isoformat()}",
            "tool_calls": call_log,
        }
        return " ".join(answers), metadata

    def process_query(self, user_text: str) -> dict:
        # --- Correction pass: fix likely STT garbling against known domain
        # vocabulary before any routing decision is made. ---
        corrected_text, was_corrected = correct_transcript(user_text, self.model)

        if not _is_data_query(corrected_text):
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": corrected_text + " (Answer directly, no tools or APIs.)"}
                ],
            )
            metadata = _empty_metadata()
            metadata["raw_transcript"] = user_text
            metadata["corrected_transcript"] = corrected_text
            metadata["transcript_was_corrected"] = was_corrected
            return {
                "answer": response["message"]["content"],
                "metadata": metadata
            }

        response = ollama.chat(
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
            answer, metadata = self._execute_tool_calls(tool_calls)
            metadata["raw_transcript"] = user_text
            metadata["corrected_transcript"] = corrected_text
            metadata["transcript_was_corrected"] = was_corrected
            return {"answer": answer, "metadata": metadata}

        content = message.get("content", "")
        extracted_calls = _extract_json_from_text(content)
        if extracted_calls:
            synthetic_calls = [
                {"function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in extracted_calls
            ]
            answer, metadata = self._execute_tool_calls(synthetic_calls)
            metadata["raw_transcript"] = user_text
            metadata["corrected_transcript"] = corrected_text
            metadata["transcript_was_corrected"] = was_corrected
            return {"answer": answer, "metadata": metadata}

        metadata = _empty_metadata()
        metadata["raw_transcript"] = user_text
        metadata["corrected_transcript"] = corrected_text
        metadata["transcript_was_corrected"] = was_corrected
        return {
            "answer": content if content else "I didn't understand that query.",
            "metadata": metadata
        }

    # @staticmethod
    # def _format_answer(data, func_name) -> str:
    #     if not data:
    #         return "No data found."
    #     if func_name == "get_crm_data":
    #         return f"Found {len(data)} customers."
    #     if func_name == "get_support_tickets":
    #         return f"Found {len(data)} support tickets."
    #     if func_name == "get_analytics" and "value" in data[0]:
    #         avg = sum(d["value"] for d in data) / len(data)
    #         return f"Average value over the period is {avg:.0f}."
    #     return str(data)[:200]

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