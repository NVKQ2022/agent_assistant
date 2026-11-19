#!/usr/bin/env python3
"""
End-to-End Test and Demonstration Script for 3-Tier Agent Architecture:
Demonstrating:
1. Follow-up questioning when user information is incomplete.
2. Mandatory pre-submission verification (Human-in-the-loop).
3. Tool execution only upon explicit user confirmation.
4. Strict multi-user tenant and data isolation.
"""

import multiprocessing
import time
import httpx
import uvicorn

from backend.main import app as backend_app
from agent_service.main import app as agent_app


def start_backend():
    uvicorn.run(backend_app, host="127.0.0.1", port=8002, log_level="warning")


def start_agent():
    uvicorn.run(agent_app, host="127.0.0.1", port=8001, log_level="warning")


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def main():
    print_banner("STARTING 3-TIER ARCHITECTURE DEMO: FOLLOW-UPS & HUMAN VERIFICATION")
    print(">> Launching Backend Service on http://127.0.0.1:8002...")
    backend_proc = multiprocessing.Process(target=start_backend, daemon=True)
    backend_proc.start()

    print(">> Launching Agent Assistant Service on http://127.0.0.1:8001...")
    agent_proc = multiprocessing.Process(target=start_agent, daemon=True)
    agent_proc.start()

    time.sleep(2.0)
    client = httpx.Client(timeout=20.0)

    try:
        # Check health
        backend_health = client.get("http://127.0.0.1:8002/health").json()
        agent_health = client.get("http://127.0.0.1:8001/health").json()
        print(f"✅ Backend Service: {backend_health}")
        print(f"✅ Agent Assistant Service: {agent_health}")

        # ------------------------------------------------------------------
        # SCENARIO 1: Multi-Turn Conversation (Follow-Up & Mandatory Verification)
        # ------------------------------------------------------------------
        print_banner("SCENARIO 1: Alice Requests Equipment (Follow-up & Verification Flow)")
        thread_id = f"test_alice_{int(time.time())}"
        alice_headers = {
            "X-User-Id": "alice",
            "X-User-Name": "Alice Wonderland",
            "X-User-Department": "Engineering",
            "X-User-Role": "Senior Developer",
        }
        alice_web_context = {
            "current_url": "http://localhost:3000/portal/requests",
            "page_title": "IT Equipment & Service Request Portal",
            "active_form": "service_request_form",
            "draft_form_data": {},
        }

        # --- Turn 1: Vague initial request ---
        prompt_turn1 = "I need a new monitor for my desk."
        print(f"\n[Turn 1] Alice Prompt: \"{prompt_turn1}\"")
        res1 = client.post(
            "http://127.0.0.1:8001/chat",
            headers=alice_headers,
            json={"message": prompt_turn1, "web_context": alice_web_context, "thread_id": thread_id},
        ).json()

        print("==> Assistant Response (Follow-up Question):")
        print(res1["response"])
        # Verify the agent DID NOT submit the request prematurely
        submit_tools_turn1 = [t for t in res1["tool_calls"] if t["tool_name"] == "submit_service_request"]
        assert len(submit_tools_turn1) == 0, "Security error: Agent submitted before gathering required details!"
        print("✅ Verified: Agent paused to ask follow-up questions instead of submitting blindly.")

        # --- Turn 2: Providing details -> Agent summarizes & asks for confirmation ---
        prompt_turn2 = "It should be 32-inch 4K with USB-C. My current screen flickers and disrupts my coding. Priority is Medium."
        print(f"\n[Turn 2] Alice Prompt: \"{prompt_turn2}\"")
        res2 = client.post(
            "http://127.0.0.1:8001/chat",
            headers=alice_headers,
            json={"message": prompt_turn2, "web_context": alice_web_context, "thread_id": thread_id},
        ).json()

        print("==> Assistant Response (Summary & Verification Request):")
        print(res2["response"])
        print(f"==> Agent Action Dispatched: {res2.get('action')}")
        print(f"==> Verification Data Extracted by Agent: {res2.get('verification_data')}")

        # Verify the LangChain Agent invoked the ask_user_verification tool
        verification_tools = [t for t in res2["tool_calls"] if t["tool_name"] == "ask_user_verification"]
        assert len(verification_tools) > 0, "Agent failed to call ask_user_verification tool!"
        assert res2.get("action") == "verification_required", "Agent action must be 'verification_required'!"
        # Verify submit was NOT called prematurely
        submit_tools_turn2 = [t for t in res2["tool_calls"] if t["tool_name"] == "submit_service_request"]
        assert len(submit_tools_turn2) == 0, "Security error: Agent submitted without explicit user confirmation!"
        print("✅ Verified: LangChain Agent called 'ask_user_verification' tool; did NOT call submit tool.")

        # --- Turn 3: User confirms -> Agent executes submission tool ---
        prompt_turn3 = "Yes, please submit it now!"
        print(f"\n[Turn 3] Alice Confirmation: \"{prompt_turn3}\"")
        res3 = client.post(
            "http://127.0.0.1:8001/chat",
            headers=alice_headers,
            json={"message": prompt_turn3, "web_context": alice_web_context, "thread_id": thread_id},
        ).json()

        print("==> Assistant Final Response (Execution Confirmation):")
        print(res3["response"])
        print(f"==> Agent Action Dispatched: {res3.get('action')}")
        submit_tools_turn3 = [t for t in res3["tool_calls"] if t["tool_name"] == "submit_service_request"]
        assert len(submit_tools_turn3) > 0, "Agent failed to call submit_service_request upon confirmation!"
        assert res3.get("action") == "form_submitted", "Agent action must be 'form_submitted'!"
        print("✅ Verified: LangChain Agent officially invoked 'submit_service_request' upon user confirmation.")

        # --- Verify Backend Database ---
        print("\n>> [Backend Verification]: Checking database for Alice's tickets...")
        db_res = client.get("http://127.0.0.1:8002/api/requests", headers={"X-User-Id": "alice"}).json()
        print(f"   Alice's tickets in Backend ({len(db_res)} total):")
        for t in db_res:
            print(f"   • {t['id']}: [{t['category']}] {t['description']} (Submitted via: {t['submitted_via']})")

        # ------------------------------------------------------------------
        # SCENARIO 2: Bob Queries Active Requests (Data Isolation)
        # ------------------------------------------------------------------
        print_banner("SCENARIO 2: Bob (Sales) Checks Requests (Isolation Test)")
        bob_thread = f"test_bob_{int(time.time())}"
        bob_headers = {
            "X-User-Id": "bob",
            "X-User-Name": "Bob Builder",
            "X-User-Department": "Sales & Accounts",
            "X-User-Role": "Account Executive",
        }
        bob_prompt = "What are my active requests?"
        print(f">> Bob Prompt: \"{bob_prompt}\"")
        bob_chat = client.post(
            "http://127.0.0.1:8001/chat",
            headers=bob_headers,
            json={"message": bob_prompt, "thread_id": bob_thread},
        ).json()
        print("==> Assistant Response to Bob:")
        print(bob_chat["response"])
        assert "4K" not in bob_chat["response"], "Data leak: Alice's monitor request was leaked to Bob!"
        print("✅ Verified: Bob cannot see Alice's requests.")

        print_banner("ALL MULTI-TURN VERIFICATION TESTS PASSED SUCCESSFULLY!")

    finally:
        print("\nShutting down demo processes...")
        backend_proc.terminate()
        agent_proc.terminate()
        backend_proc.join(timeout=2)
        agent_proc.join(timeout=2)


if __name__ == "__main__":
    main()
