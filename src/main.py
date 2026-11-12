"""Production FastAPI application entrypoint for OpsCopilot."""

from functools import lru_cache
import json
import re
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.agent import OpsCopilotAgent
from src.api.schemas import ChatRequest, ChatResponse, HealthResponse

# Initialize FastAPI application
app = FastAPI(
    title="OpsCopilot API",
    description="Production-grade enterprise RAG & SRE incident response assistant REST API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS) for web frontend & Slack integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_agent() -> OpsCopilotAgent:
    """Dependency provider returning singleton OpsCopilotAgent instance."""
    return OpsCopilotAgent()


def _extract_sources(answer: str, intermediate_steps: list[Any]) -> list[str]:
    """Extract runbook citations from answer text or intermediate search results."""
    sources: list[str] = []

    # 1. Regex extract bracketed citations like [Source: filename.md, Section: ...]
    bracket_matches = re.findall(r"\[Source:\s*([^\]]+)\]", answer)
    for match in bracket_matches:
        cleaned = match.strip()
        if cleaned not in sources:
            sources.append(cleaned)

    # 2. Extract from search_runbooks tool output if present
    for step in intermediate_steps:
        if getattr(step, "tool_name", "") == "search_runbooks":
            output = getattr(step, "output", {})
            if isinstance(output, dict) and "runbook_context" in output:
                context_str = output["runbook_context"]
                runbook_matches = re.findall(r"Source:\s*([^,\n\]]+)", context_str)
                for rb in runbook_matches:
                    rb_clean = rb.strip()
                    if rb_clean not in sources:
                        sources.append(rb_clean)

    return sources


@app.get("/", tags=["General"])
def root_endpoint() -> dict[str, str]:
    """Root endpoint providing service identification."""
    return {
        "service": "OpsCopilot API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Diagnostics"],
)
def health_check() -> HealthResponse:
    """Readiness and liveness probe for container orchestrators (K8s) and load balancers."""
    return HealthResponse(status="ok", version="0.1.0")


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Incident Response"],
)
@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Incident Response"],
)
def chat_endpoint(
    request: ChatRequest,
    agent: OpsCopilotAgent = Depends(get_agent),
) -> ChatResponse:
    """Execute operational query against incident runbooks and telemetry tools."""
    try:
        agent_response = agent.run(query=request.message)

        sources = _extract_sources(
            answer=agent_response.answer,
            intermediate_steps=agent_response.intermediate_steps,
        )

        return ChatResponse(
            answer=agent_response.answer,
            sources=sources,
            tools_called=agent_response.tools_called,
            success=agent_response.success,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpsCopilot execution error: {str(exc)}",
        )


@app.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
    tags=["Incident Response"],
)
@app.post(
    "/api/v1/chat/stream",
    status_code=status.HTTP_200_OK,
    tags=["Incident Response"],
)
async def chat_stream_endpoint(
    request: ChatRequest,
    agent: OpsCopilotAgent = Depends(get_agent),
) -> StreamingResponse:
    """Stream progressive LLM tokens asynchronously using Server-Sent Events (SSE)."""

    async def event_generator():
        try:
            async for token in agent.astream(query=request.message):
                chunk_data = json.dumps({"token": token})
                yield f"data: {chunk_data}\n\n"

            # SSE termination signal
            yield "data: [DONE]\n\n"
        except Exception as exc:
            err_data = json.dumps({"error": str(exc)})
            yield f"data: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
