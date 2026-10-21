# OpsCopilot AI: 20-Day Daily Sprint & Knowledge Defense Masterplan

> **Philosophy:** Execute on your "C-Game." Do only the assigned step for the day (45–60 minutes max). Do not build ahead. Never merge or commit code you cannot defend in a live technical interview.

---

## 0. The Knowledge Assessor & Defense Coach ("The Lead Reviewer")

To ensure you can speak fluently to hiring managers and pass senior backend/AI engineer screens, every day concludes with an evaluation by this simulated persona.

### Agent Specification: What Qualities This Teacher Possesses

1. **Pragmatic & Anti-Fluff (Zero Academic Bullshit):**
   * Does not test you on raw calculus or matrix derivation.
   * Tests you on production reality: network latency, chunk boundaries, edge cases, failure states, cost per 1k tokens, and concurrency.
2. **Socratic Defense Drilling:**
   * Never asks: *"Did you finish the code?"*
   * Asks: *"Why did you use `RecursiveCharacterTextSplitter` instead of splitting on simple `\n\n`?"* or *"What happens if ChromaDB returns 0 matches for an ambiguous query?"*
3. **The "Sniff Test" Calibration:**
   * Calibrated against modern technical recruiter filters and hiring manager interviews.
   * Flags "resume traps"—code you pasted from an LLM without understanding the trade-offs.
4. **Binary Exit Gate:**
   * At the end of each day, you must answer the **3 Oral Defense Questions** out loud or in your engineering log before checking off the day's box.

---

## Week 1: Data Ingestion, Chunking & Vector Indexing

**Weekly Goal:** An offline Python CLI that ingests raw markdown/PDF files, splits them into semantic chunks, converts them into vector embeddings, and retrieves the top 3 matches for a test question.

```
project-root/
├── data/
│   └── runbooks/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── ingest.py
│   └── query.py
├── requirements.txt
└── .env
```

---

### Day 1: Isolated Environment & Dependency Setup
* **Time Required:** 30–45 mins.
* **Strict Boundary:** Do not touch vector databases or OpenAI APIs today. Only set up the runtime environment and verified config loading.

#### Tasks
1. Create your project folder:
   ```bash
   mkdir opscopilot && cd opscopilot
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Create `requirements.txt`:
   ```text
   fastapi>=0.111.0
   uvicorn[standard]>=0.30.0
   pydantic>=2.7.0
   pydantic-settings>=2.3.0
   python-dotenv>=1.0.1
   chromadb>=0.5.0
   langchain>=0.2.0
   langchain-community>=0.2.0
   langchain-openai>=0.1.7
   tiktoken>=0.7.0
   streamlit>=1.35.0
   httpx>=0.27.0
   ```
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` and `src/config.py` using `pydantic-settings` to safely validate environment variables (`OPENAI_API_KEY`, `CHROMA_PERSIST_DIR`).

