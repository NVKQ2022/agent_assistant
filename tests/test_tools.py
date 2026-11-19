import pytest
from app.context import UserContext, context_to_runnable_config
from app.tools import (
    get_my_profile,
    get_my_orders,
    perform_admin_action,
    search_tenant_documents,
    call_external_service,
)


def test_get_my_profile():
    ctx = UserContext(user_id="alice", role="user", tenant_id="acme-corp", locale="en-US")
    config = context_to_runnable_config(ctx)
    result = get_my_profile.invoke({}, config=config)

    assert "Alice Wonderland" in result
    assert "alice@acme.com" in result
    assert "Enterprise Gold" in result
    assert "Balance: $1540.50" in result


def test_orders_tenant_and_user_isolation():
    # Alice orders
    alice_ctx = UserContext(user_id="alice", role="user", tenant_id="acme-corp")
    alice_res = get_my_orders.invoke({}, config=context_to_runnable_config(alice_ctx))
    assert "ORD-1001" in alice_res
    assert "MacBook Pro M3" in alice_res
    assert "ORD-2001" not in alice_res  # Bob's order must NOT appear

    # Bob orders
    bob_ctx = UserContext(user_id="bob", role="user", tenant_id="beta-org")
    bob_res = get_my_orders.invoke({}, config=context_to_runnable_config(bob_ctx))
    assert "ORD-2001" in bob_res
    assert "Mechanical Keyboard" in bob_res
    assert "ORD-1001" not in bob_res  # Alice's order must NOT appear


def test_rbac_admin_action_denial_and_grant():
    # Regular user attempting admin action
    user_ctx = UserContext(user_id="mallory", role="user", tenant_id="acme-corp")
    denial = perform_admin_action.invoke(
        {"action": "reset_password", "target_user": "victim_alice"},
        config=context_to_runnable_config(user_ctx),
    )
    assert "[PERMISSION DENIED]" in denial
    assert "Requires role: 'admin'" in denial

    # Admin user executing admin action
    admin_ctx = UserContext(user_id="charlie_admin", role="admin", tenant_id="internal")
    success = perform_admin_action.invoke(
        {"action": "reset_password", "target_user": "victim_alice"},
        config=context_to_runnable_config(admin_ctx),
    )
    assert "[ADMIN ACTION SUCCESSFUL]" in success
    assert "Admin 'charlie_admin'" in success


def test_tenant_documents_isolation():
    # ACME tenant
    acme_ctx = UserContext(user_id="emp1", role="user", tenant_id="acme-corp")
    acme_docs = search_tenant_documents.invoke({"query": "policy"}, config=context_to_runnable_config(acme_ctx))
    assert "ACME Security Policy" in acme_docs
    assert "Beta Corp Guidelines" not in acme_docs

    # Beta tenant
    beta_ctx = UserContext(user_id="emp2", role="user", tenant_id="beta-org")
    beta_docs = search_tenant_documents.invoke({"query": "guideline"}, config=context_to_runnable_config(beta_ctx))
    assert "Beta Corp Guidelines" in beta_docs
    assert "ACME Security Policy" not in beta_docs


def test_call_external_service_token_forwarding():
    ctx = UserContext(
        user_id="alice",
        role="user",
        tenant_id="acme-corp",
        auth_token="jwt_secret_token_xyz_12345",
    )
    res = call_external_service.invoke(
        {"service_name": "billing-service", "payload_summary": "fetch_invoices"},
        config=context_to_runnable_config(ctx),
    )
    assert "Caller: alice" in res
    assert "Forwarded Auth Token: jwt_secret..." in res
    assert "200 OK" in res
