# OpsCopilot AI — Agent Context & Guidelines

## 1. Project Overview
OpsCopilot is a production-grade enterprise RAG (Retrieval-Augmented Generation) assistant for DevOps & SRE incident response, built following the 20-Day Daily Sprint outlined in `opscopilot_daily_masterplan.md`.

- **Primary Goal**: Ingest incident runbooks, retrieve relevant context with high semantic precision, generate grounded zero-hallucination troubleshooting steps with source citations, and expose actions via FastAPI and Streamlit.
- **Strict Boundary Rule**: Adhere strictly to the current day's assigned tasks. Do not build ahead or import downstream components prematurely.

## 2. Directory Layout
```
OpsCopilot/
├── data/
│   └── runbooks/           # Ingestion markdown/spec documents
├── src/
│   ├── __init__.py
│   ├── config.py           # Pydantic Settings configuration & validation
│   ├── ingest.py           # Document loading, chunking & vector indexing (Day 3-4)
│   ├── query.py            # Retrieval & similarity search (Day 5)
│   ├── prompts.py          # Grounded prompts (Day 6)
│   ├── rag_chain.py        # LCEL RAG pipeline & history (Day 7, 9)
│   ├── service.py          # Encapsulated application service (Day 10)
│   ├── api/                # FastAPI routes & schemas (Day 11-13)
│   └── tools/              # Mock backend incident tools (Day 11)
├── tests/                  # Automated verification & test suites
├── requirements.txt        # Pinned core dependencies
├── .env.example            # Environment template
├── .env                    # Local secrets (gitignored)
├── AGENTS.md               # Canonical AI agent context (this file)
├── CLAUDE.md               # 3-line pointer stub to AGENTS.md
├── README.md               # Human-facing project overview & quickstart
├── WORKLOG.md              # Dated append-only log of changes & defense records
└── opscopilot_daily_masterplan.md # Master 20-day curriculum
```

## 3. Engineering Conventions & Standards
1. **Configuration**: Use `src/config.py` with `pydantic-settings` (`BaseSettings`). Never call `os.getenv` directly in business logic.
2. **Secrets Handling**: Use `pydantic.SecretStr` for API keys to avoid leaking credentials in logs or error traces.
3. **Environment**: Python 3.11+ using the local `venv` (`venv\Scripts\python.exe` on Windows).
4. **Verification**: After completing any task, run manual or automated tests to confirm success, and log results in `WORKLOG.md`.
5. **Interview Defense**: At the conclusion of every day's sprint, record answers to the 3 Oral Defense questions in `WORKLOG.md`.
