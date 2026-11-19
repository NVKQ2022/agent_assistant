from typing import Any, Dict, Optional, Tuple
from fastapi import Request
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig


class UserContext(BaseModel):
    user_id: str = Field(..., description="Unique employee identifier")
    name: Optional[str] = Field(default=None, description="Employee display name")
    email: Optional[str] = Field(default=None, description="Employee email")
    department: Optional[str] = Field(default="General", description="Department or business unit")
    role: str = Field(default="Employee", description="User role")
    tenant_id: str = Field(default="default_tenant", description="Workspace tenant ID")


class WebContext(BaseModel):
    current_url: Optional[str] = Field(default="http://localhost:3000/portal/requests", description="Active web page URL")
    page_title: Optional[str] = Field(default="IT & Service Request Portal", description="Web page title")
    active_form: Optional[str] = Field(default="service_request_form", description="Identifier of the active form")
    draft_form_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Form field values currently entered by the user in the browser"
    )


def extract_user_context(request: Request) -> UserContext:
    headers = request.headers
    user_id = headers.get("x-user-id") or "alice"
    role = headers.get("x-user-role") or "Employee"
    tenant_id = headers.get("x-tenant-id") or "default_tenant"
    name = headers.get("x-user-name") or (user_id.capitalize())
    email = headers.get("x-user-email") or f"{user_id}@company.com"
    department = headers.get("x-user-department") or "Engineering"

    return UserContext(
        user_id=user_id,
        name=name,
        email=email,
        department=department,
        role=role,
        tenant_id=tenant_id
    )


def context_to_runnable_config(user_ctx: UserContext, web_ctx: WebContext, thread_id: Optional[str] = None) -> RunnableConfig:
    """Pack user and web contexts into LangChain RunnableConfig."""
    configurable: Dict[str, Any] = {
        "user_context": user_ctx.model_dump(),
        "web_context": web_ctx.model_dump(),
        "user_id": user_ctx.user_id,
        "tenant_id": user_ctx.tenant_id,
    }
    if thread_id:
        configurable["thread_id"] = thread_id

    return RunnableConfig(configurable=configurable)


def get_contexts_from_config(config: Optional[RunnableConfig]) -> Tuple[UserContext, WebContext]:
    """Retrieve strongly-typed UserContext and WebContext from inside any tool."""
    if not config:
        raise ValueError("No RunnableConfig provided to tool.")
    
    configurable = config.get("configurable", {})
    user_data = configurable.get("user_context", {"user_id": configurable.get("user_id", "alice")})
    web_data = configurable.get("web_context", {})

    return UserContext(**user_data), WebContext(**web_data)
