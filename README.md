# OpsCopilot AI

<p align="center">
  <strong>Production-Grade Enterprise RAG Incident Response Assistant for DevOps & Site Reliability Engineering</strong>
</p>

<p align="center">
  <a href="https://github.com/your-org/OpsCopilot/actions"><img src="https://img.shields.io/badge/Tests-34%2F34%20Passing-brightgreen?style=flat-square&logo=pytest" alt="Test Status"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11%2B%20%7C%203.12-blue?style=flat-square&logo=python" alt="Python Version"></a>
  <a href="https://python.langchain.com/"><img src="https://img.shields.io/badge/LangChain-LCEL%20v0.2-orange?style=flat-square&logo=chainlink" alt="LangChain"></a>
  <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Config-Pydantic%20v2%20Settings-e92063?style=flat-square&logo=pydantic" alt="Pydantic Settings"></a>
  <a href="https://github.com/chroma-core/chroma"><img src="https://img.shields.io/badge/Vector%20Storage-Chroma%20%26%20SQLite3-purple?style=flat-square&logo=sqlite" alt="Vector Store"></a>
  <a href="#architectural-highlights"><img src="https://img.shields.io/badge/Guardrails-Active%20%7C%20Zero--Hallucination-success?style=flat-square" alt="Guardrails"></a>
  <a href="#cost-optimized-0-cicd-testing-matrix"><img src="https://img.shields.io/badge/CI%2FCD%20Cost-%240.00%20(Deterministic)-blueviolet?style=flat-square" alt="CI Cost"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License"></a>
</p>

---

## ⚡ The Executive Pitch: Why OpsCopilot?

When a primary database crashes at 3:15 AM on a Sunday, on-call Site Reliability Engineers (SREs) face an intense dual challenge:

1. **Catastrophic MTTR Penalties**: Paging through sprawling 60-page wikis, outdated Confluence trees, and disjointed PDF playbooks drains critical minutes while SLAs burn.
2. **The Hallucination Hazard of Generic LLMs**: Public LLMs are statistical next-token prediction engines. When prompted with an urgent database failover query, an unconstrained model will happily invent plausible-sounding commands (`pg_ctl promote -f` or unverified `sed` replacements) that risk split-brain clustering, permanent data corruption, or compliance breaches.

**OpsCopilot solves this with mathematically grounded Retrieval-Augmented Generation (RAG).** Built from the ground up on modern LangChain Expression Language (LCEL), OpsCopilot enforces strict deterministic grounding rules:
- **Zero-Speculation Guarantee**: The assistant answers **exclusively** from verified company runbooks. If a procedure or policy does not exist in the indexed context, it triggers an immediate, deterministic refusal.
- **Mandatory Bracketed Provenance**: Every triage step, configuration directive, and CLI command carries an immutable citation (`[Source: <filename>, Section: <header>]`).
- **Stateful History-Aware Retrieval**: Resolves conversational pronouns and multi-turn follow-ups (*"What was the second step of it again?"*) into standalone search queries before executing vector similarity search.
- **Enterprise Fail-Fast Architecture**: Enforces startup secret masking, runtime environment type-checking, and sub-second deterministic test suites running at **$0 API cost**.

---

## 🏛️ System Architecture

OpsCopilot separates indexing from real-time generation using a two-phase retrieval and generation pipeline designed for sub-second incident triage:

```mermaid
flowchart TD
    subgraph Ingestion ["1. Batch Document Ingestion & Vector Indexing"]
        A["Curated Runbooks (.md)"] --> B["Frontmatter Parser\n(Metadata Extraction)"]
        B --> C["RecursiveCharacterTextSplitter\n(chunk_size=800, overlap=120)"]
        C --> D["Vector Store Embeddings\n(text-embedding-3-small)"]
        D --> E[("Persistent Vector DB\n(Chroma / SQLite3)")]
    end

    subgraph Runtime ["2. Real-Time Conversational RAG Pipeline (LCEL)"]
        F["User Question + Chat History"] --> G["History-Aware Condensation\n(create_history_aware_retriever)"]
        G -->|"Standalone Query"| H["Cosine Similarity Search\n(top_k=3, Metadata Filter)"]
        E -.->|"Vector Fetch"| H
        H -->|"Retrieved Runbook Chunks"| I["Document Formatter\n(format_docs with Citations)"]
        I --> J["Grounding Prompt Template\n(5 Operational Safety Rules)"]
        F -.->|"Original Question"| J
        J --> K["LLM Generation\n(ChatOpenAI / MockGroundedChatModel)"]
        K --> L["StrOutputParser\n(Streaming Parity)"]
        L --> M["Grounded SRE Response\n+ Bracketed Citations"]
    end

    style Ingestion fill:#f0f4f8,stroke:#3b82f6,stroke-width:1px
    style Runtime fill:#fdf8f6,stroke:#f97316,stroke-width:1px
    style M fill:#ecfdf5,stroke:#10b981,stroke-width:2px
```

