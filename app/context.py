from typing import Any, Dict, Optional
import json
import base64
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig


class UserContext(BaseModel):
    """
    Structured context extracted from incoming web request headers and metadata.
    This context is injected securely into the LangChain execution environment
    so tools can access it without exposing it to prompt-injection tampering.
    """
    user_id: str = Field(description="Unique identifier of the authenticated user")
    username: Optional[str] = Field(default=None, description="Display name or username")
    email: Optional[str] = Field(default=None, description="User email address")
    role: str = Field(default="user", description="User role, e.g. user, admin, manager, auditor")
    tenant_id: str = Field(default="default", description="Organization or workspace tenant ID")
    auth_token: Optional[str] = Field(default=None, description="Raw Bearer token for downstream API delegation")
    session_id: Optional[str] = Field(default=None, description="Web session or conversation thread ID")
    locale: Optional[str] = Field(default="en-US", description="User preferred locale from Accept-Language")
    client_ip: Optional[str] = Field(default=None, description="Client remote IP address")
    user_agent: Optional[str] = Field(default=None, description="Client User-Agent header")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary tenant/user metadata")


def _decode_jwt_payload_unverified(token: str) -> Dict[str, Any]:
    """
    Helper to extract claims from JWT without signature verification (for demo/prototype).
    In production, a proper JWT verifier library like PyJWT with secret/public key would verify it.
    """
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            padding = "=" * (4 - (len(parts[1]) % 4))
            decoded = base64.urlsafe_b64decode(parts[1] + padding).decode("utf-8")
            return json.loads(decoded)
    except Exception:
        pass
    return {}


async def get_user_context(request: Request) -> UserContext:
    """
    FastAPI Dependency to extract and validate user context from HTTP headers.
    
    Supported headers:
      - X-User-Id / User-Id: user identifier
      - X-User-Role / Role: user role (admin, user, etc.)
      - X-Tenant-Id / Tenant-Id: multi-tenant organization ID
      - X-Username: user display name
      - X-User-Email: user email
      - X-Session-Id: session identifier
      - Authorization: Bearer <token> (parsed for sub, role, tenant if headers absent)
      - Accept-Language: user locale
    """
    headers = request.headers
    
    # 1. Check for Authorization header (Bearer token)
    auth_header = headers.get("authorization", "")
    token = None
    jwt_claims = {}
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        jwt_claims = _decode_jwt_payload_unverified(token)
    
    # 2. Extract user identity with fallback priority:
    #    Explicit header -> JWT claim -> query parameter -> default/rejection
    user_id = (
        headers.get("x-user-id")
        or headers.get("user-id")
        or jwt_claims.get("sub")
        or jwt_claims.get("user_id")
        or request.query_params.get("user_id")
    )
    
    if not user_id:
        from app.config import settings
        if settings.allow_anonymous:
            user_id = "anonymous_guest"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication context missing. Please provide 'X-User-Id' header or a valid 'Authorization: Bearer <token>' header."
            )

    # 3. Extract tenant / organization ID
    tenant_id = (
        headers.get("x-tenant-id")
        or headers.get("tenant-id")
        or jwt_claims.get("tenant_id")
        or jwt_claims.get("org_id")
        or "default_org"
    )

    # 4. Extract role (e.g. user, admin, manager)
    role = (
        headers.get("x-user-role")
        or headers.get("role")
        or jwt_claims.get("role")
        or "user"
    )

    # 5. Extract metadata & web context
    username = (
        headers.get("x-username")
        or jwt_claims.get("name")
        or jwt_claims.get("preferred_username")
        or user_id
    )
    email = headers.get("x-user-email") or jwt_claims.get("email")
    session_id = headers.get("x-session-id") or request.query_params.get("session_id")
    locale = headers.get("accept-language", "en-US").split(",")[0].strip()
    
    # Web context (client IP, User Agent)
    forwarded_for = headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else None)
    user_agent = headers.get("user-agent")

    return UserContext(
        user_id=user_id,
        username=username,
        email=email,
        role=role.lower(),
        tenant_id=tenant_id,
        auth_token=token,
        session_id=session_id,
        locale=locale,
        client_ip=client_ip,
        user_agent=user_agent,
    )


def context_to_runnable_config(context: UserContext, thread_id: Optional[str] = None) -> RunnableConfig:
    """
    Converts a UserContext into a LangChain RunnableConfig.
    The context is placed inside `configurable`, making it accessible to all tools
    while remaining completely invisible to the LLM's tool calling arguments schema.
    """
    configurable: Dict[str, Any] = {
        "user_context": context.model_dump(),
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "role": context.role,
        "locale": context.locale,
        "auth_token": context.auth_token,
    }
    
    if thread_id or context.session_id:
        configurable["thread_id"] = thread_id or context.session_id

    return RunnableConfig(configurable=configurable)


def get_user_context_from_config(config: Optional[RunnableConfig]) -> UserContext:
    """
    Helper for LangChain tools to extract the strongly-typed UserContext from RunnableConfig.
    Raises ValueError if context is missing, ensuring tools are never called unauthenticated.
    """
    if not config:
        raise ValueError("Security violation: Tool called without RunnableConfig execution context.")
    
    configurable = config.get("configurable", {})
    raw_ctx = configurable.get("user_context")
    
    if isinstance(raw_ctx, UserContext):
        return raw_ctx
    elif isinstance(raw_ctx, dict):
        return UserContext(**raw_ctx)
    elif "user_id" in configurable:
        return UserContext(
            user_id=configurable["user_id"],
            tenant_id=configurable.get("tenant_id", "default_org"),
            role=configurable.get("role", "user"),
            auth_token=configurable.get("auth_token"),
            locale=configurable.get("locale", "en-US"),
        )
    
    raise ValueError("Security violation: Tool execution requires an authenticated UserContext in config['configurable'].")
