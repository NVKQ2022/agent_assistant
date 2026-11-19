// Frontend Application Logic
const BACKEND_URL = "http://localhost:8002";
const AGENT_URL = "http://localhost:8001";

// Mock user directory representing active session
const USERS = {
  alice: {
    user_id: "alice",
    name: "Alice Wonderland",
    email: "alice@company.com",
    department: "Engineering",
    role: "Senior Developer",
  },
  bob: {
    user_id: "bob",
    name: "Bob Builder",
    email: "bob@company.com",
    department: "Sales & Accounts",
    role: "Account Executive",
  },
  charlie: {
    user_id: "charlie",
    name: "Charlie Chaplin",
    email: "charlie@company.com",
    department: "People Operations",
    role: "HR Coordinator",
  },
};

let currentUser = USERS.alice;
let currentThreadId = "thread_alice_" + Date.now();

// DOM Elements
const personaSelect = document.getElementById("personaSelect");
const fieldName = document.getElementById("fieldName");
const fieldDepartment = document.getElementById("fieldDepartment");
const fieldCategory = document.getElementById("fieldCategory");
const fieldPriority = document.getElementById("fieldPriority");
const fieldDescription = document.getElementById("fieldDescription");
const form = document.getElementById("serviceRequestForm");
const submitAlert = document.getElementById("submitAlert");
const requestsList = document.getElementById("requestsList");
const btnRefreshRequests = document.getElementById("btnRefreshRequests");
const btnClearForm = document.getElementById("btnClearForm");

// Assistant DOM Elements
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const btnSendChat = document.getElementById("btnSendChat");
const toggleContextDetails = document.getElementById("toggleContextDetails");
const contextInspector = document.getElementById("contextInspector");
const ctxUserId = document.getElementById("ctxUserId");
const ctxDept = document.getElementById("ctxDept");
const ctxUrl = document.getElementById("ctxUrl");
const ctxDraftPreview = document.getElementById("ctxDraftPreview");

// 1. Initialize user persona
function updateCurrentUser(uid) {
  currentUser = USERS[uid] || USERS.alice;
  currentThreadId = "thread_" + currentUser.user_id + "_" + Date.now();
  fieldName.value = currentUser.name;
  fieldDepartment.value = currentUser.department;

  // Update Inspector
  ctxUserId.textContent = currentUser.user_id;
  ctxDept.textContent = currentUser.department;
  ctxUrl.textContent = window.location.pathname || "/portal/requests";

  // Reload submitted requests for the active user
  loadUserRequests();
  updateDraftPreview();

  // Reset chat for new session
  chatMessages.innerHTML = `
    <div class="message assistant-message">
      <div class="bubble">
        👋 Hi <strong>${currentUser.name}</strong> (${currentUser.department})! I am your <strong>Portal Copilot</strong>.<br><br>
        Tell me what equipment, software, or access you need. I'll gather any missing details and verify everything with you before submitting.
      </div>
    </div>
  `;
}

// 2. Load submitted requests from Backend API
async function loadUserRequests() {
  requestsList.innerHTML = `<p class="loading-text">Loading ${currentUser.name}'s requests...</p>`;
  try {
    const res = await fetch(`${BACKEND_URL}/api/requests`, {
      headers: { "X-User-Id": currentUser.user_id },
    });
    if (!res.ok) throw new Error("Failed to load requests");
    const requests = await res.json();

    if (requests.length === 0) {
      requestsList.innerHTML = `<p class="req-meta">No requests submitted yet for ${currentUser.name}.</p>`;
      return;
    }

    requestsList.innerHTML = requests
      .map(
        (r) => `
        <div class="request-item">
          <div class="req-main">
            <h4>${r.id}: ${r.category} (${r.priority} Priority)</h4>
            <p class="req-meta">${r.description}</p>
            <p class="req-meta"><small>Submitted via: ${r.submitted_via} • ${r.created_at}</small></p>
          </div>
          <span class="req-status">${r.status}</span>
        </div>
      `
      )
      .join("");
  } catch (err) {
    requestsList.innerHTML = `<p class="req-meta" style="color:red">Backend API offline. Run backend service on port 8000.</p>`;
  }
}

// 3. Manual Form Submission
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  submitAlert.classList.add("hidden");

  const payload = {
    category: fieldCategory.value,
    priority: fieldPriority.value,
    description: fieldDescription.value,
  };

  try {
    const res = await fetch(`${BACKEND_URL}/api/requests`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": currentUser.user_id,
        "X-Submitted-Via": "web_form",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to submit");
    const created = await res.json();

    // Show alert
    submitAlert.textContent = `✅ Request ${created.id} submitted successfully!`;
    submitAlert.className = "alert alert-success";
    submitAlert.classList.remove("hidden");

    // Clear form
    fieldDescription.value = "";
    fieldCategory.value = "";
    fieldPriority.value = "Medium";
    updateDraftPreview();

    // Refresh list
    loadUserRequests();
  } catch (err) {
    submitAlert.textContent = `❌ Error: Unable to submit request. Is backend running?`;
    submitAlert.className = "alert";
    submitAlert.style.backgroundColor = "#fee2e2";
    submitAlert.style.color = "#991b1b";
    submitAlert.classList.remove("hidden");
  }
});

