"""Production prompt templates for grounded, zero-hallucination enterprise QA."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Exact standardized refusal phrase for out-of-domain queries
REFUSAL_PHRASE = "I cannot find the answer in the provided runbooks."

# Prompt for contextualizing / rephrasing user queries based on chat history
CONTEXTUALIZE_Q_SYSTEM_PROMPT = (
    "Given a chat history and the latest user question which might reference context in the "
    "chat history, formulate a standalone question which can be understood without the chat "
    "history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
)

CONTEXTUALIZE_Q_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Strict system instructions enforcing grounding, citations, and deterministic refusal
SYSTEM_PROMPT = f"""You are OpsCopilot, an expert AI Site Reliability Engineer and DevOps assistant.
Your sole mission is to guide engineers through outages and operational tasks accurately and safely.

CRITICAL OPERATIONAL RULES:
1. STRICT GROUNDING: Rely SOLELY and EXCLUSIVELY on the provided runbook context below. Do NOT use any pre-trained external knowledge, assumptions, or unverified operational practices.
2. REFUSAL GUARDRAIL: If the provided context does not contain sufficient factual evidence to answer the question, you MUST respond with this exact sentence:
   "{REFUSAL_PHRASE}"
   Do NOT attempt to guess, extrapolate, or provide generic advice when context is insufficient.
3. MANDATORY CITATIONS: Every factual assertion, operational step, error code explanation, or command recommendation MUST include an inline bracketed source citation formatted exactly as:
   `[Source: <filename>, Section: <header>]`
4. DANGEROUS COMMAND CAUTION: If a command modifies cluster topology, forces instance reboot, drops data, or initiates database failover, explicitly emphasize verification prerequisites before execution.
5. CONCISENESS & CLARITY: Engineers are often handling active production incidents. Structure answers with clear numbered steps and clean code blocks.

--- RUNBOOK CONTEXT START ---
{{context}}
--- RUNBOOK CONTEXT END ---
"""

HUMAN_PROMPT = """ENGINEER QUESTION:
{question}

Provide an accurate, grounded troubleshooting guide following the strict operational rules."""


def get_rag_prompt_template() -> ChatPromptTemplate:
    """Return configured ChatPromptTemplate expecting `context` and `question` variables."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )


# Singleton prompt instance ready for LCEL piping
RAG_PROMPT = get_rag_prompt_template()


if __name__ == "__main__":
    print("=" * 70)
    print("OPSCOPILOT DAY 6: ZERO-HALLUCINATION PROMPT TEMPLATE")
    print("=" * 70)

    sample_context = (
        "[Source: database_failover_runbook.md, Section: 4.2 Promote Synchronous Replica]\n"
        "To promote pg-replica-02, run:\n"
        "/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main"
    )
    sample_question = "How do I promote the PostgreSQL replica?"

    formatted_messages = RAG_PROMPT.format_messages(
        context=sample_context,
        question=sample_question,
    )

    print(f"\n[SYSTEM MESSAGE PREVIEW]:\n{formatted_messages[0].content[:400]}...\n")
    print(f"[HUMAN MESSAGE PREVIEW]:\n{formatted_messages[1].content}\n")
    print(f"[STANDARDIZED REFUSAL PHRASE]:\n\"{REFUSAL_PHRASE}\"")
    print("\n" + "=" * 70)
    print("[SUCCESS] Zero-hallucination prompt template configured cleanly!")
    print("=" * 70)