#### AI Prompt for Boilerplate
```text
Write a production-grade src/config.py using Pydantic Settings (BaseSettings) for Python 3.11+. It should parse OPENAI_API_KEY (secret string) and CHROMA_PERSIST_DIR (defaulting to "./chroma_db"). Include a small verification block under if __name__ == "__main__": to ensure variables load correctly from .env.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** Why do we use `pydantic-settings` instead of calling `os.getenv("OPENAI_API_KEY")` directly in application logic?
* [x] **Q2:** What happens if `OPENAI_API_KEY` is missing at app startup? (Why is failing fast better than failing during a user request?)
* [x] **Q3:** What is the difference between your local virtualenv and a Docker container?

---

### Day 2: Curating the Ingestion Dataset
* **Time Required:** 30–45 mins.
* **Strict Boundary:** No coding today. Only source and structure 3–5 real-world documents into `data/runbooks/`.

#### Tasks
1. Create `data/runbooks/`.
2. Add 3 distinct technical incident runbooks or API specs (500–1500 words each). Examples:
   * `database_failover_runbook.md` (PostgreSQL failover steps, alert thresholds, commands).
   * `refund_policy_enterprise.md` (Rules for SLA credits, refund tiers, manager approvals).
   * `user_provisioning_sop.md` (SSO setup, SCIM tokens, permission escalation).
3. Ensure these documents contain specific numbers, error codes (e.g., `ERR_503_DB_TIMEOUT`), and procedural steps.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** Why are markdown (`.md`) files easier to parse reliably in production RAG systems than multi-column PDFs?
* [x] **Q2:** If an internal company doc has tables, how do standard text splitters typically corrupt that data?
* [x] **Q3:** What is document "metadata" (e.g., filename, author, updated_at), and why will recruiters look for it in your retrieval layer?

---

### Day 3: Chunking Engine with Token Control
* **Time Required:** 45 mins.
* **Strict Boundary:** Do not generate embeddings yet. Only read files and split them into chunks on disk.

#### Tasks
1. Create `src/ingest.py`.
2. Implement text splitting using LangChain’s `RecursiveCharacterTextSplitter`.
3. Set `chunk_size=800` characters/tokens and `chunk_overlap=120`.
4. Add file-level metadata extraction (filename, section headers if available).
5. Print out the total number of chunks created and inspect 2 sample chunks in the terminal.

#### AI Prompt for Boilerplate
```text
Write a Python script src/ingest.py that reads all .md files in data/runbooks/ using LangChain DirectoryLoader or UnstructuredMarkdownLoader. Split them using RecursiveCharacterTextSplitter with chunk_size=800 and chunk_overlap=120. Iterate over the chunks and print: 1) Total chunk count, 2) First chunk content, 3) First chunk metadata.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** Why do we need `chunk_overlap`? What happens to a sentence that gets cut exactly in half at the chunk boundary without overlap?
* [x] **Q2:** Why `RecursiveCharacterTextSplitter` instead of a simple character-count slice? (What separators does it try first?)
* [x] **Q3:** If you set chunk size to 5,000 tokens vs 200 tokens, how does that affect retrieval precision vs context richness?

---

### Day 4: Vector Embeddings & Local ChromaDB Storage
* **Time Required:** 45–60 mins.
* **Strict Boundary:** Do not build search queries yet. Focus entirely on embedding generation and database persistence.

#### Tasks
1. In `src/ingest.py`, initialize `OpenAIEmbeddings(model="text-embedding-3-small")`.
2. Initialize Chroma vector store with persistent storage directory (`./chroma_db`).
3. Ingest documents into Chroma: `Chroma.from_documents(...)`.
4. Run the script. Verify that the `./chroma_db` directory is populated with SQLite/parquet files.

#### AI Prompt for Boilerplate
```text
Extend src/ingest.py to take the generated chunks, embed them using OpenAIEmbeddings(model="text-embedding-3-small"), and save them into a persistent ChromaDB client pointing to settings.CHROMA_PERSIST_DIR. Include execution timing to measure how long embedding ingestion takes.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** What is an embedding in mathematical terms? (Dimensions, dense vector representation).
* [x] **Q2:** Why did we choose `text-embedding-3-small` over `text-embedding-ada-002` or self-hosted HuggingFace models? (Trade-offs: cost, dimensionality, latency).
* [x] **Q3:** What does "persisting" a vector database mean, and why should this step happen offline rather than on every user query?

---

### Day 5: Semantic Search CLI & Retrieval Validation
* **Time Required:** 45 mins.
* **Strict Boundary:** No LLM generation or chat logic yet. Pure similarity search retrieval.

#### Tasks
1. Create `src/query.py`.
2. Connect to the existing `./chroma_db` store in read-only mode.
3. Write a function `search(query: str, k: int = 3)` using `similarity_search_with_relevance_scores`.
4. Test with: `"How do I handle a database timeout error?"`
5. Print: Distance score, Source file name, and Chunk preview.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** What distance metric does ChromaDB use by default (Cosine similarity vs L2 Euclidean distance)?
* [x] **Q2:** If a user searches for gibberish like *"xyz123abc"*, does semantic search still return documents? Why?
* [x] **Q3:** What is a "relevance threshold" filter, and why is it needed to stop irrelevant documents from entering the prompt?

---

## Week 2: Grounded RAG Pipeline & Hallucination Guardrails

**Weekly Goal:** An agent engine that takes a question, retrieves context, formats a strict system prompt, and answers using citations while refusing to answer ungrounded questions.

---

### Day 6: Prompt Engineering for Zero Hallucination
* **Time Required:** 45 mins.
* **Strict Boundary:** Focus purely on prompt templates and constraints.

#### Tasks
1. Create `src/prompts.py`.
2. Write a production system prompt using LangChain's `ChatPromptTemplate`.
3. Rules to embed in the prompt:
   * Rely solely on the provided context.
   * If the answer cannot be deduced from context, output: `"I cannot find the answer in the provided runbooks."`
   * Every factual statement must cite `[Source: <filename>, Section: <header>]`.

#### AI Prompt for Boilerplate
```text
Create a Python file src/prompts.py containing a LangChain ChatPromptTemplate designed for zero-hallucination enterprise QA. It should take two variables: `context` and `question`. Add strict instructions forbidding outside knowledge and enforcing explicit bracketed source citations.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** Why do LLMs hallucinate even when instructed not to?
* [x] **Q2:** How does few-shot prompting or negative constraints (what *not* to do) help keep the model grounded?
* [x] **Q3:** If an internal runbook contains outdated information, who is responsible: the prompt, the model, or the ingestion pipeline?

