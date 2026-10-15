"""Unit tests for configuration loading and validation."""

import os
import pytest
from pydantic import ValidationError, SecretStr
from src.config import Settings


def test_settings_loads_valid_env():
    """Verify Settings initializes cleanly with required values."""
    settings = Settings(
        OPENAI_API_KEY="sk-test-sample-key",
        CHROMA_PERSIST_DIR="./custom_chroma",
    )
    assert settings.openai_api_key.get_secret_value() == "sk-test-sample-key"
    assert settings.chroma_persist_dir == "./custom_chroma"


def test_settings_default_chroma_dir():
    """Verify default fallback for CHROMA_PERSIST_DIR."""
    settings = Settings(OPENAI_API_KEY="sk-test-sample-key")
    assert settings.chroma_persist_dir == "./chroma_db"


def test_settings_secret_masking():
    """Verify SecretStr prevents accidental key leakage in string representations."""
    settings = Settings(OPENAI_API_KEY="sk-super-secret-key-12345")
    # str(secret) and repr(secret) must mask the key
    assert "sk-super-secret-key-12345" not in str(settings.openai_api_key)
    assert "sk-super-secret-key-12345" not in repr(settings.openai_api_key)
    assert "**********" in str(settings.openai_api_key)
    # Only get_secret_value() reveals it explicitly
    assert settings.openai_api_key.get_secret_value() == "sk-super-secret-key-12345"


def test_settings_missing_api_key_raises_validation_error(monkeypatch):
    """Verify app fails fast if OPENAI_API_KEY is not set."""
    # Ensure env variable is not present
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Creating Settings without env or explicit param should fail fast
    # We pass _env_file=None to ignore any disk .env during this specific negative test
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    errors = exc_info.value.errors()
    assert any(
        err["loc"] == ("OPENAI_API_KEY",) or err["loc"] == ("openai_api_key",)
        for err in errors
    )
