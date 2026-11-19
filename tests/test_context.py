import pytest
from fastapi import Request
from starlette.datastructures import Headers
from unittest.mock import AsyncMock

from app.context import (
    UserContext,
    get_user_context,
    context_to_runnable_config,
    get_user_context_from_config,
)


def make_mock_request(headers_dict, client_host="192.168.1.100"):
    scope = {
        "type": "http",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers_dict.items()],
        "client": (client_host, 12345),
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_extract_user_context_from_headers():
    headers = {
        "x-user-id": "alice",
        "x-username": "Alice Wonderland",
        "x-user-role": "admin",
        "x-tenant-id": "acme-corp",
        "x-user-email": "alice@acme.com",
        "accept-language": "fr-FR,en;q=0.9",
        "user-agent": "Mozilla/5.0 AgentTester",
    }
    request = make_mock_request(headers)
    ctx = await get_user_context(request)

    assert ctx.user_id == "alice"
    assert ctx.username == "Alice Wonderland"
    assert ctx.role == "admin"
    assert ctx.tenant_id == "acme-corp"
    assert ctx.email == "alice@acme.com"
    assert ctx.locale == "fr-FR"
    assert ctx.client_ip == "192.168.1.100"
    assert ctx.user_agent == "Mozilla/5.0 AgentTester"


@pytest.mark.asyncio
async def test_extract_from_bearer_jwt():
    # Simulated JWT payload: {"sub": "jwt_user_42", "role": "manager", "tenant_id": "jwt_tenant"}
    import base64
    import json
    payload = json.dumps({"sub": "jwt_user_42", "role": "manager", "tenant_id": "jwt_tenant"})
    b64_payload = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    dummy_jwt = f"header.{b64_payload}.signature"

    headers = {"authorization": f"Bearer {dummy_jwt}"}
    request = make_mock_request(headers)
    ctx = await get_user_context(request)

    assert ctx.user_id == "jwt_user_42"
    assert ctx.role == "manager"
    assert ctx.tenant_id == "jwt_tenant"
    assert ctx.auth_token == dummy_jwt


def test_context_to_runnable_config_roundtrip():
    ctx = UserContext(
        user_id="charlie",
        role="admin",
        tenant_id="internal",
        locale="en-GB",
        auth_token="secret_token_123",
    )
    config = context_to_runnable_config(ctx, thread_id="test_thread_99")

    # Verify structure in configurable
    configurable = config["configurable"]
    assert configurable["user_id"] == "charlie"
    assert configurable["role"] == "admin"
    assert configurable["tenant_id"] == "internal"
    assert configurable["thread_id"] == "test_thread_99"

    # Verify tool helper can extract context accurately
    recovered = get_user_context_from_config(config)
    assert recovered.user_id == "charlie"
    assert recovered.role == "admin"
    assert recovered.tenant_id == "internal"
    assert recovered.auth_token == "secret_token_123"
