from typing import Any, List, Optional, Sequence, Union
import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.config import settings
from app.tools import ALL_TOOLS


SYSTEM_PROMPT = """You are an Enterprise AI Assistant.
You assist authenticated users with their profiles, order records, organization documents, and system operations.

CRITICAL SECURITY RULES:
1. User identity, tenant isolation, and access roles are securely supplied by the platform runtime environment.
2. When calling tools that operate on the user's data (e.g. get_my_profile, get_my_orders, perform_admin_action), the runtime automatically injects the authenticated caller's context. You do NOT supply user IDs or roles.
3. If a tool reports [PERMISSION DENIED] due to RBAC roles, politely inform the user that their current role does not have authorization for that action.
4. Never assume or spoof credentials.
"""


class SmartMockChatModel(BaseChatModel):
    """
    Intelligent mock chat model for standalone local execution, tests, and demo without requiring an external paid LLM API key.
    Inspects user prompt semantics, simulates realistic tool calls, and synthesizes tool outputs.
    """
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        # 1. If the previous message was a ToolMessage, summarize/respond with tool findings
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        if tool_messages and isinstance(messages[-1], ToolMessage):
            last_tool = messages[-1]
            response_text = (
                f"I processed your request using the verified system credentials.\n\n"
                f"{last_tool.content}"
            )
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

        # 2. Extract user input
        user_text = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_text = m.content.lower()
                break

        # 3. Simulate tool calling decision based on user intent
        if any(w in user_text for w in ["order", "purchase", "bought", "buy", "history", "item"]):
            # Extract optional status filter
            status = None
            if "shipped" in user_text:
                status = "shipped"
            elif "delivered" in user_text:
                status = "delivered"
            elif "processing" in user_text:
                status = "processing"
            args = {"status_filter": status} if status else {}
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(
                    content="",
                    tool_calls=[{"name": "get_my_orders", "args": args, "id": "call_orders_1", "type": "tool_call"}]
                )
            )])
            
        elif any(w in user_text for w in ["profile", "who am i", "balance", "account", "tier"]):
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(
                    content="",
                    tool_calls=[{"name": "get_my_profile", "args": {}, "id": "call_profile_1", "type": "tool_call"}]
                )
            )])
            
        elif any(w in user_text for w in ["admin", "reset password", "grant access", "suspend", "delete"]):
            action = "reset_password" if "password" in user_text else ("grant_access" if "grant" in user_text else "admin_operation")
            target = "target_user_xyz"
            for word in user_text.split():
                if word.startswith("user_") or word in ["dave", "john", "alice", "bob"]:
                    target = word
                    break
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(
                    content="",
                    tool_calls=[{"name": "perform_admin_action", "args": {"action": action, "target_user": target}, "id": "call_admin_1", "type": "tool_call"}]
                )
            )])

        elif any(w in user_text for w in ["doc", "document", "policy", "guideline", "roadmap", "spec"]):
            query = user_text.replace("search", "").replace("document", "").strip() or "policy"
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(
                    content="",
                    tool_calls=[{"name": "search_tenant_documents", "args": {"query": query}, "id": "call_docs_1", "type": "tool_call"}]
                )
            )])

        elif any(w in user_text for w in ["service", "external", "delegate", "forward", "sync"]):
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(
                    content="",
                    tool_calls=[{"name": "call_external_service", "args": {"service_name": "billing-microservice", "payload_summary": "sync customer ledger"}, "id": "call_ext_1", "type": "tool_call"}]
                )
            )])

        # Default conversational reply if no tools required
        return ChatResult(generations=[ChatGeneration(
            message=AIMessage(
                content=(
                    "Hello! I am your Enterprise Agent Assistant. I have secure access to your user session.\n\n"
                    "You can ask me to:\n"
                    "1. Check your account profile and balance ('Show my profile')\n"
                    "2. View your order history ('List my orders')\n"
                    "3. Query organization documents ('Find company security policies')\n"
                    "4. Perform administrative tasks ('Reset password for user_dave' - requires admin role)\n"
                    "5. Delegate to external microservices with your token ('Call billing microservice')"
                )
            )
        )])

    @property
    def _llm_type(self) -> str:
        return "smart-mock-chat-model"

    def bind_tools(self, tools: Sequence[Union[dict, Any]], **kwargs: Any) -> Any:
        return self


def get_llm() -> BaseChatModel:
    """
    Returns configured LLM:
    - Uses OpenAI (or OpenAI-compatible API such as Ollama / vLLM) if OPENAI_API_KEY is configured.
    - Otherwise falls back to SmartMockChatModel so the prototype runs out-of-the-box.
    """
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if api_key:
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=api_key,
            base_url=settings.openai_base_url,
            temperature=0.0,
        )
    return SmartMockChatModel()


def build_agent(llm: Optional[BaseChatModel] = None):
    """
    Constructs the LangChain agent graph with injected system prompt and tools.
    """
    model = llm or get_llm()
    return create_agent(
        model=model,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


# Pre-built agent instance
agent = build_agent()
