# Handoff Prompt: Fix LM Studio Model Creation for Pydantic-AI 1.x

## Problem Summary

The chat_agent returns "[Echo Mode - LLM unavailable]" responses despite the LLM status endpoint showing the model is connected. The root cause is an API incompatibility between the current `lmstudio_provider.py` code and pydantic-ai 1.x.

**Error from logs:**
```
OpenAIChatModel.__init__() got an unexpected keyword argument 'base_url'
```

The `create_lmstudio_model()` function passes `base_url` to `OpenAIModel`, but pydantic-ai 1.x changed the API. The model constructor no longer accepts `base_url` directly - you must use a different approach to configure custom OpenAI-compatible endpoints like LM Studio.

**Impact:** All LLM calls fail silently, causing the `ChatAgent` to fall back to echo mode even though LM Studio is running and accessible.

## Environment Details

- **Working Directory:** /Users/maxwell/Projects/MAI
- **Git Branch:** feat/microservice_setup
- **LM Studio URL:** http://host.docker.internal:1234/v1 (from Docker) or http://localhost:1234/v1 (from host)
- **Loaded Model:** google/gemma-3-12b
- **pydantic-ai Version:** 1.27.0 (check pyproject.toml)
- **Key Files:**
  - `src/core/models/lmstudio_provider.py` - Model creation (THE BUG IS HERE)
  - `src/core/models/providers.py` - Provider factory
  - `src/core/agents/chat_agent.py` - Chat agent implementation

## Verification Commands

```bash
# Verify LM Studio is accessible from container
docker exec mai-api curl -s http://host.docker.internal:1234/v1/models | head -20
# Expected: JSON with model list including "google/gemma-3-12b"

# Check the exact error in logs
docker compose logs mai-api 2>&1 | grep -i "base_url\|unexpected keyword"
# Expected: "OpenAIChatModel.__init__() got an unexpected keyword argument 'base_url'"

# Check pydantic-ai version
docker exec mai-api pip show pydantic-ai | grep Version
# Expected: Version: 1.27.0 (or similar 1.x)

# Test current LLM status endpoint (works because it uses httpx directly)
curl -s http://localhost:8000/api/v1/agents/llm-status
# Expected: {"provider":"lmstudio","connected":true,"model_name":"google/gemma-3-12b","error":null}

# Test chat agent (currently fails)
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "hello", "session_id": "test"}'
# Current (broken): Returns "[Echo Mode - LLM unavailable]"
# Expected (fixed): Returns actual LLM response
```

## Task: Fix OpenAIModel Creation for Pydantic-AI 1.x

### Step 1: Research pydantic-ai 1.x OpenAI Provider API

Check the pydantic-ai documentation or source code for the correct way to create an OpenAI-compatible model with a custom base URL.

**Options in pydantic-ai 1.x:**
1. Use `OpenAIModel` with an `openai.AsyncOpenAI` client that has custom `base_url`
2. Use environment variables (`OPENAI_BASE_URL`)
3. Use `OpenAIProvider` class if available

```bash
# Check pydantic-ai OpenAIModel source/signature
docker exec mai-api python -c "from pydantic_ai.models.openai import OpenAIModel; help(OpenAIModel.__init__)"
```

### Step 2: Update `create_lmstudio_model()` Function

**File:** `src/core/models/lmstudio_provider.py` (lines 177-190)

**Current (broken) code:**
```python
model = OpenAIModel(
    final_model_name,
    base_url=lm_settings.base_url,
    api_key=lm_settings.api_key,
)
```

**Fix approach - create an OpenAI client first:**
```python
from openai import AsyncOpenAI

# Create custom OpenAI client pointing to LM Studio
client = AsyncOpenAI(
    base_url=lm_settings.base_url,
    api_key=lm_settings.api_key,
)

# Pass the client to OpenAIModel
model = OpenAIModel(
    final_model_name,
    openai_client=client,  # Use the custom client
)
```

### Step 3: Update Imports

Add the `openai` import at the top of `lmstudio_provider.py`:

```python
from openai import AsyncOpenAI
```

### Step 4: Rebuild and Test

```bash
# Rebuild the API container
docker compose build mai-api

# Restart services
docker compose up -d mai-api

# Wait for health check
sleep 15

# Test the fix
curl -s -X POST "http://localhost:8000/api/v1/agents/stream/chat_agent" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What is 2+2?", "session_id": "test-fix"}'
# Should return actual LLM response, not echo mode
```

## Alternative Approaches

**Option 1: Custom OpenAI Client (Recommended)**
- Create `AsyncOpenAI` client with `base_url` and pass to `OpenAIModel`
- Most explicit and maintainable
- Works with pydantic-ai 1.x

**Option 2: Environment Variables**
- Set `OPENAI_BASE_URL` environment variable
- Less explicit, may interfere with actual OpenAI usage
- Not recommended for dual OpenAI/LM Studio support

**Option 3: Check for OpenAIProvider class**
- Some versions of pydantic-ai have a provider abstraction
- May not be available in all versions

## Success Criteria

- [ ] `docker compose logs mai-api` shows NO "unexpected keyword argument 'base_url'" errors
- [ ] `curl` to `/api/v1/agents/stream/chat_agent` returns actual LLM response (not "[Echo Mode...]")
- [ ] GUI chat with `chat_agent` selected shows intelligent responses
- [ ] Status bar still shows "LLM: OK (google/gemma-3-12b)"

## Common Issues

**Issue 1: `openai` package not installed**
- Solution: Add `openai` to dependencies in `pyproject.toml` (likely already there for pydantic-ai)
- Debug: `docker exec mai-api pip show openai`

**Issue 2: Wrong client type (sync vs async)**
- Solution: Use `AsyncOpenAI` not `OpenAI` for async operations
- Debug: Check if error mentions sync/async mismatch

**Issue 3: Model name format issues**
- Solution: LM Studio may expect specific model name formats
- Debug: `curl http://localhost:1234/v1/models` to see exact model IDs

**Issue 4: Connection timeout from Docker**
- Solution: Verify `host.docker.internal` resolves correctly
- Debug: `docker exec mai-api ping -c 1 host.docker.internal`

## Files to Review

- `src/core/models/lmstudio_provider.py` - Lines 177-190 (model creation - **FIX HERE**)
- `src/core/models/providers.py` - Lines 125-132 (provider factory)
- `src/core/agents/chat_agent.py` - Lines 47, 91-92, 152-155 (fallback logic)
- `pyproject.toml` - Check pydantic-ai and openai versions
- `docker-compose.yml` - LM Studio URL in environment variables

## Additional Context

The `lmstudio_health_check()` function works correctly because it uses `httpx` directly to call the `/v1/models` endpoint - it doesn't use pydantic-ai's model classes. This is why the status bar shows "LLM: OK" but the actual agent calls fail.

The fix needs to update only the model creation code, not the health check logic.
