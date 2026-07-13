import json
from collections.abc import Iterator
from typing import Any, TypedDict

from google.genai import types
from sqlalchemy.orm import Session

from app.config import get_settings
from app.prompts.chat_prompt import CHAT_SYSTEM_PROMPT
from app.services.llm import call_with_retry, get_client
from app.services.memory import HistoryMessage
from app.services.retrieval import search_documents
from app.services.sql_tool import (
    SqlExecutionError,
    SqlGenerationError,
    SqlValidationError,
    execute_sql,
)

settings = get_settings()

_SEARCH_DOCUMENTS = types.FunctionDeclaration(
    name="search_documents",
    description=(
        "Search Northwind Gadgets' policy documents (HR leave, product FAQ, returns & refunds, "
        "warranty, pricing & discounts) for passages relevant to a natural-language question."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(type=types.Type.STRING, description="Natural-language search query")
        },
        required=["query"],
    ),
)

_EXECUTE_SQL = types.FunctionDeclaration(
    name="execute_sql",
    description=(
        "Answer a question about order data (counts, revenue, statuses, specific orders, "
        "customers, products, dates) by generating and running a SQL query against the "
        "orders table."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "question": types.Schema(
                type=types.Type.STRING, description="Natural-language question about orders"
            )
        },
        required=["question"],
    ),
)

_TOOLS = [types.Tool(function_declarations=[_SEARCH_DOCUMENTS, _EXECUTE_SQL])]


class OrchestratorEvent(TypedDict, total=False):
    type: str  # 'meta' | 'token' | 'done'
    delta: str
    content: str
    tool_used: str
    generated_sql: str | None
    citations: list[dict[str, Any]]


class _ToolCallState(TypedDict):
    used_rag: bool
    used_sql: bool
    citations: list[dict[str, Any]]
    generated_sql: str | None


def _history_to_contents(history: list[HistoryMessage]) -> list[types.Content]:
    return [
        types.Content(role="user" if msg.role == "user" else "model", parts=[types.Part(text=msg.content)])
        for msg in history
    ]


def _execute_tool_call(db: Session, call: types.FunctionCall, state: _ToolCallState) -> types.Part:
    if call.name == "search_documents":
        query = (call.args or {}).get("query", "")
        state["used_rag"] = True
        result = search_documents(db, query)
        state["citations"].extend(
            {"document": c.document, "section": c.section, "snippet": c.snippet}
            for c in result.citations
        )
        tool_text = "\n\n".join(result.chunks) if result.has_results else "No relevant documents found."
        return types.Part.from_function_response(name=call.name, response={"result": tool_text})

    if call.name == "execute_sql":
        question = (call.args or {}).get("question", "")
        state["used_sql"] = True
        try:
            sql_result = execute_sql(question)
        except (SqlValidationError, SqlExecutionError, SqlGenerationError) as exc:
            return types.Part.from_function_response(
                name=call.name, response={"result": f"The query could not be executed: {exc}"}
            )
        if sql_result.applicable:
            state["generated_sql"] = sql_result.generated_sql
            payload = {"columns": sql_result.columns, "rows": sql_result.rows}
            return types.Part.from_function_response(
                name=call.name, response={"result": json.dumps(payload, default=str)}
            )
        return types.Part.from_function_response(
            name=call.name, response={"result": "This question cannot be answered from the orders data."}
        )

    raise ValueError(f"Unknown tool call: {call.name}")


def run_turn(db: Session, history: list[HistoryMessage], user_text: str) -> Iterator[OrchestratorEvent]:
    """Runs one chat turn: routes to tools (0, 1, or 2 in parallel), then streams the answer.

    Bounded at a single round of tool calls (no further tool calls during synthesis), which
    covers RAG-only, SQL-only, both, and no-tool questions per the assignment spec without an
    open-ended agent loop. Yields exactly one "meta" event, then "token" events, then "done".
    """
    client = get_client()
    contents = _history_to_contents(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    routing_response = call_with_retry(
        client.models.generate_content,
        model=settings.chat_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=CHAT_SYSTEM_PROMPT,
            tools=_TOOLS,
            temperature=0,
        ),
    )

    state: _ToolCallState = {
        "used_rag": False,
        "used_sql": False,
        "citations": [],
        "generated_sql": None,
    }
    function_calls = routing_response.function_calls or []

    if function_calls:
        contents.append(routing_response.candidates[0].content)
        response_parts = [_execute_tool_call(db, call, state) for call in function_calls]
        contents.append(types.Content(role="user", parts=response_parts))

    if state["used_rag"] and state["used_sql"]:
        tool_used = "both"
    elif state["used_rag"]:
        tool_used = "rag"
    elif state["used_sql"]:
        tool_used = "sql"
    else:
        tool_used = "none"

    yield {
        "type": "meta",
        "tool_used": tool_used,
        "generated_sql": state["generated_sql"],
        "citations": state["citations"],
    }

    full_text = ""
    # Once function-call turns are in `contents`, Gemini expects `tools` to stay declared on
    # subsequent calls in the same conversation; force text-only output here via tool_config
    # so the synthesis turn can't itself emit another function call instead of an answer.
    stream = call_with_retry(
        client.models.generate_content_stream,
        model=settings.chat_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=CHAT_SYSTEM_PROMPT,
            tools=_TOOLS,
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.NONE
                )
            ),
            temperature=0,
        ),
    )
    for chunk in stream:
        if chunk.text:
            full_text += chunk.text
            yield {"type": "token", "delta": chunk.text}

    yield {
        "type": "done",
        "content": full_text,
        "tool_used": tool_used,
        "generated_sql": state["generated_sql"],
        "citations": state["citations"],
    }
