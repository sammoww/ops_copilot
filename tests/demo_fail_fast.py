"""Demonstration: Late Runtime Failure (os.getenv) vs. Fail-Fast (Pydantic).

Run directly:
    python tests/demo_fail_fast.py
Or run with pytest:
    pytest tests/demo_fail_fast.py -v
"""

import os
import pytest
from pydantic import BaseModel, Field, ValidationError


# ============================================================================
# Scenario A: The os.getenv Anti-Pattern (Late Runtime Failure)
# ============================================================================
def bad_os_getenv_boot():
    """Simulates app startup with os.getenv. Returns silently even if key is missing!"""
    key = os.getenv("REQUIRED_API_KEY_NEVER_SET")
    # Notice: No error raised! Key is silently None.
    return key


def user_request_handler(api_key: str | None):
    """Simulates a user request arriving 5 hours after startup."""
    if api_key is None:
        raise AttributeError(
            "Crash in production: 'NoneType' has no attribute 'strip'. "
            "Downstream OpenAI client failed because API key is None!"
        )
    return f"Authenticated request using {api_key[:4]}..."


# ============================================================================
# Scenario B: The Pydantic Pattern (Immediate Fail-Fast at Boot)
# ============================================================================
class FailFastConfig(BaseModel):
    """Simulates Pydantic Settings boot-time validation."""

    api_key: str = Field(
        ...,
        min_length=10,
        description="Required API key that cannot be empty or None",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout must be a positive integer",
    )


# ============================================================================
# Pytest Automated Test Suite
# ============================================================================
def test_os_getenv_fails_late_during_request():
    """Verify os.getenv boots cleanly but crashes during user requests."""
    # 1. Boot phase: silently succeeds with None
    key = bad_os_getenv_boot()
    assert key is None

    # 2. Runtime phase: blows up when user invokes business logic
    with pytest.raises(AttributeError) as exc_info:
        user_request_handler(key)

    assert "Crash in production" in str(exc_info.value)


def test_pydantic_fails_fast_at_boot():
    """Verify Pydantic prevents the app from even initializing when invalid."""
    with pytest.raises(ValidationError) as exc_info:
        # Boot phase: missing required 'api_key'
        FailFastConfig()

    errors = exc_info.value.errors()
    # Pydantic clearly identifies the exact missing field
    assert any(err["loc"] == ("api_key",) for err in errors)
    assert any(err["type"] == "missing" for err in errors)


# ============================================================================
# Direct Visual Console Demo
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("DEMO: FAIL-FAST (Pydantic) VS. LATE RUNTIME FAILURE (os.getenv)")
    print("=" * 70)

    # 1. Run Scenario A
    print("\n[SCENARIO A: os.getenv]")
    print("1. App Booting...")
    key = bad_os_getenv_boot()
    print(f"   -> Result of os.getenv: {key!r} (SILENT SUCCESS! App appears healthy)")
    print("2. 5 Hours Later: Real customer hits /query...")
    try:
        user_request_handler(key)
    except AttributeError as err:
        print(f"   -> [500 INTERNAL SERVER ERROR]: {err}")

    # 2. Run Scenario B
    print("\n" + "-" * 70)
    print("[SCENARIO B: Pydantic Fail-Fast]")
    print("1. App Booting...")
    try:
        FailFastConfig()
    except ValidationError as err:
        print("   -> [APP HALTED AT STARTUP] Pydantic raised ValidationError:")
        for e in err.errors():
            print(f"      * Field '{e['loc'][0]}': {e['msg']}")
        print("   -> Container crashes readiness probe. Zero users affected!")

    print("\n" + "=" * 70)
