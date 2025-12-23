#!/bin/bash

# ==============================================================================
# 🤖 Employee Recruiter Agent - Startup Orchestrator
# ==============================================================================

# macOS Fork Safety for gRPC/Python
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Color codes for professional output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}        EMPLOYEE RECRUITER AGENT SYSTEM            ${NC}"
echo -e "${BLUE}===================================================${NC}"

# 1. Load Environment Variables Robustly
if [ -f .env ]; then
    echo -e "${GREEN}ℹ️  Loading configuration from .env...${NC}"
    # Use perl to clean and export properly, handles spaces and quotes much better than bash loops
    eval $(perl -ne 'print "export $1=\"$2\"\n" if /^([A-ZA-Z_]+)\s*=\s*\"?(.*?)\"?\s*$/' .env)
else
    echo -e "${YELLOW}⚠️  Warning: .env file not found. Falling back to system env.${NC}"
fi

# Config Defaults
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
API_PORT=${API_PORT:-8000}

# 2. Pre-flight Checks
echo -e "${GREEN}🔍 Performing pre-flight checks...${NC}"

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠️  redis-cli not found. Skipping Redis health check.${NC}"
else
    if ! redis-cli -u "$REDIS_URL" ping &> /dev/null; then
        echo -e "${RED}❌ Error: Redis is not reachable at $REDIS_URL${NC}"
        echo -e "${YELLOW}Please start Redis before running the agent.${NC}"
        exit 1
    fi
fi

# 3. Process Management Setup
WORKER_PID=""

cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    if [ -n "$WORKER_PID" ] && kill -0 "$WORKER_PID" 2>/dev/null; then
        kill "$WORKER_PID"
        echo -e "${GREEN}✅ RQ Worker (PID: $WORKER_PID) terminated.${NC}"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# 4. Launch Services
echo -e "${GREEN}🚀 Launching background worker...${NC}"
# SimpleWorker is required on macOS to avoid fork() issues
rq worker -u "$REDIS_URL" --worker-class rq.SimpleWorker > worker.log 2>&1 &
WORKER_PID=$!

sleep 1
if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo -e "${RED}❌ Worker failed to start. See worker.log for errors.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ RQ Worker started (PID: $WORKER_PID)${NC}"

echo -e "${GREEN}🚀 Starting API server...${NC}"
echo -e "${BLUE}---------------------------------------------------${NC}"
python main.py
echo -e "${BLUE}---------------------------------------------------${NC}"

cleanup
