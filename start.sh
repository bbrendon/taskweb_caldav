#!/bin/bash
# Start both backend and frontend dev servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Starting CalDAV Task Manager ==="

# Start Django backend
echo "[backend] Starting Django on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python manage.py runserver 8000 &
BACKEND_PID=$!

# Start Vue frontend
echo "[frontend] Starting Vite dev server on http://localhost:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000/api/"
echo "  Frontend: http://localhost:5173/"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and clean up on exit
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" INT TERM
wait