---

### Day 7: Building the End-to-End RAG Chain
* **Time Required:** 45 mins.
* **Strict Boundary:** Keep it in a single script/function. Don't add API layers yet.

#### Tasks
1. Create `src/rag_chain.py`.
2. Use LangChain Expression Language (LCEL) or standard piping:
   `retriever | format_docs | prompt | llm | StrOutputParser()`.
3. Use `ChatOpenAI(model="gpt-4o-mini", temperature=0.0)`.
4. Run a test in terminal: Ask a question and print the full grounded response.

#### AI Prompt for Boilerplate
```text
Write src/rag_chain.py using modern LCEL syntax. Initialize ChatOpenAI(model="gpt-4o-mini", temperature=0.0). Wire together Chroma retriever (k=3), the prompt from src/prompts.py, and StrOutputParser. Return both the final answer text and the source documents used for citation verification.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [x] **Q1:** Why is `temperature=0.0` critical for enterprise runbook QA?
* [x] **Q2:** Explain the LCEL pipeline syntax (`|`) and how data flows from input dict to output string.
* [x] **Q3:** Why use `gpt-4o-mini` instead of the full `gpt-4o` for this use case? (Latency vs cost vs reasoning capability).

---

### Day 8: Automated Hallucination & Citation Verification
* **Time Required:** 45 mins.
* **Strict Boundary:** No code architecture changes. Only test suite creation.

#### Tasks
1. Create `tests/test_grounding.py`.
2. Define a list of 5 test test-cases:
   * 2 Direct factual queries (ground truth known).
   * 1 Multi-chunk query (requires combining 2 sections).
   * 2 Out-of-domain queries (e.g., *"What is our corporate 401k policy?"* when you only ingested DB runbooks).
3. Run tests and assert that out-of-domain queries return the exact refusal string.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** What is an automated RAG evaluation framework (e.g., Ragas, TruLens)? (Explain the concept of Groundedness/Faithfulness).
* [ ] **Q2:** How would you test this pipeline in a CI/CD GitHub Actions workflow without running up expensive API bills?
* [ ] **Q3:** What constitutes a false negative in retrieval?

---

### Day 9: Chat Memory / Conversation Buffer
* **Time Required:** 45 mins.
* **Strict Boundary:** Do not over-engineer database memory. Use a simple in-memory session history first.

#### Tasks
1. Update `src/rag_chain.py` to support multi-turn conversation.
2. Implement contextual query reformulation (e.g., if user asks: *"How do I reboot it?"* after asking about PostgreSQL, the retriever rephrases the query to: *"How do I reboot PostgreSQL?"*).
3. Use LangChain's `create_history_aware_retriever`.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why does standard vector search fail if the user asks: *"What was the second step again?"*
* [ ] **Q2:** How does a "condense question prompt" or "history-aware retriever" solve this pronoun/reference issue?
* [ ] **Q3:** What is the token/latency cost of passing full chat history into every single retrieval step?

---

### Day 10: Encapsulating the Core Service
* **Time Required:** 45 mins.
* **Strict Boundary:** Code refactoring and cleanliness only.

#### Tasks
1. Refactor logic into a clean class `OpsCopilotService` in `src/service.py`.
2. Methods required:
   * `query(question: str, history: list) -> dict`
   * `health_check() -> bool`
3. Ensure no global state variables are leaking across calls.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why must database connections or LLM client instances be reused instead of re-instantiated on every function call?
* [ ] **Q2:** What is dependency injection and how will it help when we wrap this service in FastAPI next week?
* [ ] **Q3:** Walk through `src/service.py` line-by-line out loud in under 2 minutes.

---

## Week 3: Function/Tool Calling & Asynchronous FastAPI

**Weekly Goal:** Expose the assistant via a production FastAPI REST API supporting both RAG document lookup, tool execution (mock DB query), and Server-Sent Events (SSE) streaming.

```
src/
├── api/
│   ├── routes.py
│   └── schemas.py
├── tools/
│   └── incident_tools.py
├── main.py
```

---

### Day 11: Defining External Action Tools
* **Time Required:** 45 mins.
* **Strict Boundary:** Do not connect to FastAPI yet. Just test tools in Python.

#### Tasks
1. Create `src/tools/incident_tools.py`.
2. Create 2 mock enterprise backend tools using LangChain's `@tool` decorator or Pydantic:
   * `get_service_status(service_name: str) -> dict`: Returns mock latency, health (`HEALTHY`, `DEGRADED`, `DOWN`).
   * `create_incident_ticket(title: str, severity: str) -> dict`: Returns a mock ticket ID (e.g., `INC-8921`).
3. Bind tools to the ChatOpenAI model using `.bind_tools()`.

#### AI Prompt for Boilerplate
```text
Write src/tools/incident_tools.py using LangChain's @tool decorator and Pydantic schemas. Define get_service_status(service_name: str) and create_incident_ticket(title: str, severity: str). Write a small test demonstrating how ChatOpenAI(model="gpt-4o-mini").bind_tools([get_service_status, create_incident_ticket]) correctly detects the function call when prompted: "The payments database is down, file an urgent incident."
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Does the LLM execute the Python code of your tool directly on OpenAI's servers? (Explain the tool-calling handshake).
* [ ] **Q2:** How does the model know what arguments to pass to your function? (Role of JSON Schema and docstrings).
* [ ] **Q3:** What security vulnerabilities exist with LLM tool calling (e.g., SQL injection, arbitrary code execution), and how do you protect against them?

