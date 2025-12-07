# Docker Configuration for MAI Framework

## Quick Start

### Default (LM Studio on host)

```bash
docker compose up -d
```

Requires LM Studio running on your host machine at `localhost:1234`.

### With Ollama (containerized)

```bash
docker compose -f docker-compose.yml -f docker/docker-compose.ollama.yml up -d

# Pull a model
docker exec mai-ollama ollama pull llama3.2

# Verify
curl http://localhost:8000/api/llm-status
```

### With llama.cpp (containerized)

```bash
# First, copy your GGUF model file
docker volume create llamacpp_models
docker run --rm -v llamacpp_models:/models -v /path/to/your/models:/source alpine cp /source/model.gguf /models/

# Start services
LLAMACPP__MODEL_FILE=model.gguf docker compose -f docker-compose.yml -f docker/docker-compose.llamacpp.yml up -d

# Verify
curl http://localhost:8000/api/llm-status
```

### With Ollama on host

```bash
# Start Ollama on host first
ollama serve

# Then start MAI with Ollama provider
LLM__PROVIDER=ollama docker compose up -d
```

## Environment Variables

### Provider Selection

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM__PROVIDER` | `lmstudio` | Provider to use: `openai`, `lmstudio`, `ollama`, `llamacpp`, `auto` |

### Ollama Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA__BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama API URL |
| `OLLAMA__MODEL_NAME` | `llama3.2` | Default model to use |

### llama.cpp Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMACPP__BASE_URL` | `http://host.docker.internal:8080/v1` | llama.cpp server URL |
| `LLAMACPP__MODEL_NAME` | `local-model` | Model identifier |
| `LLAMACPP__MODEL_FILE` | `model.gguf` | GGUF file name in volume |
| `LLAMACPP__CTX_SIZE` | `8192` | Context window size |
| `LLAMACPP__N_GPU_LAYERS` | `-1` | GPU layers (-1 = all) |

## GPU Support

For NVIDIA GPU acceleration, uncomment the `deploy` section in the overlay files:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Requires nvidia-container-toolkit installed on host.

## Troubleshooting

### Check provider status

```bash
curl http://localhost:8000/api/llm-status
curl http://localhost:8000/api/models/providers
```

### Check container logs

```bash
docker compose logs mai-api
docker compose logs ollama  # if using Ollama overlay
docker compose logs llamacpp  # if using llama.cpp overlay
```

### Network issues

Ensure containers are on the same network (`mai-network`).

For host services, use `host.docker.internal` instead of `localhost`.