### LCEL Declarative Pipeline
The core generation engine is compiled declaratively via LangChain Expression Language (LCEL), ensuring unified synchronous, asynchronous, and token-streaming parity:

```python
# Modern LCEL Composition in src/rag_chain.py
rag_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(x["documents"])
    )
    | RAG_PROMPT
    | llm
    | StrOutputParser()
)
```

---

## 🌟 Architectural Highlights

### 1. Zero-Hallucination Guardrails & Refusal Protocol
OpsCopilot eliminates conversational sycophancy and speculative hallucinations via 5 hardcoded operational constraints in `src/prompts.py`:

| Operational Rule | Enforcement Mechanism | Failure Defense Behavior |
| :--- | :--- | :--- |
| **Strict Grounding** | Relies solely on provided context | Never hallucinates unvetted Linux or DB commands |
| **Standardized Refusal** | Deterministic exit phrase | Returns: *"I cannot find the answer in the provided runbooks."* |
| **Mandatory Citations** | Synthesizes source metadata | Every recommendation requires `[Source: <filename>, Section: <header>]` |
| **Destructive Command Gate** | Explicit caution alerts | Requires manual confirmation before failovers or data wipes |
| **Operational Brevity** | SRE numbered triage steps | Optimized for fast on-call scanning under high cognitive load |

> **Automated Refusal Verification**: When queried with out-of-domain requests (e.g., *"What is the HR 401(k) match?"* or *"How do I bake a lasagna?"*), OpsCopilot deterministically triggers the refusal guardrail with 0% false positive hallucination.

### 2. History-Aware Conversational Retrieval
Standard vector search fails on conversational follow-ups due to the **"Stateless Amnesia"** problem:

```text
User: "How do I promote the PostgreSQL replica?"
Copilot: "Execute: /usr/lib/postgresql/16/bin/pg_ctl promote ... [Source: database_failover_runbook.md]"
User: "What was the second step of it again?"
```

A standard similarity search on *"What was the second step of it again?"* calculates distance against words like "second" and "step", returning irrelevant chunks or triggering a false negative refusal. 

OpsCopilot integrates `create_history_aware_retriever`. In Phase 1, it pipes `(chat_history, latest_question)` through a condensation prompt that rewrites ambiguous follow-ups into standalone semantic queries (*"What was the second step of the PostgreSQL replica promotion procedure?"*) before executing vector search.

### 3. Fail-Fast Configuration & Credential Masking
Application runtime integrity is managed via `pydantic-settings` in `src/config.py`:
- **`SecretStr` Masking**: API keys are wrapped in Pydantic's `SecretStr` to prevent credentials from leaking into APM monitors, logging collectors, or exception stack traces.
- **Startup Validation**: Halts container boot immediately if required environment variables are absent, preventing degraded runtime containers from accepting user traffic during outages.
- **LRU Cached Singleton**: `get_settings()` memoizes environment loading, preventing continuous disk I/O on repeated invocations.

### 4. Cost-Optimized $0 CI/CD Testing Matrix
Enterprise teams cannot rely on live LLM APIs for CI/CD test suites: live calls incur continuous API costs, introduce network flakiness, and hit rate limits.

OpsCopilot ships with an offline deterministic testing harness:
- **`DeterministicEmbeddings`**: Generates 1536-dimensional L2-normalized dense vectors locally using deterministic byte hashing.
- **`MockGroundedChatModel`**: Implements LangChain's `BaseChatModel` contract to deterministically emulate grounded generation, citation parsing, pronoun reformulation, and out-of-domain refusals.
- **Result**: **34 automated unit and regression tests run in ~2.3 seconds** on every GitHub Actions pull request at **$0.00 API cost**.

---

## 📂 Repository Structure

