# Agent Workflow & Human-in-the-Loop (HITL)

This document explains how the LangChain Agent manages multi-turn conversations, asks follow-up questions to clarify missing parameters, and enforces a strict Human-in-the-Loop (HITL) verification step before executing actions—without using regular expressions or manual string parsing.

---

## 🧠 Multi-Turn State Management with `MemorySaver`

In web applications, users don't submit complete requests in a single prompt. They converse, ask questions, provide partial details, and confirm actions across multiple turns.

The Agent Assistant uses LangGraph's native in-memory checkpointer (`MemorySaver`):

```python
# agent_service/agent.py
from langgraph.checkpoint.memory import MemorySaver

memory_checkpointer = MemorySaver()

agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    checkpointer=memory_checkpointer,
    system_prompt=SYSTEM_PROMPT,
)
```

Each conversation is identified by a unique `thread_id` passed in `config["configurable"]["thread_id"]`. When the user replies in Turn 2, the agent remembers:
- Who the user is (*Alice, Engineering*).
- What was discussed in Turn 1 (*a 32-inch 4K monitor*).
- What details have already been gathered.

---

## 🔄 The 3-Step Agent Workflow

```
[User Input]
     │
     ▼
[Step 1: Check Required Info]
     ├── Missing Info? ──► [Ask Follow-Up Question in Conversation]
     │
     └── Info Complete?
             │
             ▼
[Step 2: Pre-Submission Verification]
     └── Calls Tool: ask_user_verification(category, priority, description)
             │
             ├── Dispatches Action: "verification_required" to Web UI
             └── Shows Review Summary & Confirmation Buttons to User
                     │
                     ▼
             [User Review]
                     ├── User Rejects / Changes ──► [Agent Adjusts Draft & Re-verifies]
                     │
                     └── User Confirms: "Yes, submit it now"
                             │
                             ▼
             [Step 3: Execution on Confirmation]
                     └── Calls Tool: submit_service_request(...)
                             └── Ticket Created in Backend Database!
```

---

## 🚫 Why Zero Regex is Used

In naive agent architectures, developers often write regex or string-matching rules to detect confirmation or extract fields:

```python
# ❌ FRAGILE ANTI-PATTERN: Regex / Substring Matching
if re.search(r"confirm|yes|submit", user_prompt, re.I):
    submit_order()
category = re.findall(r"category:\s*(\w+)", prompt)
```

### The Native LangChain Approach
In this prototype:
1. **The LLM extracts structured arguments**: The LLM automatically extracts `category`, `priority`, and `description` as strongly-typed JSON schema arguments when invoking tools.
2. **The LLM decides the workflow phase**:
   - When details are ready, the agent calls the tool `ask_user_verification(...)`.
   - When the user confirms, the agent calls the tool `submit_service_request(...)`.
3. **Structured API Responses**:
   The web service checks the tool calls made by the agent:
   ```python
   # agent_service/main.py
   for tc in msg.tool_calls:
       if tc["name"] == "ask_user_verification":
           action = "verification_required"
           verification_data = tc["args"]  # Clean dictionary!
       elif tc["name"] == "submit_service_request":
           action = "form_submitted"
           verification_data = tc["args"]
   ```
4. **Zero Regex in Frontend**:
   The frontend UI reads `data.action === "verification_required"` directly from the response and dynamically displays the confirmation buttons and pre-fills the form draft on screen!

---

## 💬 Live Multi-Turn Transcript Example

### Turn 1: Vague Input -> Follow-Up Question
```text
User: "I need a new monitor for my desk."

Agent (LLM Reasoning):
- Missing: Screen size, specs, connectivity, priority, justification.
- Action: Ask clarifying follow-up question.

Agent Response:
"What monitor specifications do you need (e.g., screen size, resolution, 
refresh rate, and number of monitors)? Also, what priority should this 
request have (Low, Medium, High, or Urgent), and what is the business justification?"
```

---

### Turn 2: Details Provided -> Tool: `ask_user_verification`
```text
User: "It should be 32-inch 4K with USB-C. My current screen flickers and disrupts my coding. Priority is Medium."

Agent (LLM Reasoning):
- All required fields gathered: Category=Hardware, Priority=Medium, Description=32-inch 4K with USB-C...
- Action: Invoke tool ask_user_verification() to prepare human review.
- DO NOT invoke submit_service_request() yet!

Tool Call Executed:
ask_user_verification(
    category="Hardware",
    priority="Medium",
    description="Request a new 32-inch 4K monitor with USB-C connectivity. The current screen flickers and disrupts coding work, so a replacement is needed to maintain productivity."
)

Agent Response:
"📋 Request Summary for Review:
- Submitter: Alice Wonderland (Engineering)
- Category: Hardware
- Priority: Medium
- Description: Request a new 32-inch 4K monitor with USB-C connectivity...

⚠️ Please confirm: Would you like me to officially submit this request now?"

Frontend Action:
Displays interactive action buttons: [✅ Yes, Submit It] [⚡ Make it High Priority] [❌ Cancel]
```

---

### Turn 3: User Confirms -> Tool: `submit_service_request`
```text
User: "Yes, please submit it now!"

Agent (LLM Reasoning):
- User explicitly confirmed the pending verification summary.
- Action: Call submit_service_request() to record the ticket in Backend.

Tool Call Executed:
submit_service_request(
    category="Hardware",
    priority="Medium",
    description="Request a new 32-inch 4K monitor with USB-C connectivity..."
)

Backend API Response:
201 Created -> Ticket ID: REQ-103 (Status: Pending Approval)

Agent Response:
"Your request has been submitted successfully.
- Ticket ID: REQ-103
- Category: Hardware
- Priority: Medium
- Status: Pending Approval"

Frontend Action:
Refreshes the submitted requests list, displaying ticket REQ-103 in real time!
```
