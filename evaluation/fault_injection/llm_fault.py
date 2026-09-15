"""
evaluation/fault_injection/llm_fault.py - Mock LLM client simulating LLM failure modes.

Simulates deterministic LLM failures for evaluation:
  - timeout: raises TimeoutError
  - exception: raises RuntimeError
  - malformed_json: outputs raw malformed text tool calls
  - invalid_args: returns tool calls with invalid enum/types
  - tool_mismatch: returns a tool that does not match user query intent
  - empty_response: returns empty message
"""
from typing import Any, Dict, List, Optional


class MockFaultyLLMClient:
    def __init__(self, failure_mode: str = "none"):
        self.failure_mode = failure_mode
        self.call_count = 0

    def chat(self, model: str, messages: List[Dict], tools: Optional[List] = None) -> Dict[str, Any]:
        self.call_count += 1

        if self.failure_mode == "timeout":
            raise TimeoutError("Ollama chat timed out after 30s")

        if self.failure_mode == "exception":
            raise RuntimeError("Ollama connection refused / model crashed")

        if self.failure_mode == "empty_response":
            return {"message": {"role": "assistant", "content": ""}}

        if self.failure_mode == "malformed_json":
            return {
                "message": {
                    "role": "assistant",
                    "content": '{"name": "get_crm_data", "arguments": {status: "unclosed',
                }
            }

        if self.failure_mode == "invalid_args":
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_crm_data",
                                "arguments": {"status": "unsupported_status_value", "limit": -5},
                            }
                        }
                    ],
                }
            }

        if self.failure_mode == "tool_mismatch":
            # Model called analytics when the user asked for CRM data
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_analytics",
                                "arguments": {"metric": "daily_active_users"},
                            }
                        }
                    ],
                }
            }

        # Default valid response
        return {
            "message": {
                "role": "assistant",
                "content": "This is a direct response from the assistant.",
            }
        }