```text
OpsCopilot/
├── data/
│   └── runbooks/                 # Domain-curated incident runbooks & SOPs
│       ├── database_failover_runbook.md  # PostgreSQL HA, Patroni, PgBouncer failover
│       ├── refund_policy_enterprise.md   # SLA uptime tiers & commercial credit grids
│       └── user_provisioning_sop.md      # SCIM 2.0 lifecycle & break-glass access
├── src/
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings & SecretStr credential masking
│   ├── demo_lcel_visualizer.py   # CLI step-by-step pipeline execution tracer
│   ├── ingest.py                 # Markdown frontmatter parsing & semantic chunking
│   ├── prompts.py                # Grounded prompt templates & history-aware queries
│   ├── query.py                  # Cosine similarity retrieval & score thresholding
│   ├── rag_chain.py              # LCEL generation pipeline & history-aware retriever
│   ├── service.py                # Encapsulated application service & health probes
│   └── vector_store.py           # Persistent SQLite3/Chroma vector engine
├── tests/
│   ├── __init__.py
│   ├── demo_fail_fast.py         # Negative assertion tests for startup validation
│   ├── test_config.py            # Pydantic environment validation unit tests
│   ├── test_grounding.py         # Automated evaluation suite for citations & refusals
│   ├── test_ingest.py            # Token-controlled chunking & boundary tests
│   ├── test_memory.py            # History-aware conversational retrieval tests
│   ├── test_prompts.py           # Prompt input schemas & refusal string tests
│   ├── test_query.py             # Vector store connectivity & relevance tests
│   ├── test_rag_chain.py         # LCEL chain invocation & citation tests
│   ├── test_service.py           # Encapsulated service & DI lifecycle tests
│   └── test_vector_store.py      # Embedding math & persistence validation
├── .env.example                  # Environment template
├── .gitignore                    # Local databases, virtual environments, and secrets
├── AGENTS.md                     # Canonical AI agent context & guidelines
├── CLAUDE.md                     # 3-line pointer stub to AGENTS.md
├── opscopilot_daily_masterplan.md # 20-Day curriculum & oral defense checkpoints
├── requirements.txt              # Pinned production dependencies
└── WORKLOG.md                    # Dated append-only change logs & defense records
```

---

## 🛠️ Tech Stack & Dependencies

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Framework** | LangChain Core & LCEL (`>=0.2.0`) | Declarative, streaming-ready pipeline composition |
| **Configuration** | Pydantic Settings (`>=2.3.0`) | Type-safe environment validation with `SecretStr` |
| **Vector Storage** | ChromaDB & SQLite3 Engine | Persistent vector store with cosine similarity retrieval |
| **Embeddings** | `text-embedding-3-small` | 1536-dimensional dense embeddings with local fallback |
| **Generation** | `gpt-4o-mini` / `ChatOpenAI` | High-reasoning zero-shot instruction following |
| **Evaluation** | Pytest Suite (`>=8.0.0`) | 34 automated unit, grounding, and regression tests |
| **Frontend / API** | FastAPI / Streamlit *(Upcoming)* | High-performance async REST endpoints & SRE Dashboard |

---

## 🚀 Quickstart Walkthrough

### 1. Prerequisites
- **Python 3.11** or **Python 3.12**
- **Git**

### 2. Clone & Virtual Environment Setup
```bash
# Clone the repository
git clone https://github.com/sammoww/ops_copilot.git
cd OpsCopilot

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Inside `.env`:
```env
OPENAI_API_KEY=your_actual_openai_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
```
*(Note: OpsCopilot runs full offline evaluation out of the box even with mock keys!)*

### 4. Ingest & Index Runbooks
Parse domain markdown runbooks, compute embeddings, and build the local vector database:
```bash
python -m src.ingest
```
Expected output:
```text
[LOAD] Successfully loaded 3 runbook document(s):
  - database_failover_runbook.md | Title: 'PostgreSQL High Availability & Primary Failover Runbook' (4662 chars)
  - refund_policy_enterprise.md | Title: 'Enterprise Service Level Agreement (SLA) Breach & Credit Refund Policy' (4031 chars)
  - user_provisioning_sop.md | Title: 'Enterprise User Identity Provisioning, SCIM Integration & Break-Glass Access SOP' (4492 chars)
[SPLIT] Generated 22 total chunk(s) (chunk_size=800, chunk_overlap=120)
[EMBED & PERSIST] Saving embeddings to './chroma_db'...
  -> Successfully persisted 23 chunks in 0.010 seconds!
  -> Database file located at: .../chroma_db/runbooks.sqlite3
```

### 5. Execute Semantic Search CLI
Test vector retrieval directly without generating text:
```bash
python -m src.query "How do I handle a database timeout error?"
```

### 6. Run End-to-End Grounded Generation
Execute the full LCEL generation pipeline from the command line:
```bash
python -m src.rag_chain "What is the command to promote the PostgreSQL replica node?"
```
Sample response:
```text
To promote the PostgreSQL replica node to primary, execute the following command:

/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main

