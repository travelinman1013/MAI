#!/bin/bash
# Start MLX-LM Manager Service
# This service runs on the host to manage the MLX-LM server process

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Use project venv if available, otherwise system Python
if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
    UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"
else
    PYTHON="python3"
    UVICORN="uvicorn"
fi

# Check for required dependencies
if ! $PYTHON -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
    echo "Missing dependencies. Install with:"
    echo "  pip install fastapi uvicorn httpx"
    echo "Or activate the project virtual environment."
    exit 1
fi

echo "Starting MLX-LM Manager on port 8082..."
echo "  Manager: http://localhost:8082"
echo "  Endpoints:"
echo "    GET  /status  - Server status"
echo "    POST /start   - Start server"
echo "    POST /stop    - Stop server"
echo "    POST /restart - Restart server"
echo "    GET  /models  - List models"
echo "    GET  /config  - Get config"
echo "    POST /config  - Update config"
echo ""

exec $UVICORN mlx_manager:app --host 127.0.0.1 --port 8082 --app-dir "$SCRIPT_DIR"
