# System Architecture

This document describes the 3-tier microservice architecture of the Context-Aware Enterprise Agent Assistant prototype.

---

## 🏛️ High-Level Component Architecture

The prototype is organized into three independent services located in dedicated root folders:

```
agent_assistant/
├── frontend/               # Service 1: Web UI (Port 3000)
│   ├── index.html          # Form fields, User Persona switcher, Chat Copilot
│   ├── style.css           # Responsive enterprise UI styling
│   ├── app.js              # State manager & API client
│   └── server.py           # Lightweight static web server
│
├── backend/                # Service 2: Core Business Backend (Port 8002)
│   ├── main.py             # FastAPI REST endpoints (/api/requests, /api/me)
│   └── models.py           # Pydantic data schemas
│
└── agent_service/          # Service 3: LangChain Agent Assistant (Port 8001)
    ├── main.py             # FastAPI chat endpoint (/chat)
    ├── agent.py            # LangChain agent graph & system instructions
    ├── tools.py            # Injected-context tools
    ├── context.py          # UserContext & WebContext extractors
    └── config.py           # Azure OpenAI settings & Backend URL
```

---

## 🔁 End-to-End Sequence Diagram

The diagram below illustrates how user context from HTTP headers and web context from the browser flow through the system:

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant FE as Frontend UI (Port 3000)
    participant Agent as Agent Service (Port 8001)
    participant BE as Backend API (Port 8002)

    Note over User,FE: User selects persona (Alice, Engineering)
    User->>FE: Types: "I need a 4K monitor because mine is flickering"
    FE->>Agent: POST /chat (Headers: X-User-Id=alice; Body: message + live web_context)
    
    Note over Agent: Step 1: Agent inspects context via RunnableConfig
    Note over Agent: Step 2: Agent recognizes complete info & invokes tool:
    Agent->>Agent: ask_user_verification(category="Hardware", priority="Medium", description="...")
    Agent-->>FE: HTTP 200 { response, action: "verification_required", verification_data: {...} }
    
    Note over FE: Frontend displays confirmation buttons & pre-fills form draft
    User->>FE: Clicks "✅ Yes, Submit It"
    FE->>Agent: POST /chat (Body: "Yes, please submit it now", thread_id="test_thread")
    
    Note over Agent: Step 3: Agent verifies confirmation & invokes tool:
    Agent->>BE: submit_service_request() -> POST /api/requests (Header: X-User-Id=alice)
    BE-->>Agent: Ticket Created: REQ-103 (Status: Pending Approval)
    Agent-->>FE: HTTP 200 { response, action: "form_submitted" }
    
    FE->>BE: GET /api/requests (Header: X-User-Id=alice)
    BE-->>FE: Returns updated tickets list [REQ-101, REQ-103]
    FE-->>User: Success banner displayed; tickets table refreshed!
```

---

## 🧩 Service Roles & Responsibilities

### 1. Frontend Service (`frontend/` - Port 3000)
- **Two-Column Responsive Layout**:
  - **Left**: Service Request Form with standard fields (`Category`, `Priority`, `Description`, manual submit button) and a "Submitted Requests" dashboard.
  - **Right**: An embedded "Portal Copilot" chat panel.
- **Session Simulation**:
  - The Persona Switcher dropdown allows instant toggling between different employee identities (*Alice - Senior Developer*, *Bob - Account Executive*, *Charlie - HR Coordinator*).
- **Context Bundling**:
  - Every chat message automatically bundles the active user headers and the browser's live form state (`current_url`, `active_form`, `draft_form_data`).
- **Action Handling**:
  - Responds to structured actions returned by the agent (`verification_required`, `form_submitted`) without requiring any regex or text scraping.

### 2. Backend Service (`backend/` - Port 8002)
- Built with **FastAPI** to represent the core enterprise application.
- Exposes:
  - `POST /api/requests`: Creates new service requests. Extracts the authenticated user's identity from the `X-User-Id` HTTP header.
  - `GET /api/requests`: Strictly queries requests belonging to the authenticated caller (enforces complete multi-tenant / multi-user data isolation).
  - `GET /api/users/{user_id}`: Returns user profile and department metadata.
- Operates independently of the AI agent, meaning forms can be submitted manually or programmatically.

### 3. Agent Assistant Service (`agent_service/` - Port 8001)
- Built with **FastAPI** and **LangChain 1.5+**.
- Uses Azure OpenAI `gpt-5.6-luna` (or any OpenAI-compatible provider).
- Maintains multi-turn conversation threads using LangGraph's in-memory `MemorySaver` checkpointer.
- Hosts context-injected tools:
  - `inspect_web_and_user_context`: Reads caller identity and live browser form drafts.
  - `ask_user_verification`: Triggers the Human-in-the-Loop review phase.
  - `submit_service_request`: Calls the backend API on behalf of the user with verified credentials.
  - `get_my_active_requests`: Queries existing tickets from the backend.
