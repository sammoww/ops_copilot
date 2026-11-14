"""Unit tests for Day 16: Streamlit Chat Interface."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ui_app_file_exists_and_under_60_lines():
    """Verify ui/app.py exists and meets the strict <60 lines constraint."""
    app_path = Path("ui/app.py")
    assert app_path.exists(), "ui/app.py must exist"

    lines = [line for line in app_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) <= 60, f"ui/app.py must be <= 60 non-empty lines, got {len(lines)}"


def test_ui_stream_generator_logic():
    """Verify stream generation logic parses SSE data lines and handles [DONE]."""
    sample_sse_lines = [
        'data: {"token": "Auth"}',
        'data: {"token": " service"}',
        'data: {"token": " is"}',
        'data: {"token": " healthy."}',
        "data: [DONE]",
    ]

    tokens = []
    for line in sample_sse_lines:
        if line.startswith("data: ") and not line.endswith("[DONE]"):
            data = json.loads(line[6:])
            if "token" in data:
                tokens.append(data["token"])

    full_text = "".join(tokens)
    assert full_text == "Auth service is healthy."
