# Prototype Documentation: Context-Aware Agent Assistant

Welcome to the technical documentation for the **Context-Aware Enterprise Agent Assistant** prototype built with **LangChain**, **FastAPI**, and modern web technologies.

---

## 📚 Documentation Index

| Document | Description |
| :--- | :--- |
| **[1. System Architecture](architecture.md)** | Full 3-tier architecture breakdown (Frontend, Backend, Agent Service), sequence diagrams, and cross-service communication. |
| **[2. Context Injection & Security](context-injection-security.md)** | Deep dive into how user identity (`UserContext`) and web state (`WebContext`) are securely injected into tools via LangChain's `RunnableConfig` without prompt-injection risks. |
| **[3. Agent Workflow & HITL](agent-workflow-and-hitl.md)** | Multi-turn memory (`MemorySaver`), follow-up questioning, and the native Human-in-the-Loop verification tool workflow (zero regex). |
| **[4. API Reference](api-reference.md)** | Complete endpoint specifications, headers, payloads, and response structures for the Backend and Agent Assistant services. |
| **[5. Getting Started Guide](getting-started.md)** | Step-by-step instructions for local installation, environment configuration, launching the services, and testing. |

---

## 🎯 Executive Summary

In enterprise environments, AI agents that interact with business workflows (such as IT equipment requests, permissions, or customer tickets) face two critical challenges:
1. **Identity & Authorization Security**: Asking the LLM to supply user IDs or roles creates severe prompt-injection vulnerabilities where users can spoof identity.
2. **Autonomous Premature Execution**: Autonomous agents must not trigger irreversible actions without human verification, and must ask clarifying follow-up questions when information is incomplete.

### The Solution Demonstrated in This Prototype
- **Runtime Context Injection**: HTTP request headers (`X-User-Id`, `X-User-Department`, etc.) and web context (live form drafts) are parsed by the web layer and injected out-of-band into LangChain's `RunnableConfig`. The LLM's tool calling schema never exposes identity parameters.
- **Native Human-in-the-Loop Protocol**: The LangChain Agent uses dedicated tools (`ask_user_verification` and `submit_service_request`) to gather details, present a review summary, and only execute after explicit confirmation, without any regular expressions or string-parsing heuristics.
- **Clean 3-Tier Separation**:
  - `frontend/`: Web UI on Port 3000 with interactive form, user persona switcher, and Copilot chat panel.
  - `backend/`: FastAPI service on Port 8002 handling form submissions, user profiles, and database records.
  - `agent_service/`: FastAPI + LangChain service on Port 8001 orchestrating the context-aware AI agent.
