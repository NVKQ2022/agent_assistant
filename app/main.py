from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.config import settings
from app.context import UserContext, get_user_context, context_to_runnable_config
from app.agent import agent, ALL_TOOLS


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Prototype showing how a LangChain Agent Assistant extracts user context from HTTP web requests "
        "(headers, auth tokens, web context) and injects it securely into tools via LangChain RunnableConfig."
    ),
)

# Enable CORS for web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "What are my recent orders?"})
    thread_id: Optional[str] = Field(default=None, json_schema_extra={"example": "session_abc123"})


class ToolCallRecord(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    output: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    user_context: UserContext
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    thread_id: Optional[str] = None


@app.get("/health", tags=["System"])
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_configured": bool(settings.openai_api_key),
    }


@app.get("/user/context", response_model=UserContext, tags=["Context"])
async def inspect_request_context(context: UserContext = Depends(get_user_context)):
    """
    Diagnostic endpoint to inspect how HTTP request headers were parsed into UserContext.
    Send custom headers like `X-User-Id`, `X-User-Role`, `X-Tenant-Id`, or `Authorization: Bearer <token>`.
    """
    return context


@app.get("/tools", tags=["Agent"])
async def list_tools():
    """
    Lists all tools registered with the Agent Assistant and their public argument schemas.
    Notice that `config: RunnableConfig` is automatically hidden from the LLM arguments schema.
    """
    tools_info = []
    for t in ALL_TOOLS:
        tools_info.append({
            "name": t.name,
            "description": t.description,
            "args_schema": t.args,
        })
    return {"tools": tools_info}


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat_with_agent(
    payload: ChatRequest,
    context: UserContext = Depends(get_user_context),
):
    """
    Send a natural language message to the Agent Assistant.
    
    The user's identity is NOT taken from the prompt text; it is extracted from request headers
    (or Bearer token) and injected into LangChain's RunnableConfig at execution time.
    """
    # 1. Convert validated UserContext to LangChain RunnableConfig
    runnable_config = context_to_runnable_config(context, thread_id=payload.thread_id)
    
    # 2. Invoke LangChain Agent with user message and injected config
    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config=runnable_config,
        )
    except Exception as exc:
        err_msg = str(exc)
        if "content management policy" in err_msg or "content_filter" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request flagged by LLM safety filter. Please rephrase your query."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution error: {err_msg}"
        )
    
    # 3. Extract final response and tool execution audit trail
    messages = result.get("messages", [])
    final_response = "No response generated."
    tool_calls_map: Dict[str, ToolCallRecord] = {}
    
    for msg in messages:
        # Collect tool calls issued by the agent
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_calls_map[tc["id"]] = ToolCallRecord(
                    tool_name=tc["name"],
                    args=tc["args"],
                )
        # Collect outputs returned by the tools
        elif isinstance(msg, ToolMessage):
            tool_call_id = getattr(msg, "tool_call_id", "")
            if tool_call_id in tool_calls_map:
                tool_calls_map[tool_call_id].output = msg.content
            else:
                tool_calls_map[tool_call_id] = ToolCallRecord(
                    tool_name=getattr(msg, "name", "tool"),
                    args={},
                    output=msg.content,
                )
        # Final AI text
        elif isinstance(msg, AIMessage) and msg.content:
            final_response = msg.content
            
    return ChatResponse(
        response=final_response,
        user_context=context,
        tool_calls=list(tool_calls_map.values()),
        thread_id=payload.thread_id or context.session_id,
    )
