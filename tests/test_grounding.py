"""Day 8 Automated Grounding and Hallucination Verification Test Suite.

Validates that OpsCopilot strictly adheres to grounding constraints:
1. Direct factual queries return precise ground-truth runbook answers with citations.
2. Multi-chunk queries synthesize procedures spanning multiple sections.
3. Out-of-domain queries return the exact refusal phrase without hallucinating.
"""

import pytest
from src.prompts import REFUSAL_PHRASE
from src.rag_chain import answer_question


# Test Case Definitions (5 required test cases)
GROUNDING_TEST_CASES = [
    # Case 1: Direct Factual Query (PostgreSQL promotion)
    {
        "id": "factual_pg_promotion",
        "category": "factual",
        "query": "What is the command to promote the PostgreSQL replica node?",
        "expected_citations": ["database_failover_runbook.md"],
        "expected_phrases": ["pg_ctl promote", "/var/lib/postgresql/16/main"],
        "must_refuse": False,
    },
    # Case 2: Direct Factual Query (SLA Credit Grid)
    {
        "id": "factual_sla_credit",
        "category": "factual",
        "query": "What SLA credit percentage is granted for monthly uptime between 99.00% and 99.49%?",
        "expected_citations": ["refund_policy_enterprise.md"],
        "expected_phrases": ["50% credit"],
        "must_refuse": False,
    },
    # Case 3: Multi-chunk Query (Full Failover Procedure spanning isolation + promotion + pgbouncer)
    {
        "id": "multi_chunk_failover",
        "category": "multi_chunk",
        "query": "What are the complete steps for a PostgreSQL database failover to replica including PgBouncer?",
        "expected_citations": ["database_failover_runbook.md"],
        "expected_phrases": ["pg_ctl promote", "PgBouncer", "isolate"],
        "must_refuse": False,
    },
    # Case 4: Out-of-domain Query (HR / 401k policy)
    {
        "id": "out_of_domain_401k",
        "category": "out_of_domain",
        "query": "What is our corporate 401k matching policy and vesting schedule?",
        "expected_citations": [],
        "expected_phrases": [REFUSAL_PHRASE],
        "must_refuse": True,
    },
    # Case 5: Out-of-domain Query (General cooking recipe / unrelated tech)
    {
        "id": "out_of_domain_recipe",
        "category": "out_of_domain",
        "query": "How do I bake traditional Italian lasagna with homemade béchamel sauce?",
        "expected_citations": [],
        "expected_phrases": [REFUSAL_PHRASE],
        "must_refuse": True,
    },
]


@pytest.mark.parametrize("case", GROUNDING_TEST_CASES, ids=lambda c: c["id"])
def test_grounding_verification(case):
    """Verify factual grounding, multi-chunk synthesis, and zero-hallucination refusals."""
    result = answer_question(case["query"], k=3)
    answer = result["answer"]
    docs = result["source_documents"]

    # Assertion 1: Basic result structure integrity
    assert isinstance(answer, str)
    assert len(answer.strip()) > 0
    assert len(docs) > 0

    if case["must_refuse"]:
        # Zero-hallucination guardrail check:
        # Out-of-domain queries MUST return the exact system refusal phrase
        assert REFUSAL_PHRASE in answer, (
            f"Expected refusal for out-of-domain query '{case['query']}', but got: {answer}"
        )
    else:
        # In-domain factual grounding check:
        # 1. Must NOT return the refusal phrase
        assert REFUSAL_PHRASE not in answer, (
            f"Pipeline falsely refused in-domain query '{case['query']}': {answer}"
        )

        # 2. Must cite the expected runbook sources
        for expected_source in case["expected_citations"]:
            assert expected_source in answer, (
                f"Missing citation '{expected_source}' in answer: {answer}"
            )

        # 3. Must contain the expected ground truth keywords/commands
        for expected_phrase in case["expected_phrases"]:
            assert expected_phrase.lower() in answer.lower(), (
                f"Expected phrase '{expected_phrase}' missing from answer: {answer}"
            )


def test_retrieval_documents_relevance_count():
    """Verify the pipeline retrieves the requested top-k documents."""
    result = answer_question("How do I promote the PostgreSQL replica?", k=3)
    assert len(result["source_documents"]) == 3
    # Check that retrieved documents have page_content and metadata
    for doc in result["source_documents"]:
        assert hasattr(doc, "page_content")
        assert len(doc.page_content) > 0
        assert "filename" in doc.metadata
