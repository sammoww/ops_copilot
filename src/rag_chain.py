"""End-to-end grounded RAG chain using modern LCEL syntax."""

import argparse
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

try:
    from langchain.chains import create_history_aware_retriever
except (ImportError, ModuleNotFoundError):
    from langchain_classic.chains import create_history_aware_retriever

from src.config import get_settings
from src.prompts import CONTEXTUALIZE_Q_PROMPT, RAG_PROMPT, REFUSAL_PHRASE
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

        # Extract system and human message text flexibly across prompt structures
        system_text = ""
        human_text = ""
        for m in messages:
            msg_type = getattr(m, "type", "")
            if msg_type == "system":
                system_text = m.content
            elif msg_type in ("human", "user"):
                human_text = m.content

        if not human_text and messages:
            human_text = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        if not system_text and len(messages) > 1 and getattr(messages[0], "type", "") != "human":
            system_text = messages[0].content if hasattr(messages[0], "content") else str(messages[0])

        # Case A: Contextual Query Reformulation (called by create_history_aware_retriever)
        if "standalone question" in system_text.lower() or "reformulate" in system_text.lower():
            # Scan chat history messages (all messages between system and the latest human input)
            history_text = " ".join([m.content for m in messages[1:-1]]).lower()
            query_lower = human_text.lower()

            topic = ""
            if any(term in history_text for term in ["postgres", "postgresql", "failover", "replica", "database"]):
                topic = "PostgreSQL database replica failover"
            elif any(term in history_text for term in ["refund", "sla", "credit"]):
                topic = "enterprise SLA credit refund policy"
            elif any(term in history_text for term in ["scim", "provisioning", "break-glass"]):
                topic = "SCIM provisioning break-glass emergency"

            # If user query references previous topic with pronouns or follow-up phrasing
            followup_indicators = ["it", "step", "again", "second", "third", "how", "what about", "that"]
            has_indicator = any(word in query_lower.split() or word in query_lower for word in followup_indicators)

            if topic and has_indicator and not any(term in query_lower for term in ["postgres", "refund", "scim"]):
                rephrased = f"{human_text} for {topic}".strip()
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=rephrased))])

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=human_text))])

        # Case B: Tool Calling Detection (when tools are bound to the model)
        tools = kwargs.get("tools", [])
        if tools:
            # Check if a ToolMessage was already executed in this conversation
            last_tool_msg = None
            for m in reversed(messages):
                if getattr(m, "type", "") == "tool":
                    last_tool_msg = m
                    break

            if last_tool_msg is not None:
                import json
                tool_content = str(last_tool_msg.content)
                
                # Check for validation error feedback
                if "VALIDATION_ERROR" in tool_content:
                    return ChatResult(
                        generations=[ChatGeneration(message=AIMessage(content=f"I encountered a validation error: {tool_content}. Please provide valid parameters."))]
                    )

                # Format service status telemetry
                if any(k in tool_content.lower() for k in ["latency", "active_replicas", "diagnostic_alert", "error_rate"]):
                    try:
                        data = json.loads(tool_content)
                        ans = (
                            f"Service status for {data.get('service_name')}: {data.get('status')}. "
                            f"Latency: {data.get('latency_ms')}ms, Error rate: {data.get('error_rate_pct')}%, "
                            f"Active replicas: {data.get('active_replicas')}, Region: {data.get('region')}. "
                            f"Diagnostics: {data.get('diagnostic_alert')}"
                        )
                    except Exception:
                        ans = f"Service telemetry report:\n{tool_content}"
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=ans))])

                # Format incident ticket confirmation
                if any(k in tool_content.lower() for k in ["ticket_id", "inc-", "escalated_to"]):
                    try:
                        data = json.loads(tool_content)
                        ans = (
                            f"Incident ticket {data.get('ticket_id')} ({data.get('severity')}) successfully opened "
                            f"for '{data.get('title')}'. Escalated to: {data.get('escalated_to')}."
                        )
                    except Exception:
                        ans = f"Incident ticket dispatched:\n{tool_content}"
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=ans))])

                # Format runbook context search results
                if any(k in tool_content.lower() for k in ["runbook_context", "source:"]):
                    ans = (
                        "Based on verified runbooks retrieved from ChromaDB:\n"
                        "1. Isolate the degraded primary to avoid split-brain conditions [Source: database_failover_runbook.md, Section: 4.1 Isolate Primary].\n"
                        "2. Execute replica promotion command: `/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main` [Source: database_failover_runbook.md, Section: 4.2 Promote Synchronous Replica].\n"
                        "3. Update PgBouncer upstream routing configuration to point to the new primary node [Source: database_failover_runbook.md, Section: 4.3 Switch PgBouncer]."
                    )
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=ans))])

                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"Tool output: {tool_content}"))])

            # No tool executed yet -> check whether to invoke a tool or reply directly
            query_lower = human_text.lower()
            tool_calls = []

            # Check for get_service_status request
            if any(term in query_lower for term in ["status", "health", "latency", "telemetry"]):
                target_service = "postgres-primary"
                for s in ["auth-service", "payment-gateway", "postgres-primary", "pgbouncer"]:
                    if s in query_lower:
                        target_service = s
                        break
                tool_calls.append({
                    "name": "get_service_status",
                    "args": {"service_name": target_service},
                    "id": "call_mock_status_01",
                    "type": "tool_call",
                })

            # Check for create_incident_ticket request
            elif any(term in query_lower for term in ["ticket", "file an incident", "incident", "down", "outage"]):
                severity = "P0" if any(w in query_lower for w in ["p0", "urgent", "critical", "down"]) else "P1"
                tool_calls.append({
                    "name": "create_incident_ticket",
                    "args": {
                        "title": human_text.strip(),
                        "severity": severity,
                    },
                    "id": "call_mock_ticket_02",
                    "type": "tool_call",
                })

            # Check for search_runbooks request
            elif any(term in query_lower for term in ["failover", "runbook", "steps", "procedure", "replica", "postgres", "refund", "sla", "scim", "how do i", "how to"]):
                tool_calls.append({
                    "name": "search_runbooks",
                    "args": {"query": human_text.strip()},
                    "id": "call_mock_runbook_03",
                    "type": "tool_call",
                })

            if tool_calls:
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content="", tool_calls=tool_calls))]
                )

            # Direct conversation without tool call (e.g. greetings)
            if any(w in query_lower for w in ["hello", "hi", "hey", "who are you", "help"]):
                greeting = "Hello! I am OpsCopilot, your DevOps & SRE incident response assistant. How can I help with services, runbooks, or tickets today?"
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=greeting))])

        # Case C: Standard Grounded QA Generation
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
            "scim", "provisioning", "break-glass", "okta", "saml", "rbac", "user", "access",
            "step", "second step"
        }
        has_domain_term = any(term in question_lower for term in domain_keywords)
        if not has_domain_term:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=REFUSAL_PHRASE))])

        # Synthesize grounded answer with citations
        lines = [
            "Based on the verified runbooks, here are the operational steps:\n",
        ]

        if "promote" in question_lower or "database" in question_lower or "postgresql" in question_lower or "failover" in question_lower or "step" in question_lower:
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

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> Any:
        """Bind external tools to the mock chat model returning a runnable binding."""
        return self.bind(tools=tools, **kwargs)

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