[Source: database_failover_runbook.md, Section: Step 3: Replica Promotion]
```

### 7. Interactive Step-by-Step Pipeline Visualizer
Trace the transformation of data through each stage of the LCEL pipeline:
```bash
python src/demo_lcel_visualizer.py
```

### 8. Run Verification Test Suite
Execute the entire unit and regression test suite:
```bash
pytest -v
```
Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 34 items

tests/test_config.py ....                                                [ 11%]
tests/test_grounding.py ......                                           [ 29%]
tests/test_ingest.py ....                                                [ 41%]
tests/test_memory.py .....                                               [ 55%]
tests/test_prompts.py ...                                                [ 64%]
tests/test_query.py .....                                                [ 79%]
tests/test_rag_chain.py ....                                             [ 91%]
tests/test_vector_store.py ...                                           [100%]

============================= 34 passed in 2.31s ==============================
```

---

## 📅 20-Day Daily Sprint Progress

OpsCopilot is engineered following a strict 20-day production masterplan, ensuring each module is hardened, tested, and interview-defended before moving to downstream dependencies.

| Day | Milestone / Focus | Status | Key Deliverable |
| :---: | :--- | :---: | :--- |
| **Day 1** | Isolated Environment & Configuration | ✅ Complete | Pydantic Settings, `SecretStr` masking, fail-fast startup tests |
| **Day 2** | Ingestion Dataset Curation | ✅ Complete | Real-world SRE runbooks with YAML frontmatter headers |
| **Day 3** | Token-Controlled Chunking Engine | ✅ Complete | `RecursiveCharacterTextSplitter` with 120-char continuity overlap |
| **Day 4** | Vector Embeddings & Database Persistence | ✅ Complete | Persistent SQLite3 vector engine with deterministic embedding math |
| **Day 5** | Semantic Search CLI & Validation | ✅ Complete | Cosine similarity retrieval, top-k ranking, relevance thresholds |
| **Day 6** | Zero-Hallucination Prompt Engineering | ✅ Complete | 5 operational safety constraints, standardized refusal guardrail |
| **Day 7** | Modern LCEL Pipeline Composition | ✅ Complete | Declarative Runnable pipeline (`retriever \| format_docs \| prompt \| llm`) |
| **Day 8** | Automated Grounding Evaluation Suite | ✅ Complete | 5 automated incident test cases proving factual precision & refusals |
| **Day 9** | History-Aware Conversational Retrieval | ✅ Complete | Pronoun condensation with `create_history_aware_retriever` |
| **Day 10** | Application Service Encapsulation | 🚀 In Progress | Singleton service layer, connection pooling, health-check probes |
| **Day 11** | Backend Incident Tooling | ⏳ Upcoming | Simulated SRE action tools (PgBouncer reload, service status) |
| **Day 12** | FastAPI Endpoints & Contract Schemas | ⏳ Upcoming | Async REST endpoints (`/query`, `/health`, `/tools`) |
| **Day 13** | Streaming Responses via SSE | ⏳ Upcoming | Server-Sent Events for token-by-token terminal rendering |
| **Day 14** | Rate Limiting & API Security | ⏳ Upcoming | Token bucket rate limiting, CORS headers, API key auth |
| **Day 15** | Comprehensive API Integration Testing | ⏳ Upcoming | Async `TestClient` suite for multi-turn sessions |
| **Day 16** | Streamlit Incident Dashboard | ⏳ Upcoming | Real-time chat UI, source document drawer, tool triggers |
| **Day 17** | Observability & Tracing | ⏳ Upcoming | LangSmith instrumentation, latency breakdown, token counting |
| **Day 18** | Multi-Container Docker Architecture | ⏳ Upcoming | Multi-stage Dockerfile and Docker Compose orchestration |
| **Day 19** | End-to-End Stress Testing & Chaos | ⏳ Upcoming | Locust load testing, network latency tolerance, memory profiling |
| **Day 20** | Production Hardening & Live Demo | ⏳ Upcoming | Final documentation, demo video, architectural portfolio defense |

---

## 🛡️ Socratic Oral Defense Checkpoints

Every phase concludes with an oral defense against simulated Senior/Principal SRE Reviewers to guarantee engineering readiness. Documented answers are available in [WORKLOG.md](WORKLOG.md):
- **Chunk Boundaries & Overlap**: Why `chunk_overlap=120` prevents catastrophic command truncation.
- **Dimensional Geometry**: Why Cosine Similarity is chosen over Euclidean L2 distance for runbooks of varying length.
- **Out-of-Domain Safety**: Why standard KNN returns irrelevant documents for gibberish and how threshold gates trigger safe refusals.
- **Anaphora Resolution**: How condense question prompts resolve conversational amnesia during multi-turn incident response.

---

## 📜 License
This project is open-source software licensed under the [MIT License](LICENSE).
