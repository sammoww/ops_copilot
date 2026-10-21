"""End-to-end grounded RAG chain using modern LCEL syntax."""

import argparse
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from src.config import get_settings
from src.prompts import RAG_PROMPT, REFUSAL_PHRASE
from src.query import get_vector_store


def format_docs(docs: list[Document]) -> str:
    """Format retrieved documents with source and section headers for prompt injection."""
    if not docs:
        return "NO RUNBOOK CONTEXT AVAILABLE."

    formatted_blocks = []
    for doc in docs:
        filename = doc.metadata.get("filename", "unknown.md")
        title = doc.metadata.get("title", "")
        doc_id = doc.metadata.get("document_id", "")
        header_info = f"Source: {filename}"
        if title:
            header_info += f", Title: {title}"
        if doc_id:
            header_info += f", ID: {doc_id}"

        block = f"[{header_info}]\n{doc.page_content}"
        formatted_blocks.append(block)

    return "\n\n---\n\n".join(formatted_blocks)


class MockGroundedChatModel(BaseChatModel):
    """Deterministic offline chat model for offline tests and local development."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        from langchain_core.outputs import ChatGeneration, ChatResult

        # Extract system and human message text
        system_text = messages[0].content if len(messages) > 0 else ""
        human_text = messages[1].content if len(messages) > 1 else ""

        # Extract context block from system prompt
        context = ""
        if "--- RUNBOOK CONTEXT START ---" in system_text:
            context = system_text.split("--- RUNBOOK CONTEXT START ---")[1].split("--- RUNBOOK CONTEXT END ---")[0].strip()

        # Check if context is absent or empty
        if not context or context == "NO RUNBOOK CONTEXT AVAILABLE.":
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=REFUSAL_PHRASE))])

        # If question is completely unrelated to the retrieved runbook context, refuse
        question_lower = human_text.lower()
        context_lower = context.lower()

        # Check if question keywords match domain concepts
        domain_keywords = {
            "postgres", "postgresql", "failover", "replica", "database", "patroni", "pgbouncer",
            "refund", "sla", "credit", "invoice", "netsuite", "billing", "downtime",
            "scim", "provisioning", "break-glass", "okta", "saml", "rbac", "user", "access"
        }
        has_domain_term = any(term in question_lower for term in domain_keywords)
        if not has_domain_term:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=REFUSAL_PHRASE))])

        # Synthesize grounded answer with citations
        lines = [
            "Based on the verified runbooks, here are the operational steps:\n",
        ]

        if "promote" in question_lower or "database" in question_lower or "postgresql" in question_lower:
            lines.append("1. Isolate the degraded primary to avoid split-brain conditions [Source: database_failover_runbook.md, Section: 4.1 Isolate Primary].")
            lines.append("2. Execute replica promotion command: `/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main` [Source: database_failover_runbook.md, Section: 4.2 Promote Synchronous Replica].")
            lines.append("3. Update PgBouncer upstream routing configuration to point to the new primary node [Source: database_failover_runbook.md, Section: 4.3 Switch PgBouncer].")
        elif "refund" in question_lower or "sla" in question_lower or "credit" in question_lower:
            lines.append("1. Verify account status and validate synthetic downtime duration against Datadog monitors [Source: refund_policy_enterprise.md, Section: 4.1 Claim Ingestion].")
            lines.append("2. Compute credit percentage against SLA uptime compensation grid (e.g. 50% credit for 99.00%-99.49% uptime) [Source: refund_policy_enterprise.md, Section: 2 SLA Credit Grid].")
            lines.append("3. Obtain appropriate approval based on credit amount (e.g. Director approval for $5,000-$24,999) [Source: refund_policy_enterprise.md, Section: 3 Escalation Matrix].")
        elif "scim" in question_lower or "provisioning" in question_lower or "break-glass" in question_lower:
            lines.append("1. If SCIM token expired (`ERR_401_SCIM_TOKEN_EXPIRED`), rotate secret in Vault path `secret/idp/scim-bearer` [Source: user_provisioning_sop.md, Section: 3 SCIM Synchronization].")
            lines.append("2. In P0/P1 emergency where SSO is unreachable, engage 2-person quorum to retrieve break-glass credentials [Source: user_provisioning_sop.md, Section: 4 Break-Glass Emergency Protocol].")
        else:
            lines.append(f"Follow the documented operational procedure [Source: runbooks, Section: General].")

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="\n".join(lines)))])

    @property
    def _llm_type(self) -> str:
        return "mock-grounded-chat-model"


def get_chat_model() -> BaseChatModel:
    """Return configured ChatOpenAI model, or MockGroundedChatModel for offline tests."""
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value()

    if api_key and not api_key.startswith("sk-test-placeholder"):
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=api_key,
        )

    return MockGroundedChatModel()


def build_rag_chain(k: int = 3) -> tuple[Any, Any]:
    """Construct LCEL RAG chain returning both the answer and the source documents.

    Pipeline:
      question -> retriever -> format_docs -> prompt -> llm -> StrOutputParser()
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    llm = get_chat_model()

    # LCEL generation pipeline
    rag_chain_from_docs = (
        {
            "context": lambda x: format_docs(x["documents"]),
            "question": lambda x: x["question"],
        }
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    return retriever, rag_chain_from_docs


def answer_question(question: str, k: int = 3) -> dict[str, Any]:
    """Execute end-to-end RAG query returning answer text and source documents."""
    retriever, chain = build_rag_chain(k=k)
    source_docs = retriever.invoke(question)

    answer_text = chain.invoke(
        {
            "question": question,
            "documents": source_docs,
        }
    )

    return {
        "question": question,
        "answer": answer_text,
        "source_documents": source_docs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpsCopilot End-to-End RAG Query Runner")
    parser.add_argument(
        "question",
        nargs="?",
        default="How do I promote the PostgreSQL replica during failover?",
        help="Operational question to answer.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OPSCOPILOT DAY 7: END-TO-END GROUNDED RAG CHAIN")
    print("=" * 70)
    print(f"QUESTION: {args.question}\n")

    result = answer_question(args.question)

    print("[ANSWER]:")
    print(result["answer"])
    print("\n" + "-" * 70)
    print(f"[RETRIEVED {len(result['source_documents'])} SOURCE DOCUMENTS]:")
    for idx, doc in enumerate(result["source_documents"], start=1):
        filename = doc.metadata.get("filename", "unknown")
        doc_id = doc.metadata.get("document_id", "N/A")
        print(f"  {idx}. {filename} ({doc_id})")
    print("=" * 70)
