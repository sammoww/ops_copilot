# ==============================================================================
# OpsCopilot — Production Dockerfile
# Multi-purpose image for both FastAPI Backend (8000) and Streamlit Frontend (8501)
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable immediate stdout flushing
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build-essential, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Layer-cached dependency installation
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code, UI, and incident runbooks
COPY src/ ./src/
COPY ui/ ./ui/
COPY data/ ./data/

# Expose FastAPI backend (8000) and Streamlit frontend (8501)
EXPOSE 8000 8501

# Default execution: Launch production FastAPI backend
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