---

### Day 12: Tool Routing & Execution Loop
* **Time Required:** 45 mins.
* **Strict Boundary:** Run via command line test.

#### Tasks
1. Implement the execution loop in `src/agent.py`:
   * User query comes in.
   * Model decides whether to call a tool, query ChromaDB RAG, or reply directly.
   * If a tool is called, execute the tool locally, feed the result back to the model, and get the final answer.
2. Test query: *"What is the status of the auth-service?"* $\rightarrow$ Model calls `get_service_status(service_name='auth-service')` $\rightarrow$ Model formats the answer.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** What is the difference between ReAct agent prompting and native OpenAI Tool Calling?
* [ ] **Q2:** What happens if the tool raises an unhandled Python exception (e.g., `KeyError` or timeout)? How should the LLM handle that error message?
* [ ] **Q3:** How do you prevent an agent from getting trapped in an infinite tool-calling loop?

---

### Day 13: FastAPI Skeleton & Strict Request/Response Schemas
* **Time Required:** 45 mins.
* **Strict Boundary:** Standard synchronous or async JSON endpoint. No streaming yet.

#### Tasks
1. Create `src/api/schemas.py`:
   * `ChatRequest`: `message: str`, `conversation_id: Optional[str]`.
   * `ChatResponse`: `answer: str`, `sources: List[str]`, `tools_called: List[str]`.
