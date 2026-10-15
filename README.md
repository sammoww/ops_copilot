# OpsCopilot AI

OpsCopilot is a production-grade enterprise Retrieval-Augmented Generation (RAG) assistant designed for DevOps and Site Reliability Engineering (SRE) teams to navigate technical incident runbooks and troubleshoot outages under pressure.

## Features
- **Deterministic & Grounded**: Built with zero-hallucination guardrails and strict bracketed citations.
- **Fail-Fast Configuration**: Strongly typed runtime environment validation using Pydantic Settings.
- **Production Pipeline**: Semantic chunking, persistent Chroma vector store, LCEL chain execution, tool calling, and FastAPI endpoints.

## Quickstart (Day 1)

### 1. Prerequisites
- Python 3.11 or Python 3.12
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd OpsCopilot

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Inside `.env`:
```env
OPENAI_API_KEY=your_actual_openai_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
```

### 4. Validate Configuration
Run the configuration verification script:
```bash
python -m src.config
```

Expected output:
```text
--- OpsCopilot Configuration Validation ---
[SUCCESS] Environment loaded successfully:
 - OPENAI_API_KEY:    sk-test...ment (SecretStr masked)
 - CHROMA_PERSIST_DIR: ./chroma_db
 - ENV FILE PATH:     ...
```

## Project Roadmap
See [opscopilot_daily_masterplan.md](opscopilot_daily_masterplan.md) for the 20-day sprint schedule and knowledge defense checkpoints.