def get_tool_enabled_model() -> Any:
    """Return configured ChatModel bound to external incident response action tools."""
    from src.tools.incident_tools import ALL_INCIDENT_TOOLS

    model = get_chat_model()
    return model.bind_tools(ALL_INCIDENT_TOOLS)


def build_rag_chain(k: int = 3) -> tuple[Any, Any]:
    """Construct LCEL RAG chain with history-aware retriever returning docs and answer.

    Pipeline:
      (question, chat_history) -> history_aware_retriever -> format_docs -> prompt -> llm -> StrOutputParser()
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    llm = get_chat_model()

    # History-aware retrieval: reformulates conversational follow-ups into standalone queries
    history_aware_retriever = create_history_aware_retriever(
        llm=llm,
        retriever=retriever,
        prompt=CONTEXTUALIZE_Q_PROMPT,
    )

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

    return history_aware_retriever, rag_chain_from_docs


def answer_question(
    question: str,
    chat_history: Optional[list[BaseMessage]] = None,
    k: int = 3,
) -> dict[str, Any]:
    """Execute end-to-end RAG query with optional multi-turn conversation history."""
    history_retriever, chain = build_rag_chain(k=k)
    history = chat_history or []

    # Retrieve docs using history-aware retriever
    source_docs = history_retriever.invoke(
        {
            "input": question,
            "chat_history": history,
        }
    )

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
        "chat_history": history,
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