2. Create `src/main.py` with FastAPI, CORS middleware, and a health endpoint `GET /health`.
3. Add `POST /api/v1/chat` returning the structured `ChatResponse`.
4. Test using the automatic Swagger UI at `http://localhost:8000/docs`.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why do we use Pydantic models for request validation in FastAPI instead of raw JSON dictionaries?
* [ ] **Q2:** What does FastAPI's `/docs` (OpenAPI/Swagger) give frontend developers without you writing extra documentation?
* [ ] **Q3:** Why is CORS middleware necessary if a React/Streamlit app talks to your FastAPI backend on different ports?

---

### Day 14: Token Streaming with Server-Sent Events (SSE)
* **Time Required:** 45–60 mins.
* **Strict Boundary:** Focus strictly on asynchronous streaming.

#### Tasks
1. Add endpoint `POST /api/v1/chat/stream` in `src/main.py`.
2. Use FastAPI's `StreamingResponse(media_type="text/event-stream")`.
3. Use the LLM's `.astream()` method to yield tokens one by one as they arrive from OpenAI.
4. Test via cURL in your terminal to see tokens printing progressively:
   ```bash
   curl -N -X POST http://localhost:8000/api/v1/chat/stream \
     -H "Content-Type: application/json" \
     -d '{"message": "How do I reboot the database?"}'
   ```

#### AI Prompt for Boilerplate
```text
Write a FastAPI endpoint POST /api/v1/chat/stream that accepts ChatRequest and returns a StreamingResponse using text/event-stream. Inside an async generator function, iterate over agent.astream(request.message) and yield SSE-compliant data chunks formatted as `data: {"token": "..."}\n\n`.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** What is the difference between WebSockets and Server-Sent Events (SSE)? Why is SSE ideal for LLM token streaming?
* [ ] **Q2:** Why does waiting for the complete response (5–10 seconds) feel broken to users compared to streaming the first token in 400ms (Time to First Token - TTFT)?
* [ ] **Q3:** Why must the streaming generator be an `async def` function in FastAPI when handling concurrent users?

---

### Day 15: Error Handling & Rate Limiting Guardrails
* **Time Required:** 45 mins.
* **Strict Boundary:** Production hardening.

#### Tasks
1. Add global exception handlers in FastAPI for:
   * OpenAI API timeouts / `RateLimitError`.
   * Invalid user payloads.
2. Return standard HTTP 429 or 503 error payloads with clear client-facing messages.
3. Test by simulating a missing API key or invalid payload.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** How does an exponential backoff retry policy work when calling upstream LLM APIs?
* [ ] **Q2:** What is the risk of exposing raw Python stack traces (`Traceback (most recent call last)`) to API clients?
* [ ] **Q3:** What HTTP status code should be returned when the upstream LLM hits rate limits?

---

## Week 4: Streamlit UI, Containerization & Job-Ready Artifacts

**Weekly Goal:** Package the entire system into a Docker container, connect a clean Streamlit chat UI, publish a public GitHub repository with an architecture diagram, and write resume bullet points.

---

### Day 16: Streamlit Chat Interface
* **Time Required:** 45 mins.
* **Strict Boundary:** Keep UI under 60 lines. Do not spend time styling CSS.

#### Tasks
1. Create `ui/app.py`.
2. Use `st.chat_input` and `st.chat_message`.
3. Use `httpx.stream` or `requests` to consume the FastAPI `/api/v1/chat/stream` SSE endpoint.
4. Use `st.write_stream` to display the typewriter effect in the browser.
5. Run: `streamlit run ui/app.py`.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why is it better architecture to keep Streamlit completely decoupled from the AI logic (calling FastAPI via HTTP) rather than importing `rag_chain.py` directly into Streamlit?
* [ ] **Q2:** How does Streamlit's execution model work (how does the whole script rerun on user interaction)?
* [ ] **Q3:** How do session states (`st.session_state`) preserve chat history across reruns?

---

### Day 17: Multi-Stage Dockerfile & Docker Compose
* **Time Required:** 45 mins.
* **Strict Boundary:** Containerization only.

#### Tasks
1. Write a clean `Dockerfile`:
   * Base image: `python:3.11-slim`.
   * Set `PYTHONUNBUFFERED=1`.
   * Install requirements, copy code, expose port 8000.
2. Write `docker-compose.yml` to spin up both the FastAPI backend and Streamlit UI with a single command.
3. Test locally: `docker compose up --build`.

#### AI Prompt for Boilerplate
```text
Write a production-grade Dockerfile using python:3.11-slim with non-root user permissions and cache-efficient dependency installation. Next, write a docker-compose.yml file that launches both the FastAPI backend service (port 8000) and the Streamlit frontend service (port 8501) on a shared bridge network.
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why do we copy `requirements.txt` and run `pip install` BEFORE copying the rest of the application code in a Dockerfile? (Docker layer caching).
* [ ] **Q2:** Why should you avoid running containers as the `root` user in enterprise production?
* [ ] **Q3:** What is the purpose of `.dockerignore`? (Name 3 things that should be in it).

