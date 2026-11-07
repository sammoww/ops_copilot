"""Encapsulated production application service for OpsCopilot."""

from functools import lru_cache
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.vectorstores import VectorStore

try:
    from langchain.chains import create_history_aware_retriever
except (ImportError, ModuleNotFoundError):
    from langchain_classic.chains import create_history_aware_retriever

from src.config import Settings, get_settings
from src.prompts import CONTEXTUALIZE_Q_PROMPT, RAG_PROMPT, REFUSAL_PHRASE
from src.query import get_vector_store
from src.rag_chain import format_docs, get_chat_model


class OpsCopilotService:
    """Production application service encapsulating vector retrieval and LCEL generation.

    Designed for clean lifecycle management and seamless Dependency Injection
    in FastAPI (Day 11+) and Streamlit (Day 14+). Reuses database connections
    and model instances to eliminate per-request connection overhead.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm: Optional[BaseChatModel] = None,
        settings: Optional[Settings] = None,
        k: int = 3,
    ) -> None:
        """Initialize service dependencies with optional dependency injection.

        Args:
            vector_store: Injected vector store, or lazily resolved singleton.
            llm: Injected language model, or lazily resolved model.
            settings: Application configuration settings.
            k: Top-k documents to retrieve per operational query.
        """
        self.settings = settings or get_settings()
        self.k = k
        self.vector_store = vector_store or get_vector_store()
        self.llm = llm or get_chat_model()

        # Build reusable underlying retriever
        self.base_retriever = self.vector_store.as_retriever(search_kwargs={"k": self.k})

        # Build history-aware contextual retriever
        self.history_retriever = create_history_aware_retriever(
            llm=self.llm,
            retriever=self.base_retriever,
            prompt=CONTEXTUALIZE_Q_PROMPT,
        )

        # Build reusable LCEL document-to-answer generation pipeline
        self.rag_chain = (
            {
                "context": lambda x: format_docs(x["documents"]),
                "question": lambda x: x["question"],
            }
            | RAG_PROMPT
            | self.llm
            | StrOutputParser()
        )

    def query(
        self,
        question: str,
        history: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        """Execute a conversational RAG query against verified operational runbooks.

        Args:
            question: Operational troubleshooting question from user/engineer.
            history: Optional multi-turn conversation history.

        Returns:
            Dictionary containing:
                - question (str): The original question asked.
                - answer (str): Grounded answer with source citations.
                - source_documents (list[Document]): Retrieved source runbook chunks.
                - chat_history (list): Preserved conversation session history.
        """
        if not question or not question.strip():
            return {
                "question": question,
                "answer": REFUSAL_PHRASE,
                "source_documents": [],
                "chat_history": history or [],
            }

        # Normalize chat history into BaseMessage instances if passed as dicts or tuples
        normalized_history: list[BaseMessage] = []
        if history:
            for item in history:
                if isinstance(item, BaseMessage):
                    normalized_history.append(item)
                elif isinstance(item, dict):
                    role = item.get("role", "user")
                    content = item.get("content", "")
                    if role in ("user", "human"):
                        normalized_history.append(HumanMessage(content=content))
                    elif role in ("assistant", "ai"):
                        normalized_history.append(AIMessage(content=content))

        # Retrieve documents using conversational history-aware retriever
        source_docs = self.history_retriever.invoke(
            {
                "input": question,
                "chat_history": normalized_history,
            }
        )

        # Generate grounded answer via LCEL chain
        answer_text = self.rag_chain.invoke(
            {
                "question": question,
                "documents": source_docs,
            }
        )

        return {
            "question": question,
            "answer": answer_text,
            "source_documents": source_docs,
            "chat_history": normalized_history,
        }

    def health_check(self) -> bool:
        """Verify health and operational readiness of underlying dependencies.

        Checks:
            1. Vector store is instantiated and queryable.
            2. LLM client is configured and initialized.

        Returns:
            bool: True if all components are functional, False otherwise.
        """
        try:
            # Check vector store connectivity by executing a 1-doc probe
            probe_docs = self.base_retriever.invoke("healthcheck probe")
            if not isinstance(probe_docs, list):
                return False

            # Check LLM instance exists
            if self.llm is None:
                return False

            return True
        except Exception:
            return False


@lru_cache()
def get_opscopilot_service() -> OpsCopilotService:
    """Return cached singleton instance of OpsCopilotService for FastAPI dependency injection."""
    return OpsCopilotService()
