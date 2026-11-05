"""Interactive step-by-step visualizer for the LCEL generation pipeline.

Demonstrates how data transforms at each stage of:
    input -> {context, question} -> RAG_PROMPT -> llm -> StrOutputParser()
"""

import sys
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from src.prompts import RAG_PROMPT
from src.rag_chain import format_docs, get_chat_model


def print_banner(step_num: int, title: str):
    print("\n" + "=" * 70)
    print(f"  STAGE {step_num}: {title}")
    print("=" * 70)


def interactive_lcel_demo():
    print("#" * 70)
    print("      INTERACTIVE LCEL PIPELINE VISUALIZER (Step-by-Step)")
    print("#" * 70)
    print("LCEL expression we are tracing:")
    print("  rag_chain = { 'context': format_docs, 'question': ... } | RAG_PROMPT | llm | StrOutputParser()")

    # -------------------------------------------------------------
    # STAGE 0: The Raw Inputs
    # -------------------------------------------------------------
    print_banner(0, "RAW INPUT (What enters the pipeline)")
    user_question = "How do I promote the PostgreSQL replica?"
    sample_docs = [
        Document(
            page_content="Log into pg-replica-02.internal and run:\n/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main",
            metadata={"filename": "database_failover_runbook.md", "title": "PostgreSQL HA Failover", "document_id": "RB-OPS-042"}
        ),
        Document(
            page_content="Update PgBouncer upstream host config to point to promoted primary:\nsed -i 's/host=10.0.12.10/host=10.0.12.44/' /etc/pgbouncer/pgbouncer.ini\nsystemctl reload pgbouncer",
            metadata={"filename": "database_failover_runbook.md", "title": "PostgreSQL HA Failover", "document_id": "RB-OPS-042"}
        )
    ]

    pipeline_input = {
        "question": user_question,
        "documents": sample_docs,
    }

    print(f"Data type: dict with keys {list(pipeline_input.keys())}")
    print(f"  - question: '{pipeline_input['question']}'")
    print(f"  - documents: list of {len(pipeline_input['documents'])} raw Document objects")

    # -------------------------------------------------------------
    # STAGE 1: Dict Mapping & format_docs()
    # -------------------------------------------------------------
    print_banner(1, "DICTIONARY MAPPING (format_docs + passthrough question)")
    print("In LCEL: { 'context': lambda x: format_docs(x['documents']), 'question': lambda x: x['question'] }")

    stage_1_output = {
        "context": format_docs(pipeline_input["documents"]),
        "question": pipeline_input["question"],
    }

    print(f"\nResult data type: dict with keys {list(stage_1_output.keys())}")
    print("\n--- Value of 'context' (glued plain text string) ---")
    print(stage_1_output["context"])
    print("\n--- Value of 'question' ---")
    print(stage_1_output["question"])

    # -------------------------------------------------------------
    # STAGE 2: | RAG_PROMPT (ChatPromptTemplate)
    # -------------------------------------------------------------
    print_banner(2, "PIPE INTO RAG_PROMPT (| RAG_PROMPT)")
    print("The template takes {'context': ..., 'question': ...} and fills in the blanks.")

    stage_2_output = RAG_PROMPT.format_prompt(**stage_1_output)
    messages = stage_2_output.to_messages()

    print(f"\nResult data type: PromptValue -> contains {len(messages)} Chat Messages")
    print("\n[Message 1: SystemMessage (Rules + Embedded Context)]:")
    print(messages[0].content[:350] + "\n...[truncated for display]...")
    print("\n[Message 2: HumanMessage (User Question)]:")
    print(messages[1].content)

    # -------------------------------------------------------------
    # STAGE 3: | llm (ChatModel / GPT-4)
    # -------------------------------------------------------------
    print_banner(3, "PIPE INTO LLM (| llm)")
    print("Sends the 2 messages to the model (gpt-4o-mini, temperature=0.0).")

    llm = get_chat_model()
    stage_3_output = llm.invoke(messages)

    print(f"\nResult data type: {type(stage_3_output).__name__} (AIMessage object)")
    print(f"Raw object attributes:")
    print(f"  - type: {stage_3_output.type}")
    print(f"  - content length: {len(stage_3_output.content)} characters")
    print(f"  - raw preview:\n    {stage_3_output.content[:200]}...")

    # -------------------------------------------------------------
    # STAGE 4: | StrOutputParser()
    # -------------------------------------------------------------
    print_banner(4, "PIPE INTO PARSER (| StrOutputParser())")
    print("Strips the outer AIMessage object wrapper to extract just the pure Python 'str'.")

    parser = StrOutputParser()
    stage_4_output = parser.invoke(stage_3_output)

    print(f"\nResult data type: {type(stage_4_output).__name__} (pure text string ready for user UI)")
    print("\n" + "#" * 70)
    print("FINAL DELIVERED ANSWER:")
    print("#" * 70)
    print(stage_4_output)
    print("#" * 70)


if __name__ == "__main__":
    interactive_lcel_demo()