---

### Day 18: Architecture Diagram & README Construction
* **Time Required:** 45 mins.
* **Strict Boundary:** Documentation and presentation.

#### Tasks
1. Write `README.md` with the following structure:
   * **Project Title & 2-Sentence Pitch.**
   * **ASCII Architecture Flowchart** (User $\rightarrow$ Streamlit $\rightarrow$ FastAPI $\rightarrow$ LangChain Router $\rightarrow$ ChromaDB / Tool Engine $\rightarrow$ OpenAI).
   * **Key Production Features** (Grounding, Streaming, Pydantic validation, Tool Calling).
   * **Local Quickstart** (3 commands: clone, copy `.env`, `docker compose up`).
   * **Example cURL request & response**.

#### ASCII Diagram for README
```text
+----------------+      HTTP/SSE       +-------------------+
|  Streamlit UI  | <=================> |  FastAPI Backend  |
+----------------+                     +-------------------+
                                                 |
                                     [ LangChain Agent Router ]
                                        /                 \
                                       v                   v
                        +----------------------+    +----------------------+
                        | ChromaDB Vector Store|    | Tool Calling Engine  |
                        | (Grounded Runbooks)  |    | (Mock Status & JIRA) |
                        +----------------------+    +----------------------+
                                       \                   /
                                        v                 v
                                      +---------------------+
                                      | OpenAI (gpt-4o-mini)|
                                      +---------------------+
```

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** If a technical recruiter spends 45 seconds reviewing your GitHub repository, what 3 things must they see immediately?
* [ ] **Q2:** Why does having an architecture diagram elevate a repository from a "student/tutorial project" to an "engineer's project"?
* [ ] **Q3:** How do you ensure no API keys or secrets were accidentally committed to git history? (`git log -S`, `.gitignore`).

---

### Day 19: Screen Demo & Git Polish
* **Time Required:** 45 mins.
* **Strict Boundary:** Visual proof of work.

#### Tasks
1. Record a 60–90 second clean video (using Loom or native screen recorder):
   * *0:00–0:20:* Query a specific runbook detail $\rightarrow$ show response streaming with source citation.
   * *0:20–0:45:* Query something not in the docs $\rightarrow$ show the refusal guardrail preventing hallucination.
   * *0:45–1:15:* Trigger an action: *"Database latency is spiking, check status and create ticket"* $\rightarrow$ show tool call execution.
2. Convert video to a GIF or link the Loom directly at the top of your `README.md`.
3. Push to GitHub with a clean commit history.

#### End-of-Day Knowledge Defense (Assessor Checkpoint)
* [ ] **Q1:** Why do hiring managers prefer a 60-second video demo over cloning and running your code locally?
* [ ] **Q2:** Can you explain the 3 distinct actions demonstrated in your video without looking at notes?

---

### Day 20: Resume & Interview Defense Final Calibration
* **Time Required:** 45 mins.
* **Strict Boundary:** Career conversion.

