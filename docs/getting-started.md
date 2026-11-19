# Getting Started & Developer Guide

This guide walks you through setting up, configuring, and running the 3-tier Context-Aware Enterprise Agent Assistant prototype locally.

---

## 📋 Prerequisites

- **Python**: 3.10, 3.11, or 3.12
- **Bash Shell**: (Linux, macOS, or WSL on Windows)
- **OpenAI / Azure OpenAI Credentials**: Any OpenAI API key or Azure OpenAI endpoint.

---

## ⚡ Quickstart (5 Minutes)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/NVKQ2022/agent_assistant.git
cd agent_assistant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Configure Environment (`.env`)
Copy the template file:
```bash
cp .env.example .env
```

Edit `.env` with your API credentials:
```env
# Server configuration
HOST=0.0.0.0
PORT=8001
APP_ENV=development
ALLOW_ANONYMOUS=false

# Backend Service URL
BACKEND_URL=http://localhost:8002

# Azure OpenAI / OpenAI compatible endpoint
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://<your-resource>.services.ai.azure.com/openai/v1
OPENAI_MODEL=gpt-5.6-luna
```

---

### 3. Launch All Services Concurrently
Run the launcher script:
```bash
./start_all.sh
```

This will automatically launch:
- 🌐 **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- 🤖 **Agent Assistant API**: [http://localhost:8001](http://localhost:8001) (Docs at `/docs`)
- 🏢 **Backend API**: [http://localhost:8002](http://localhost:8002) (Docs at `/docs`)

Press `Ctrl+C` in your terminal to cleanly stop all background services.

---

## 🧪 Testing & Verification

### 1. Run Automated End-to-End Multi-Turn Test
Runs the live multi-turn follow-up and verification scenario against the Azure OpenAI model:
```bash
.venv/bin/python demo_e2e.py
```

### 2. Run the Pytest Unit & Integration Suite
Runs the 15 security and context-isolation tests:
```bash
.venv/bin/pytest -v
```

---

## 🖥️ Using the Web Interface

1. Open [http://localhost:3000](http://localhost:3000) in your browser.
2. In the top navigation bar, use the **User Persona** dropdown to switch identities:
   - *Alice*: Senior Developer in Engineering
   - *Bob*: Account Executive in Sales & Accounts
   - *Charlie*: HR Coordinator in People Operations
3. In the right-hand **Copilot Panel**:
   - Type: `"I need a new monitor for my desk"`
   - Observe how the assistant pauses to ask follow-up questions regarding specifications and urgency.
   - Reply with your preferences.
   - Observe the structured summary and click the interactive **`[✅ Yes, Submit It]`** button.
   - Watch the left-hand form update and the submitted requests table refresh in real time!
