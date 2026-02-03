#!/bin/bash
# start_servers.sh

# Start Backend
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
cd backend
fuser -k 8088/tcp || true
uvicorn app.main:app --host 0.0.0.0 --port 8088 > ../backend.log 2>&1 &
BE_PID=$!
cd ..

# Start Frontend
cd frontend
fuser -k 5173/tcp || true
npm run dev -- --host 0.0.0.0 --port 5173 > ../frontend.log 2>&1 &
FE_PID=$!
cd ..

echo "Backend PID: $BE_PID"
echo "Frontend PID: $FE_PID"

# Wait for servers to be ready
echo "Waiting for servers to start..."
sleep 10

# Verify
curl -s http://127.0.0.1:8088/ > /dev/null && echo "Backend is UP" || echo "Backend is DOWN"
curl -s http://127.0.0.1:5173/ > /dev/null && echo "Frontend is UP" || echo "Frontend is DOWN"

# Save PIDs to file for later cleanup
echo $BE_PID > .server_pids
echo $FE_PID >> .server_pids
