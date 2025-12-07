# Task: Add Docker Integration for Ollama and llama.cpp

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Create Docker Compose overlay files for Ollama and llama.cpp services
**Sequence**: 7 of 10
**Depends On**: 06-api-routes.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `[TO_BE_ASSIGNED]`
- **Project ID**: `[TO_BE_ASSIGNED]`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous tasks implemented the provider code and API routes. Now we add Docker Compose configurations to run Ollama and llama.cpp as containerized services.

Docker Compose supports overlay files that can extend the base configuration. This allows users to optionally add Ollama or llama.cpp without modifying the main docker-compose.yml.

---

## Requirements

### 1. Create Ollama Docker Compose Overlay

Create `docker/docker-compose.ollama.yml`:

```yaml
# Ollama service overlay
# Usage: docker compose -f docker-compose.yml -f docker/docker-compose.ollama.yml up -d

services:
  ollama:
    image: ollama/ollama:latest
    container_name: mai-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_ORIGINS=*
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    networks:
      - mai-network
    # GPU support (uncomment if using NVIDIA GPU)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

  # Override mai-api to connect to Ollama
  mai-api:
    environment:
      - LLM__PROVIDER=ollama
      - OLLAMA__BASE_URL=http://ollama:11434/v1
      - OLLAMA__MODEL_NAME=${OLLAMA__MODEL_NAME:-llama3.2}
    depends_on:
      ollama:
        condition: service_healthy

volumes:
  ollama_data:
    driver: local
```

### 2. Create llama.cpp Docker Compose Overlay

Create `docker/docker-compose.llamacpp.yml`:

```yaml
# llama.cpp server service overlay
# Usage: docker compose -f docker-compose.yml -f docker/docker-compose.llamacpp.yml up -d
#
# Note: You must provide a GGUF model file in the llamacpp_models volume
# Example: docker cp /path/to/model.gguf mai-llamacpp:/models/model.gguf

services:
  llamacpp:
    image: ghcr.io/ggml-org/llama.cpp:server
    container_name: mai-llamacpp
    ports:
      - "8080:8080"
    volumes:
      - llamacpp_models:/models
    environment:
      - LLAMA_ARG_CTX_SIZE=${LLAMACPP__CTX_SIZE:-8192}
      - LLAMA_ARG_N_GPU_LAYERS=${LLAMACPP__N_GPU_LAYERS:--1}
      - LLAMA_ARG_HOST=0.0.0.0
      - LLAMA_ARG_PORT=8080
    command: --model /models/${LLAMACPP__MODEL_FILE:-model.gguf}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    networks:
      - mai-network
    # GPU support (uncomment if using NVIDIA GPU)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

  # Override mai-api to connect to llama.cpp
  mai-api:
    environment:
      - LLM__PROVIDER=llamacpp
      - LLAMACPP__BASE_URL=http://llamacpp:8080/v1
      - LLAMACPP__MODEL_NAME=${LLAMACPP__MODEL_NAME:-local-model}
    depends_on:
      llamacpp:
        condition: service_healthy

volumes:
  llamacpp_models:
    driver: local
```

### 3. Update Main Docker Compose

Update `docker-compose.yml` to add LLM provider environment variables to mai-api service:

```yaml
# In the mai-api service, add/update environment section:
mai-api:
  # ... existing configuration ...
  environment:
    # ... existing env vars ...
    # LLM Provider configuration
    - LLM__PROVIDER=${LLM__PROVIDER:-lmstudio}
    # LM Studio (default, running on host)
    - LM_STUDIO__BASE_URL=${LM_STUDIO__BASE_URL:-http://host.docker.internal:1234/v1}
    # Ollama (when using docker-compose.ollama.yml or on host)
    - OLLAMA__BASE_URL=${OLLAMA__BASE_URL:-http://host.docker.internal:11434/v1}
    - OLLAMA__MODEL_NAME=${OLLAMA__MODEL_NAME:-llama3.2}
    # llama.cpp (when using docker-compose.llamacpp.yml or on host)
    - LLAMACPP__BASE_URL=${LLAMACPP__BASE_URL:-http://host.docker.internal:8080/v1}
    - LLAMACPP__MODEL_NAME=${LLAMACPP__MODEL_NAME:-local-model}
```

### 4. Create Docker Documentation

Create `docker/README.md`:

```markdown
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
```

---

## Files to Create

- `docker/docker-compose.ollama.yml` - Ollama service overlay
- `docker/docker-compose.llamacpp.yml` - llama.cpp service overlay
- `docker/README.md` - Docker usage documentation

## Files to Modify

- `docker-compose.yml` - Add LLM provider environment variables

---

## Success Criteria

```bash
# Verify overlay files exist and are valid YAML
python -c "import yaml; yaml.safe_load(open('docker/docker-compose.ollama.yml')); print('Ollama YAML OK')"
# Expected: Ollama YAML OK

python -c "import yaml; yaml.safe_load(open('docker/docker-compose.llamacpp.yml')); print('Llamacpp YAML OK')"
# Expected: Llamacpp YAML OK

# Verify docker compose config is valid (dry run)
docker compose -f docker-compose.yml -f docker/docker-compose.ollama.yml config > /dev/null && echo "Ollama config OK"
# Expected: Ollama config OK

docker compose -f docker-compose.yml -f docker/docker-compose.llamacpp.yml config > /dev/null && echo "Llamacpp config OK"
# Expected: Llamacpp config OK

# Verify README exists
test -f docker/README.md && echo "README OK"
# Expected: README OK
```

**Checklist:**
- [ ] `docker-compose.ollama.yml` created with Ollama service
- [ ] `docker-compose.llamacpp.yml` created with llama.cpp service
- [ ] Both overlays override mai-api environment
- [ ] Health checks configured for both services
- [ ] Volume mounts configured
- [ ] GPU support commented but available
- [ ] Main docker-compose.yml updated with env vars
- [ ] docker/README.md created with usage instructions

---

## Technical Notes

- **Overlay Pattern**: Use `-f` flag to compose multiple files
- **host.docker.internal**: Special hostname for accessing host from container (macOS/Windows)
- **Health Checks**: Ollama uses `/api/tags`, llama.cpp uses `/health`
- **Model Volume**: llama.cpp requires model file in volume before starting
- **Start Period**: Allow time for model loading before health checks fail

---

## Important

- Do NOT modify existing service configurations unnecessarily
- Keep GPU support commented by default for compatibility
- Use environment variable substitution for configurability
- llama.cpp requires manual model file placement

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (08-frontend-integration.md) depends on this completing successfully