// 4. Update Live Form Draft preview for the Inspector
function updateDraftPreview() {
  const draft = {
    category: fieldCategory.value || null,
    priority: fieldPriority.value || null,
    description: fieldDescription.value || null,
  };
  ctxDraftPreview.textContent = JSON.stringify(draft, null, 2);
  return draft;
}

[fieldCategory, fieldPriority, fieldDescription].forEach((el) => {
  el.addEventListener("input", updateDraftPreview);
});

btnClearForm.addEventListener("click", () => {
  fieldCategory.value = "";
  fieldPriority.value = "Medium";
  fieldDescription.value = "";
  submitAlert.classList.add("hidden");
  updateDraftPreview();
});

btnRefreshRequests.addEventListener("click", loadUserRequests);

// 5. Chat Interaction with Agent Assistant Service
function appendMessage(sender, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}-message`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.style.whiteSpace = "pre-wrap";
  bubble.textContent = text;
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChatMessage(userText) {
  appendMessage("user", userText);
  chatInput.value = "";
  chatInput.disabled = true;
  btnSendChat.disabled = true;

  // Capture current web context (current url, form draft)
  const currentDraft = updateDraftPreview();
  const webContext = {
    current_url: window.location.href,
    page_title: document.title,
    active_form: "service_request_form",
    draft_form_data: currentDraft,
  };

  // Add temporary typing indicator
  const typingDiv = document.createElement("div");
  typingDiv.className = "message assistant-message";
  typingDiv.innerHTML = `<div class="bubble" style="color:#64748b"><em>Agent is thinking...</em></div>`;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch(`${AGENT_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": currentUser.user_id,
        "X-User-Name": currentUser.name,
        "X-User-Department": currentUser.department,
        "X-User-Role": currentUser.role,
        "X-Tenant-Id": "acme-corp",
      },
      body: JSON.stringify({
        message: userText,
        web_context: webContext,
        thread_id: currentThreadId,
      }),
    });

    chatMessages.removeChild(typingDiv);

    if (!res.ok) {
      const err = await res.json();
      appendMessage("assistant", `⚠️ Error: ${err.detail || "Unable to reach assistant"}`);
      return;
    }

    const data = await res.json();
    appendMessage("assistant", data.response);

    // Handle LangChain Agent Actions directly from structured tool calls
    if (data.action === "verification_required") {
      // The LangChain Agent decided to request verification before submitting
      if (data.verification_data) {
        const v = data.verification_data;
        if (v.category) fieldCategory.value = v.category;
        if (v.priority) fieldPriority.value = v.priority;
        if (v.description) fieldDescription.value = v.description;
        updateDraftPreview();
      }

      // Display quick action confirmation buttons
      const actionDiv = document.createElement("div");
      actionDiv.className = "message assistant-message";
      actionDiv.style.marginTop = "-6px";
      actionDiv.innerHTML = `
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" onclick="sendChatMessage('Yes, please submit it now')">✅ Yes, Submit It</button>
          <button class="btn btn-sm btn-secondary" onclick="sendChatMessage('Change priority to High')">⚡ Make it High Priority</button>
          <button class="btn btn-sm btn-outline" onclick="sendChatMessage('I want to cancel this request')">❌ Cancel</button>
        </div>
      `;
      chatMessages.appendChild(actionDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } else if (data.action === "form_submitted") {
      // The LangChain Agent submitted the form
      submitAlert.textContent = `🎉 Agent Copilot officially submitted your request!`;
      submitAlert.className = "alert alert-success";
      submitAlert.classList.remove("hidden");
      // Clear form and reload list
      fieldDescription.value = "";
      fieldCategory.value = "";
      fieldPriority.value = "Medium";
      updateDraftPreview();
      loadUserRequests();
    }
      const d = data.autofill_data;
      if (d.category) fieldCategory.value = d.category;
      if (d.priority) fieldPriority.value = d.priority;
      if (d.description) fieldDescription.value = d.description;
      updateDraftPreview();

      // Flash highlight
      form.style.transition = "box-shadow 0.3s";
      form.style.boxShadow = "0 0 0 3px #38bdf8";
      setTimeout(() => (form.style.boxShadow = "none"), 1200);
    }
  } catch (err) {
    if (typingDiv.parentNode) chatMessages.removeChild(typingDiv);
    appendMessage("assistant", `⚠️ Connection Error: Unable to reach Agent Assistant service on port 8001.`);
  } finally {
    chatInput.disabled = false;
    btnSendChat.disabled = false;
    chatInput.focus();
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (text) sendChatMessage(text);
});

// Quick prompt chips
document.querySelectorAll(".prompt-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    sendChatMessage(chip.getAttribute("data-prompt"));
  });
});

toggleContextDetails.addEventListener("click", () => {
  contextInspector.classList.toggle("hidden");
});

personaSelect.addEventListener("change", (e) => {
  updateCurrentUser(e.target.value);
});

// Init on page load
updateCurrentUser("alice");