#### 1. The Resume Bullet Points (Copy into your CV)
> **OpsCopilot AI — Production RAG & Automated Action Agent**
> * Engineered an asynchronous enterprise knowledge agent using **Python 3.11, FastAPI, LangChain, and ChromaDB**, indexing internal operations runbooks for contextual Q&A.
> * Implemented strict contextual grounding and citation constraints with `gpt-4o-mini`, eliminating hallucinations and reducing ungrounded responses to 0% across baseline test suites.
> * Integrated OpenAI Tool Calling to dynamically trigger backend mock operations (incident ticketing, service health telemetry) directly from natural language requests.
> * Decreased Time to First Token (TTFT) to `<450ms` by implementing Server-Sent Events (SSE) streaming through FastAPI to a decoupled **Streamlit** user interface.
> * Containerized multi-service deployment via **Docker & Docker Compose**, ensuring environment parity and single-command local orchestration.

#### 2. The Comprehensive Interview Defense Exam
Before submitting job applications, answer these 5 comprehensive questions out loud:

1. *"Why did you use RAG instead of fine-tuning a model on the company's runbooks?"*
   * **Target Answer:** Fine-tuning teaches style, vocabulary, or task form; it does not reliably teach facts or dynamic knowledge. Updating documents in RAG takes seconds (re-indexing a vector database), whereas fine-tuning requires expensive re-training and still hallucinates. RAG also provides exact source citations for verification.
2. *"How does your chunking strategy balance retrieval speed vs answer quality?"*
   * **Target Answer:** Used an 800-token chunk with 120-token overlap. Small chunks (e.g., 100 tokens) lack sufficient semantic context for the LLM to understand relationships. Large chunks (e.g., 3000 tokens) pollute the context window with noise, diluting the embedding similarity score and increasing API inference costs.
3. *"What happens if two documents contain conflicting information?"*
   * **Target Answer:** ChromaDB returns both chunks if both are semantically similar to the query. In the system prompt, I instruct the model to highlight discrepancies and cite both sources with their respective document timestamps/versions rather than arbitrarily picking one.
4. *"How did you handle token streaming through FastAPI?"*
   * **Target Answer:** Used FastAPI's `StreamingResponse` with `media_type="text/event-stream"` and consumed the LangChain/OpenAI async generator via `.astream()`. This yields tokens asynchronously over an open HTTP connection, keeping memory footprint minimal and drastically cutting TTFT for the client.
5. *"If this service had to scale to 10,000 concurrent internal engineers, what breaks first?"*
   * **Target Answer:** In-memory ChromaDB and single-instance rate limits. In production, I would migrate ChromaDB to an external cluster (like Pinecone, Qdrant, or pgvector on RDS), put the FastAPI backend behind an ALB with autoscaled worker pods, and introduce Redis caching for frequent queries to avoid hitting OpenAI API rate limits.

---

## Daily Accountability Checklist

| Day | Focus Area | Status | Defense Score (1-5) |
|---|---|---|---|
| Day 1 | Environment, Virtualenv & Pydantic Config | [ ] | |
| Day 2 | Curating 3-5 Technical Runbooks | [ ] | |
| Day 3 | Token Chunking with Overlap | [ ] | |
| Day 4 | Embeddings & ChromaDB Persistence | [ ] | |
| Day 5 | Read-Only Semantic Search CLI | [ ] | |
| Day 6 | Strict Anti-Hallucination Prompting | [ ] | |
| Day 7 | LangChain LCEL RAG Pipeline | [ ] | |
| Day 8 | Automated Grounding & Refusal Tests | [ ] | |
| Day 9 | Multi-Turn Memory & Query Rewriting | [ ] | |
| Day 10 | Encapsulated Service Class | [ ] | |
| Day 11 | Tool Definitions with Pydantic | [ ] | |
| Day 12 | Tool Execution & Routing Loop | [ ] | |
| Day 13 | FastAPI App & Pydantic Schemas | [ ] | |
| Day 14 | SSE Token Streaming Endpoint | [ ] | |
| Day 15 | Error Handlers & Upstream Retries | [ ] | |
| Day 16 | Streamlit Streaming Chat UI | [ ] | |
| Day 17 | Dockerfile & Docker Compose | [ ] | |
| Day 18 | Architecture Flowchart & README | [ ] | |
| Day 19 | 60-Second Video Demo & Git Push | [ ] | |
| Day 20 | Resume Bullets & Final Oral Defense | [ ] | |