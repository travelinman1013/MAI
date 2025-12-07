#!/bin/bash
# List available local MLX models

LOCAL_MODELS_DIR="/Volumes/the-eagle/maxwell-ext/lmstudio/models/mlx-community"

echo "Available MLX Models:"
echo "====================="

if [ -d "$LOCAL_MODELS_DIR" ]; then
    for model in "$LOCAL_MODELS_DIR"/*/; do
        if [ -d "$model" ]; then
            model_name=$(basename "$model")
            # Check for config.json (indicates valid MLX model)
            if [ -f "$model/config.json" ]; then
                size=$(du -sh "$model" 2>/dev/null | cut -f1)
                echo "  - $model_name ($size)"
            fi
        fi
    done
else
    echo "  Local models directory not found: $LOCAL_MODELS_DIR"
    echo "  Models will be downloaded from HuggingFace Hub"
fi

echo ""
echo "Usage: ./scripts/start-mlx-server.sh [model_name]"
echo "Default: Llama-3.2-1B-Instruct-4bit"
