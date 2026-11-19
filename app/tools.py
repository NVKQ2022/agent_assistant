from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.context import get_user_context_from_config, UserContext


# Mock Database partitioned by tenant and user
MOCK_USERS_DB: Dict[str, Dict[str, Any]] = {
    "alice": {
        "full_name": "Alice Wonderland",
        "email": "alice@acme.com",
        "tier": "Enterprise Gold",
        "balance_usd": 1540.50,
        "preferences": {"notifications": True, "currency": "USD"},
    },
    "bob": {
        "full_name": "Bob Builder",
        "email": "bob@beta.org",
        "tier": "Standard",
        "balance_usd": 85.00,
        "preferences": {"notifications": False, "currency": "EUR"},
    },
    "charlie_admin": {
        "full_name": "Charlie Administrator",
        "email": "charlie@corp.internal",
        "tier": "Super Admin",
        "balance_usd": 99999.00,
        "preferences": {"notifications": True, "currency": "USD"},
    },
}

MOCK_ORDERS_DB: List[Dict[str, Any]] = [
    {"order_id": "ORD-1001", "user_id": "alice", "tenant_id": "acme-corp", "item": "MacBook Pro M3", "amount": 2499.00, "status": "shipped"},
    {"order_id": "ORD-1002", "user_id": "alice", "tenant_id": "acme-corp", "item": "USB-C Hub", "amount": 49.99, "status": "delivered"},
    {"order_id": "ORD-2001", "user_id": "bob", "tenant_id": "beta-org", "item": "Mechanical Keyboard", "amount": 120.00, "status": "processing"},
    {"order_id": "ORD-2002", "user_id": "bob", "tenant_id": "beta-org", "item": "Ergonomic Mouse", "amount": 75.50, "status": "delivered"},
    {"order_id": "ORD-3001", "user_id": "charlie_admin", "tenant_id": "internal", "item": "Server Rack Unit", "amount": 4500.00, "status": "delivered"},
]

MOCK_TENANT_DOCS: Dict[str, List[str]] = {
    "acme-corp": [
        "ACME Security Policy: All external devices require MDM enrollment.",
        "ACME Q3 Roadmap: Migration to Kubernetes cluster in us-east-1.",
    ],
    "beta-org": [
        "Beta Corp Guidelines: Remote work core hours are 10am-4pm GMT.",
        "Beta Product Specs: Version 2.0 release planned for December.",
    ],
}


@tool
def get_my_profile(config: RunnableConfig) -> str:
    """
    Retrieve the account profile, balance, and preferences for the currently authenticated user.
    Note: The user identity is securely obtained from the request context, not from user prompts.
    """
    user_context = get_user_context_from_config(config)
    uid = user_context.user_id.lower()
    
    profile = MOCK_USERS_DB.get(uid, {
        "full_name": user_context.username or uid,
        "email": user_context.email or f"{uid}@{user_context.tenant_id}.com",
        "tier": "Standard Free",
        "balance_usd": 0.00,
        "preferences": {"notifications": True, "currency": "USD"},
    })
    
    return (
        f"[User Profile Context]\n"
        f"- User ID: {user_context.user_id}\n"
        f"- Name: {profile['full_name']}\n"
        f"- Role: {user_context.role}\n"
        f"- Tenant: {user_context.tenant_id}\n"
        f"- Email: {profile['email']}\n"
        f"- Tier: {profile['tier']}\n"
        f"- Balance: ${profile['balance_usd']:.2f}\n"
        f"- Preferred Locale: {user_context.locale}"
    )


@tool
def get_my_orders(status_filter: Optional[str] = None, limit: int = 5, config: RunnableConfig = None) -> str:
    """
    Fetch the order history belonging strictly to the currently authenticated user.
    Optionally filter by status (e.g. 'shipped', 'delivered', 'processing').
    """
    user_context = get_user_context_from_config(config)
    uid = user_context.user_id.lower()
    tenant = user_context.tenant_id.lower()

    # Query strictly partitioned by user_id and tenant_id
    user_orders = [
        o for o in MOCK_ORDERS_DB 
        if o["user_id"].lower() == uid and (o["tenant_id"].lower() == tenant or tenant == "default_org")
    ]
    
    if status_filter:
        user_orders = [o for o in user_orders if o["status"].lower() == status_filter.lower()]
        
    user_orders = user_orders[:limit]
    
    if not user_orders:
        return f"No orders found for user '{user_context.user_id}' in tenant '{user_context.tenant_id}'."

    lines = [f"Found {len(user_orders)} order(s) for user '{user_context.user_id}' (Tenant: {user_context.tenant_id}):"]
    for o in user_orders:
        lines.append(f"- Order #{o['order_id']}: {o['item']} - ${o['amount']:.2f} [Status: {o['status'].upper()}]")
    return "\n".join(lines)


@tool
def perform_admin_action(action: str, target_user: str, config: RunnableConfig) -> str:
    """
    Execute a privileged administrative operation (e.g. 'reset_password', 'grant_access', 'suspend_user').
    Restricted: Only users with the 'admin' role in their request context are authorized.
    """
    user_context = get_user_context_from_config(config)
    
    # Enforce Role-Based Access Control (RBAC)
    if user_context.role.lower() != "admin":
        return (
            f"[PERMISSION DENIED]\n"
            f"User '{user_context.user_id}' with role '{user_context.role}' is NOT authorized to execute admin action '{action}'. "
            f"Requires role: 'admin'."
        )

    return (
        f"[ADMIN ACTION SUCCESSFUL]\n"
        f"Admin '{user_context.user_id}' (Tenant: {user_context.tenant_id}) successfully performed '{action}' on target '{target_user}'. "
        f"Audit log recorded from IP: {user_context.client_ip or 'unknown'}."
    )


@tool
def search_tenant_documents(query: str, config: RunnableConfig) -> str:
    """
    Search internal company documents and knowledge base strictly scoped to the user's organization tenant.
    """
    user_context = get_user_context_from_config(config)
    tenant = user_context.tenant_id.lower()
    
    docs = MOCK_TENANT_DOCS.get(tenant, [])
    matching = [d for d in docs if any(word.lower() in d.lower() for word in query.split())]
    
    if not matching and docs:
        matching = docs  # Return all tenant docs if query is general
        
    if not matching:
        return f"No internal documentation found for tenant '{user_context.tenant_id}' matching '{query}'."

    return (
        f"[Knowledge Base for Tenant: {user_context.tenant_id}]\n" +
        "\n".join(f"- {d}" for d in matching)
    )


@tool
def call_external_service(service_name: str, payload_summary: str, config: RunnableConfig) -> str:
    """
    Simulates making a call to a downstream microservice on behalf of the user,
    forwarding the authenticated user's bearer token and headers for delegation.
    """
    user_context = get_user_context_from_config(config)
    has_token = bool(user_context.auth_token)
    token_preview = f"{user_context.auth_token[:10]}..." if has_token else "NONE (Using user session headers)"

    return (
        f"[Delegated Call to '{service_name}']\n"
        f"- Caller: {user_context.user_id} ({user_context.role})\n"
        f"- Tenant: {user_context.tenant_id}\n"
        f"- Forwarded Auth Token: {token_preview}\n"
        f"- Payload: {payload_summary}\n"
        f"- Status: 200 OK (Downstream service verified caller identity)"
    )


# All available tools for the agent assistant
ALL_TOOLS = [
    get_my_profile,
    get_my_orders,
    perform_admin_action,
    search_tenant_documents,
    call_external_service,
]
