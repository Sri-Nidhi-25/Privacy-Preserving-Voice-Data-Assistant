"""
tests/test_config.py - Tests for configuration loading and validation.
"""
import pytest
from app.config import Settings


def test_valid_config():
    s = Settings(
        APP_NAME="Test Assistant",
        OBFUSCATION_STRENGTH="medium",
        MAX_RESULTS=5,
        API_KEY="test-key-123",
    )
    assert s.OBFUSCATION_STRENGTH == "medium"
    assert s.MAX_RESULTS == 5
    assert s.API_KEY == "test-key-123"


def test_invalid_obfuscation_strength():
    with pytest.raises(ValueError, match="OBFUSCATION_STRENGTH must be one of"):
        Settings(OBFUSCATION_STRENGTH="extreme")


def test_invalid_max_results():
    with pytest.raises(ValueError, match="MAX_RESULTS must be > 0"):
        Settings(MAX_RESULTS=0)


def test_invalid_timeout():
    with pytest.raises(ValueError, match="LLM_TIMEOUT_SECONDS must be > 0"):
        Settings(LLM_TIMEOUT_SECONDS=-1.0)


def test_api_key_dev_warning_mode():
    s = Settings(API_KEY="")
    # Should fall back to dev key with a warning
    assert s.API_KEY == "dev-insecure-key"


def test_string_sanitization():
    s = Settings(
        OLLAMA_MODEL="  llama3.2:latest   ",
        STT_MODEL=" small.en ",
        OBFUSCATION_STRENGTH=" MILD ",
    )
    assert s.OLLAMA_MODEL == "llama3.2:latest"
    assert s.STT_MODEL == "small.en"
    assert s.OBFUSCATION_STRENGTH == "mild"


def test_high_obfuscation_strength_alias():
    s = Settings(OBFUSCATION_STRENGTH="high")
    assert s.OBFUSCATION_STRENGTH == "strong"


def test_very_strong_obfuscation_strength():
    s1 = Settings(OBFUSCATION_STRENGTH="very_strong")
    assert s1.OBFUSCATION_STRENGTH == "very_strong"

    s2 = Settings(OBFUSCATION_STRENGTH="verystrong")
    assert s2.OBFUSCATION_STRENGTH == "very_strong"

    s3 = Settings(OBFUSCATION_STRENGTH="very strong")
    assert s3.OBFUSCATION_STRENGTH == "very_strong"
