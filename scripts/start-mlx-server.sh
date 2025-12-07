#!/bin/bash
# Start MLX-LM server for MAI
# Usage: ./scripts/start-mlx-server.sh [model_name]

set -e

# Configuration
MLX_PORT="${MLX_PORT:-8081}"
MLX_HOST="${MLX_HOST:-127.0.0.1}"
LOCAL_MODELS_DIR="/Volumes/the-eagle/maxwell-ext/lmstudio/models/mlx-community"

# Default model (small and fast)
DEFAULT_MODEL="Llama-3.2-1B-Instruct-4bit"

# Parse arguments
MODEL_NAME="${1:-$DEFAULT_MODEL}"

# Check if local model exists
if [ -d "$LOCAL_MODELS_DIR/$MODEL_NAME" ]; then
    MODEL_PATH="$LOCAL_MODELS_DIR/$MODEL_NAME"
    echo "Using local model: $MODEL_PATH"
else
    # Fall back to HuggingFace Hub
    MODEL_PATH="mlx-community/$MODEL_NAME"
    echo "Using HuggingFace model: $MODEL_PATH"
fi

# Check if mlx_lm is installed
if ! command -v mlx_lm.server &> /dev/null; then
    echo "Error: mlx_lm not installed. Install with: pip install mlx-lm"
    exit 1
fi

# Check if port is already in use
if lsof -i :$MLX_PORT &> /dev/null; then
    echo "Warning: Port $MLX_PORT is already in use"
    echo "Kill existing process with: lsof -ti :$MLX_PORT | xargs kill -9"
    exit 1
fi

echo "Starting MLX-LM server..."
echo "  Model: $MODEL_PATH"
echo "  Host: $MLX_HOST"
echo "  Port: $MLX_PORT"
echo ""

# Start server
exec mlx_lm.server \
    --model "$MODEL_PATH" \
    --host "$MLX_HOST" \
    --port "$MLX_PORT"
