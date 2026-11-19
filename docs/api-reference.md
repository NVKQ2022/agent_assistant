# API Reference

This document outlines the REST API specifications for the Backend Service (Port 8002) and the Agent Assistant Service (Port 8001).

---

## 🛠️ Service 1: Backend Service (Port 8002)

Base URL: `http://localhost:8002`

### 1. Health Check
- **Endpoint**: `GET /health`
- **Response** `(200 OK)`:
  ```json
  {
    "service": "backend",
    "status": "healthy",
    "port": 8002
  }
  ```

---

### 2. Submit Service Request
- **Endpoint**: `POST /api/requests`
- **Headers**:
  - `Content-Type: application/json`
  - `X-User-Id`: Identifier of the authenticated user (e.g. `alice`, `bob`)
  - `X-Submitted-Via`: `web_form` or `agent_assistant`
- **Request Body**:
  ```json
  {
    "category": "Hardware",
    "priority": "Medium",
    "description": "32-inch 4K Monitor for software development",
    "web_context": {
      "current_url": "http://localhost:3000/portal/requests",
      "active_form": "service_request_form"
    }
  }
  ```
- **Response** `(201 Created)`:
  ```json
  {
    "id": "REQ-103",
    "user_id": "alice",
    "user_name": "Alice Wonderland",
    "user_email": "alice@company.com",
    "department": "Engineering",
    "category": "Hardware",
    "priority": "Medium",
    "description": "32-inch 4K Monitor for software development",
    "status": "Pending Approval",
    "created_at": "2026-11-20 00:57:06",
    "submitted_via": "agent_assistant"
  }
  ```

---

### 3. List User Requests
- **Endpoint**: `GET /api/requests`
- **Headers**:
  - `X-User-Id`: Identifier of the authenticated caller (e.g. `alice`)
- **Behavior**: Strictly returns requests belonging to the user specified in `X-User-Id`.
- **Response** `(200 OK)`:
  ```json
  [
    {
      "id": "REQ-101",
      "user_id": "alice",
      "user_name": "Alice Wonderland",
      "department": "Engineering",
      "category": "Hardware",
      "priority": "Medium",
      "description": "Dual 27-inch 4K Monitors for development workstation",
      "status": "Approved",
      "created_at": "2026-11-20 00:00:00",
      "submitted_via": "web_form"
    }
  ]
  ```

---

### 4. Get User Profile
- **Endpoint**: `GET /api/users/{user_id}`
- **Response** `(200 OK)`:
  ```json
  {
    "user_id": "alice",
    "name": "Alice Wonderland",
    "email": "alice@company.com",
    "department": "Engineering",
    "role": "Senior Developer"
  }
  ```

---

## 🤖 Service 2: Agent Assistant Service (Port 8001)

Base URL: `http://localhost:8001`

### 1. Health Check
- **Endpoint**: `GET /health`
- **Response** `(200 OK)`:
  ```json
  {
    "service": "agent_service",
    "status": "healthy",
    "port": 8001,
    "model": "gpt-5.6-luna"
  }
  ```

---

### 2. Chat with Assistant
- **Endpoint**: `POST /chat`
- **Headers**:
  - `Content-Type: application/json`
  - `X-User-Id`: User identifier (e.g. `alice`)
  - `X-User-Name`: Display name (e.g. `Alice Wonderland`)
  - `X-User-Department`: Department (e.g. `Engineering`)
  - `X-User-Role`: Role (e.g. `Senior Developer`)
  - `X-Tenant-Id`: Tenant / Organization partition
- **Request Body**:
  ```json
  {
    "message": "I need a 4K monitor because mine flickers",
    "thread_id": "session_alice_1700000000",
    "web_context": {
      "current_url": "http://localhost:3000/portal/requests",
      "page_title": "IT Equipment & Service Request Portal",
      "active_form": "service_request_form",
      "draft_form_data": {
        "category": "Hardware",
        "priority": "Medium",
        "description": ""
      }
    }
  }
  ```

- **Response** `(200 OK)`:
  ```json
  {
    "response": "📋 Request Summary for Review:\n- Submitter: Alice Wonderland (Engineering)\n- Category: Hardware\n- Priority: Medium\n- Description: Request a new 32-inch 4K monitor...\n\nWould you like me to submit this request for you now?",
    "user_context": {
      "user_id": "alice",
      "name": "Alice Wonderland",
      "department": "Engineering",
      "role": "Senior Developer",
      "tenant_id": "acme-corp"
    },
    "web_context": {
      "current_url": "http://localhost:3000/portal/requests",
      "page_title": "IT Equipment & Service Request Portal",
      "active_form": "service_request_form",
      "draft_form_data": {}
    },
    "thread_id": "session_alice_1700000000",
    "action": "verification_required",
    "verification_data": {
      "category": "Hardware",
      "priority": "Medium",
      "description": "Request a new 32-inch 4K monitor..."
    },
    "tool_calls": [
      {
        "tool_name": "ask_user_verification",
        "args": {
          "category": "Hardware",
          "priority": "Medium",
          "description": "Request a new 32-inch 4K monitor..."
        },
        "output": "[VERIFICATION PENDING] Prepared request summary..."
      }
    ]
  }
  ```

---

## 💻 Sample `curl` Commands

### Query Active Tickets:
```bash
curl -X GET http://localhost:8002/api/requests \
  -H "X-User-Id: alice"
```

### Send Chat Message to Agent:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: alice" \
  -H "X-User-Name: Alice Wonderland" \
  -H "X-User-Department: Engineering" \
  -d '{
    "message": "I need a 4K monitor for development",
    "thread_id": "curl_session_1"
  }'
```
