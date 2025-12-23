#!/bin/bash

# Fix for macOS fork safety issues with grpc/python
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Default Redis URL if not set in .env
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}

echo "---------------------------------------------------"
echo "Starting Employee Recruiter Agent System"
echo "Redis URL: $REDIS_URL"
echo "---------------------------------------------------"

# Function to kill background processes on exit
cleanup() {
    echo "Shutting down..."
    kill $WORKER_PID
    exit
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT

# Start RQ Worker in the background
# Using SimpleWorker to avoid fork/threading crashes on macOS
echo "[1/2] Starting RQ Worker (SimpleWorker)..."
rq worker -u "$REDIS_URL" --worker-class rq.SimpleWorker &
WORKER_PID=$!

# Wait a moment for worker to initialize
sleep 2

# Start FastAPI Server
echo "[2/2] Starting FastAPI Server..."
python main.py

# Ensure worker is killed when server stops
cleanup
