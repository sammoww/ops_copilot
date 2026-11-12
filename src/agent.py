"""Enterprise ReAct agent execution loop and tool routing engine for OpsCopilot."""

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from pydantic import ValidationError

from src.rag_chain import get_chat_model
from src.tools.incident_tools import ALL_AGENT_TOOLS

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Record of a single tool execution step within the agent loop."""

    tool_name: str
    tool_args: dict[str, Any]
    tool_call_id: str
    output: Any
    is_error: bool = False


@dataclass
class AgentResponse:
    """Structured response returned by the OpsCopilot execution loop."""

    query: str
    answer: str
    intermediate_steps: list[AgentStep] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    iterations: int = 0
    success: bool = True
    error_message: Optional[str] = None


class OpsCopilotAgent:
    """Production ReAct execution loop managing model invocation, tool routing, and self-healing error recovery.

    Loop Mechanics:
    1. Send user query and chat history to the tool-bound ChatModel.
    2. If the model outputs standard text (no tool_calls), return the answer directly.
    3. If the model emits tool_calls:
       a. Safely execute each requested tool locally in Python.
       b. Catch Pydantic ValidationErrors or runtime exceptions without crashing.
       c. Package results/errors into ToolMessages and append to conversation history.
       d. Repeat the loop so the model can self-correct or synthesize the final answer.
    4. Guards against infinite loops via a hard max_iterations ceiling.
    """

    def __init__(
        self,
        model: Optional[BaseChatModel] = None,
        tools: Optional[list[Any]] = None,
        max_iterations: int = 5,
    ) -> None:
        """Initialize the agent with models, tool registry, and loop parameters.

        Args:
            model: Optional injected chat model (defaults to get_chat_model()).
            tools: Optional tool list (defaults to ALL_AGENT_TOOLS).
            max_iterations: Maximum loop iterations to prevent infinite recursion.
        """
        self.raw_model = model or get_chat_model()
        self.tools_list = tools or ALL_AGENT_TOOLS
        self.tool_map = {t.name: t for t in self.tools_list}
        self.max_iterations = max_iterations

        # Bind available tools to the chat model
        self.bound_model = self.raw_model.bind_tools(self.tools_list)

    def run(
        self,
        query: str,
        chat_history: Optional[list[BaseMessage]] = None,
    ) -> AgentResponse:
        """Execute the multi-turn agent execution loop.

        Args:
            query: The user query, question, or incident command.
            chat_history: Optional prior conversation turns.

        Returns:
            AgentResponse containing the final answer, intermediate tool steps, and execution telemetry.
        """
        if not query or not query.strip():
            return AgentResponse(
                query=query,
                answer="No query provided. Please ask an operational question or request a service action.",
                iterations=0,
                success=True,
            )

        messages: list[BaseMessage] = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=query.strip()))

        intermediate_steps: list[AgentStep] = []
        tools_called: list[str] = []

        for iteration in range(1, self.max_iterations + 1):
            logger.debug(f"[OpsCopilotAgent] Iteration {iteration}/{self.max_iterations}")

            # 1. Invoke tool-bound model
            response = self.bound_model.invoke(messages)
            messages.append(response)

            # 2. Check stopping condition: model provided final response without tool calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                return AgentResponse(
                    query=query,
                    answer=response.content if hasattr(response, "content") else str(response),
                    intermediate_steps=intermediate_steps,
                    tools_called=tools_called,
                    iterations=iteration,
                    success=True,
                )

            # 3. Process each tool call requested by the model
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                call_id = tool_call.get("id", f"call_{iteration}")

                tools_called.append(tool_name)

                # Execute tool safely
                if tool_name not in self.tool_map:
                    err_msg = f"TOOL_NOT_FOUND: Tool '{tool_name}' is not in the registered tool catalog."
                    intermediate_steps.append(
                        AgentStep(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_call_id=call_id,
                            output=err_msg,
                            is_error=True,
                        )
                    )
                    messages.append(ToolMessage(content=err_msg, tool_call_id=call_id))
                    continue

                tool_func = self.tool_map[tool_name]
                try:
                    # Run the tool (Pydantic validates input arguments here)
                    result = tool_func.invoke(tool_args)
                    result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                    is_error = False

                    intermediate_steps.append(
                        AgentStep(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_call_id=call_id,
                            output=result,
                            is_error=False,
                        )
                    )

                except ValidationError as ve:
                    # Pydantic input validation failure - provide actionable feedback for self-correction
                    result_str = (
                        f"VALIDATION_ERROR: Invalid arguments for tool '{tool_name}': {ve}. "
                        "Please adjust parameter values to match the schema and retry."
                    )
                    is_error = True
                    intermediate_steps.append(
                        AgentStep(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_call_id=call_id,
                            output=result_str,
                            is_error=True,
                        )
                    )

                except Exception as exc:
                    # General tool execution failure (network, database, timeout)
                    result_str = f"TOOL_EXECUTION_ERROR: Tool '{tool_name}' failed with exception: {exc}"
                    is_error = True
                    intermediate_steps.append(
                        AgentStep(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_call_id=call_id,
                            output=result_str,
                            is_error=True,
                        )
                    )

                # Append tool result as ToolMessage to continue the loop
                messages.append(ToolMessage(content=result_str, tool_call_id=call_id))

        # Reached max iterations without the model producing a final stopping answer
        return AgentResponse(
            query=query,
            answer="OpsCopilot was unable to complete the request within the safety execution limit. Please refine your query.",
            intermediate_steps=intermediate_steps,
            tools_called=tools_called,
            iterations=self.max_iterations,
            success=False,
            error_message="Maximum agent iterations exceeded (loop guard triggered).",
        )

    async def astream(
        self,
        query: str,
        chat_history: Optional[list[BaseMessage]] = None,
    ):
        """Yield progressive tokens asynchronously from the agent execution loop.

        Pipeline:
        1. Evaluates incoming query against bound tools.
        2. If a tool call is required, executes it and adds ToolMessage to conversation history.
        3. Streams the final synthesized tokens progressively using the model's astream API.
        """
        if not query or not query.strip():
            yield "No query provided. Please ask an operational question or request a service action."
            return

        messages: list[BaseMessage] = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=query.strip()))

        # Determine if tools are needed
        response = await self.bound_model.ainvoke(messages)
        tool_calls = getattr(response, "tool_calls", None) or []

        if tool_calls:
            messages.append(response)
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                call_id = tool_call.get("id", "call_stream")

                if tool_name in self.tool_map:
                    try:
                        result = self.tool_map[tool_name].invoke(tool_args)
                        result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                    except Exception as exc:
                        result_str = f"TOOL_ERROR: {exc}"
                else:
                    result_str = f"TOOL_NOT_FOUND: {tool_name}"

                messages.append(ToolMessage(content=result_str, tool_call_id=call_id))

            # Stream final synthesized response
            async for chunk in self.bound_model.astream(messages):
                token = getattr(chunk, "content", "")
                if token:
                    yield token
        else:
            # Stream response directly
            async for chunk in self.bound_model.astream(messages):
                token = getattr(chunk, "content", "")
                if token:
                    yield token


def run_agent(
    query: str,
    chat_history: Optional[list[BaseMessage]] = None,
    max_iterations: int = 5,
) -> AgentResponse:
    """Convenience helper to initialize an agent and execute a query."""
    agent = OpsCopilotAgent(max_iterations=max_iterations)
    return agent.run(query=query, chat_history=chat_history)
