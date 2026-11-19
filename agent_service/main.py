from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from agent_service.config import settings
from agent_service.context import (
    UserContext,
    WebContext,
    extract_user_context,
    context_to_runnable_config,
)
from agent_service.agent import agent


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Agent Assistant Service for handling conversation and context-aware tool calls."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the assistant")
    web_context: Optional[WebContext] = Field(default=None, description="Current web page context and form draft values")
    thread_id: Optional[str] = Field(default=None, description="Conversation thread identifier")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    output: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    user_context: UserContext
    web_context: WebContext
    thread_id: str
    tool_calls: List[ToolExecutionRecord] = Field(default_factory=list)
    action: Optional[str] = None  # "verification_required", "form_submitted", or None
    verification_data: Optional[Dict[str, Any]] = None


@app.get("/health", tags=["System"])
def health():
    return {
        "service": "agent_service",
        "status": "healthy",
        "port": 8001,
        "model": settings.openai_model
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_assistant(
    payload: ChatRequest,
    request: Request,
):
    """
    Handles chat messages from the frontend assistant panel.
    Combines user context (from headers) and web context (from body) into RunnableConfig.
    The LangChain agent handles all intent reasoning, follow-up questions, and verification.
    """
    user_ctx = extract_user_context(request)
    web_ctx = payload.web_context or WebContext()
    thread_id = payload.thread_id or f"session_{user_ctx.user_id}"

    runnable_config = context_to_runnable_config(user_ctx, web_ctx, thread_id=thread_id)

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config=runnable_config
        )
    except Exception as exc:
        err_msg = str(exc)
        if "content management policy" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request filtered by safety policy. Please rephrase."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {err_msg}"
        )

    messages = result.get("messages", [])
    final_response = "I processed your request."
    tool_records: Dict[str, ToolExecutionRecord] = {}
    action = None
    verification_data = None

    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_records[tc["id"]] = ToolExecutionRecord(
                    tool_name=tc["name"],
                    args=tc["args"],
                )
                # LangChain Agent explicitly indicates state via tool choice:
                if tc["name"] == "ask_user_verification":
                    action = "verification_required"
                    verification_data = tc["args"]
                elif tc["name"] == "submit_service_request":
                    action = "form_submitted"
                    verification_data = tc["args"]

        elif isinstance(msg, ToolMessage):
            t_id = getattr(msg, "tool_call_id", "")
            if t_id in tool_records:
                tool_records[t_id].output = msg.content

        elif isinstance(msg, AIMessage) and msg.content:
            final_response = msg.content

    return ChatResponse(
        response=final_response,
        user_context=user_ctx,
        web_context=web_ctx,
        thread_id=thread_id,
        tool_calls=list(tool_records.values()),
        action=action,
        verification_data=verification_data,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
