# 3-Tier Enterprise Agent Assistant Architecture

A simple, modular, and production-ready prototype demonstrating how an **Agent Assistant** can use **user context from web requests** (HTTP headers, user identity, department) and **web context** (active page, form inputs) to help users fill and submit web forms via LangChain tools.

---

## 🏗️ The 3 Services (Separate Folders)

```
agent_assistant/
├── frontend/               # Service 1: Web UI (Form, Persona Switcher, Assistant Chat Panel)
│   ├── index.html          # Form fields & Copilot chat interface
│   ├── style.css           # Clean modern enterprise stylesheet
│   ├── app.js              # Interacts with Backend & Agent Assistant
│   └── server.py           # Web server (Port 3000)
│
├── backend/                # Service 2: Backend API (FastAPI)
│   ├── main.py             # Handles manual form submits, user directory & tickets (Port 8002)
│   └── models.py           # Pydantic schemas (ServiceRequest, UserProfile)
│
├── agent_service/          # Service 3: LangChain Agent Assistant (FastAPI + LangChain)
│   ├── main.py             # POST /chat endpoint (Port 8001)
│   ├── agent.py            # LangChain agent with Azure OpenAI gpt-5.6-luna
│   ├── tools.py            # Tools: submit_service_request, autofill_form_on_screen
│   ├── context.py          # UserContext and WebContext extractor & RunnableConfig
│   └── config.py           # Azure OpenAI settings & Backend URL
│
├── start_all.sh            # One-click launcher for all 3 microservices
├── demo_e2e.py             # Automated end-to-end multi-scenario test
└── .env                    # Shared Azure OpenAI credentials
```

---

## 🔄 Interaction Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant FE as Frontend (Port 3000)
    participant Agent as Agent Service (Port 8001)
    participant BE as Backend API (Port 8002)

    Note over User,FE: User selects persona (e.g. Alice, Engineering)
    User->>FE: Types in Chat: "I need a 4K monitor because mine flickers, please submit it"
    FE->>Agent: POST /chat (Headers: X-User-Id=alice; Body: message + web_context)
    Note over Agent: LangChain Agent gathers details (Category: Hardware, Priority: Medium)
    Agent->>BE: Tool submit_service_request() -> POST /api/requests (Header: X-User-Id=alice)
    BE-->>Agent: Ticket Created: REQ-103 (Status: Pending Approval)
    Agent-->>FE: HTTP 200 { response, action: "form_submitted" }
    FE->>BE: GET /api/requests (Header: X-User-Id=alice)
    BE-->>FE: Returns updated tickets list [REQ-101, REQ-103]
    FE-->>User: Chat displays confirmation; tickets table refreshes in real time!
```

---

## 🚀 How to Run

### 1. Launch All 3 Services Concurrently
```bash
cd /home/quan/projects/agent_assistant
./start_all.sh
```
This starts:
- **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- **Agent Assistant API**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Backend Service API**: [http://localhost:8002/docs](http://localhost:8002/docs)

### 2. Run the Automated End-to-End Test
```bash
.venv/bin/python demo_e2e.py
```
This tests:
1. **Alice** (Engineering): Submitting a Hardware ticket via natural language; verified in Backend DB.
2. **Bob** (Sales): Autofilling a software license request directly on the web page.
3. **Data Isolation**: Bob cannot see Alice's requests in Backend.

---

## 💡 How User & Web Context are Handled

### 1. User Context (HTTP Request Headers)
- The frontend sends the user's authenticated session as headers with every chat call:
  - `X-User-Id: alice`
  - `X-User-Name: Alice Wonderland`
  - `X-User-Department: Engineering`
  - `X-User-Role: Senior Developer`
- The Agent Assistant injects this into LangChain's `RunnableConfig`. The LLM **never** needs to guess or ask for the employee's ID.

### 2. Web Context (Browser Form State)
- The frontend captures live form state and attaches it to the request body:
  ```json
  {
    "message": "Please submit this request",
    "web_context": {
      "current_url": "http://localhost:3000/portal/requests",
      "active_form": "service_request_form",
      "draft_form_data": {
        "category": "Hardware",
        "priority": "Medium",
        "description": "4K monitor needed"
      }
    }
  }
  ```
- If the user already filled out part of the form, the agent inspects it via `inspect_web_and_user_context` and only asks for what is missing.

### 3. Tool Execution with Caller Context
- When the Agent Assistant calls `submit_service_request`, it forwards the caller's verified `X-User-Id` header to `http://localhost:8002/api/requests`.
- This ensures non-repudiation and prevents prompt-injection attacks.
