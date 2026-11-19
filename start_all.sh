#!/bin/bash
# Script to launch all 3 microservices concurrently

set -e

# Find virtualenv python
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    UVICORN=".venv/bin/uvicorn"
else
    PYTHON="python3"
    UVICORN="uvicorn"
fi

echo "=========================================================="
echo " Starting 3-Tier Agent Assistant Architecture"
echo "=========================================================="
echo " 1. Backend Service (Port 8002)      -> Handles form requests & DB"
echo " 2. Agent Assistant Service (Port 8001)-> LangChain AI Copilot"
echo " 3. Frontend Web App (Port 3000)     -> UI Form & Assistant Chat"
echo "=========================================================="

# Trap SIGINT and SIGTERM to kill background children on Ctrl+C
trap 'echo -e "\n🛑 Stopping all services..."; kill $(jobs -p) 2>/dev/null; exit' SIGINT SIGTERM EXIT

# 1. Start Backend Service
echo "Starting Backend API on http://localhost:8002..."
$UVICORN backend.main:app --host 0.0.0.0 --port 8002 &
PID_BACKEND=$!

# 2. Start Agent Assistant Service
echo "Starting Agent Assistant Service on http://localhost:8001..."
$UVICORN agent_service.main:app --host 0.0.0.0 --port 8001 &
PID_AGENT=$!

# 3. Start Frontend Web Server
echo "Starting Frontend Web Server on http://localhost:3000..."
$PYTHON frontend/server.py &
PID_FRONTEND=$!

echo ""
echo "✅ All services running!"
echo "👉 Open your browser at: http://localhost:3000"
echo "Press Ctrl+C to stop all services."
echo ""

wait
