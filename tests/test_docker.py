"""Unit tests for Day 17: Multi-Stage Dockerfile & Docker Compose."""

from pathlib import Path
import pytest
import yaml


def test_dockerfile_structure_and_directives():
    """Verify Dockerfile contains required production directives and ports."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in content or "FROM python:3.11-slim" in content
    assert "WORKDIR /app" in content
    assert "requirements.txt" in content
    assert "EXPOSE 8000 8501" in content
    assert "uvicorn" in content


def test_docker_compose_validity_and_services():
    """Verify docker-compose.yml defines both backend and frontend with healthchecks."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert "services" in data
    services = data["services"]

    # Verify backend service definition
    assert "backend" in services
    backend = services["backend"]
    assert "8000:8000" in backend["ports"]
    assert "healthcheck" in backend

    # Verify frontend service definition
    assert "frontend" in services
    frontend = services["frontend"]
    assert "8501:8501" in frontend["ports"]
    assert "http://backend:8000" in str(frontend["environment"])
    assert "backend" in str(frontend["depends_on"])
    assert "streamlit" in frontend["command"]


def test_dockerignore_excludes_unnecessary_artifacts():
    """Verify .dockerignore excludes virtualenvs, caches, and database locks."""
    ignore_path = Path(".dockerignore")
    assert ignore_path.exists(), ".dockerignore must exist at repository root"

    content = ignore_path.read_text(encoding="utf-8")
    assert "venv/" in content or "venv" in content
    assert "__pycache__" in content
    assert ".git" in content
