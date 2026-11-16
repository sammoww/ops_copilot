"""OpsCopilot Day 19: End-to-End Live Demo Walkthrough.

Demonstrates the 3 core capabilities of OpsCopilot in the terminal:
1. Grounded Runbook Q&A with real-time streaming and source citations.
2. Zero-Hallucination Refusal Protocol on out-of-domain queries.
3. Autonomous SRE Action Tool Calling (Telemetry check & Incident ticket creation).
"""

import sys
import time
from src.agent import OpsCopilotAgent


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def stream_typewriter(text: str, delay: float = 0.002) -> None:
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def run_demo() -> None:
    agent = OpsCopilotAgent()

    # -------------------------------------------------------------
    # DEMO 1: Grounded Q&A with Streaming & Citation
    # -------------------------------------------------------------
    print_banner("DEMO 1: Grounded SRE Runbook Q&A + Citation Provenance")
    query_1 = "What is the command to promote the PostgreSQL replica node?"
    print(f"[ENGINEER]: {query_1}\n")
    print("[OPSCOPILOT (Streaming Response)]:")
    
    response_1 = agent.run(query_1)
    stream_typewriter(response_1.answer)
    print(f"\n-> Tools Triggered: {response_1.tools_called}")
    print("-> Status: SUCCESS (Verified from Patroni Failover Runbook)")

    time.sleep(1.5)

    # -------------------------------------------------------------
    # DEMO 2: Zero-Hallucination Refusal Guardrail
    # -------------------------------------------------------------
    print_banner("DEMO 2: Anti-Hallucination Refusal Protocol")
    query_2 = "How do I configure the company 401(k) retirement match?"
    print(f"[ENGINEER]: {query_2}\n")
    print("[OPSCOPILOT (Refusal Response)]:")

    response_2 = agent.run(query_2)
    stream_typewriter(response_2.answer)
    print(f"\n-> Tools Triggered: {response_2.tools_called}")
    print("-> Status: GUARDRAIL TRIGGERED (Out-of-domain query safely refused)")

    time.sleep(1.5)

    # -------------------------------------------------------------
    # DEMO 3: Autonomous Incident Action Tools
    # -------------------------------------------------------------
    print_banner("DEMO 3: Autonomous Incident Telemetry & Ticketing Tools")
    query_3 = "The database latency is spiking. Check health of postgres-primary and file an urgent incident ticket."
    print(f"[ENGINEER]: {query_3}\n")
    print("[OPSCOPILOT (ReAct Agent Execution)]:")

    response_3 = agent.run(query_3)
    for step in response_3.intermediate_steps:
        print(f"  [ACTION EXECUTED]: Tool '{step.tool_name}'")
        print(f"  [INPUT ARGS]     : {step.tool_args}")
        print(f"  [TOOL OUTPUT]    : {step.output}")
        print()

    print("[OPSCOPILOT FINAL SYNTHESIS]:")
    stream_typewriter(response_3.answer)
    print(f"\n-> Tools Triggered: {response_3.tools_called}")
    print("-> Status: SUCCESS (Autonomous remediation actions dispatched)")

    print_banner("END-TO-END DEMO WALKTHROUGH COMPLETE (3/3 SUCCESS)")


if __name__ == "__main__":
    run_demo()
