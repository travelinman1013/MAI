# Handoff Prompt: MAI Framework Implementation - Comprehensive Status & Next Steps

## Project Overview
**MAI Framework** is a production-ready, reusable AI application framework built on Pydantic AI. It targets small-scale deployments (<1000 users) using local LLMs (LM Studio), Qdrant (Vector DB), Redis (Cache/State), and PostgreSQL.

## Current Implementation Status

### 1. Infrastructure Layer (✅ Mostly Complete)
-   **Database**: Async SQLAlchemy with `pgvector` support (`src/infrastructure/database/`).
-   **Cache**: Redis client implemented (`src/infrastructure/cache/`).
-   **Vector Store**: Qdrant client implemented (`src/infrastructure/vector_store/`).
-   **Configuration**: Settings management with Pydantic Settings (`src/core/utils/config.py`).

### 2. Core Framework (✅ Complete)
-   **Agents** (`src/core/agents/`):
    -   ✅ `BaseAgentFramework` generic class implemented.
    -   ✅ Integration with Pydantic AI `Agent` class.
    -   ✅ Structured Output support (`StandardResponse`) verified.
    -   ✅ Integration with `ShortTermMemory` for automatic state persistence.
    -   ✅ Multi-turn conversation support with Redis-backed persistence.
-   **Memory** (`src/core/memory/`):
    -   ✅ `ShortTermMemory` (Redis-backed) implemented.
    -   ✅ `LongTermMemory` (Qdrant + Postgres) structure exists.
-   **Prompts** (`src/core/prompts/`):
    -   ✅ `PromptManager` implemented with YAML storage and Jinja2 templates.
    -   ✅ **Security**: Sandboxing for templates is implemented and verified (blocks `config` access).
-   **Tools** (`src/core/tools/`):
    -   ✅ Registry and decorators structure exists.

### 3. API Layer (❌ Pending)
-   `src/api/routes/`: Currently empty. Needs Auth, Agents, Memory, and Health endpoints.

## Recently Completed: Agent State Management ✅

**Task ID**: `7e6e6abd-e408-420e-b038-7c66fb152c3c` (Agent State Management) - **COMPLETED**

### What Was Implemented:
1.  **Modified `src/core/agents/base.py`**:
    -   Imported `ConversationMemory` from `src.core.memory.short_term`.
    -   Updated `run_async` to:
        -   Initialize memory for the given `session_id`.
        -   Load history from Redis into the memory instance.
        -   Append the user's input to memory.
        -   Pass full conversation history to the Pydantic AI agent.
        -   Append the agent's structured response to memory (as JSON).
    -   Added `conversation_memory` field to `AgentDependencies`.
2.  **Implemented `get_conversation_context`**:
    -   Loads conversation from Redis using `ConversationMemory`.
    -   Converts Message objects to dict format for Pydantic AI.
    -   Returns empty list if Redis or session_id not available.
3.  **Verified with Tests**:
    -   Created `tests/unit/core/agents/test_state_management.py` with two tests:
        - `test_agent_state_management_with_session_id`: Verifies multi-turn conversation persistence.
        - `test_agent_state_management_no_session_id`: Verifies stateless operation when no session provided.
    -   All tests passing (4/4 in agents test suite).

## Next Recommended Focus: API Layer

With agent state management complete, the framework's core is now functional. The next logical step is to expose this functionality via REST API.

## Technical Context & Commands

-   **Python Version**: 3.11+
-   **Key Libraries**: `pydantic-ai`, `asyncpg`, `redis`, `qdrant-client`.
-   **Test Command**:
    ```bash
    export PYTHONPATH=$PYTHONPATH:. && .venv/bin/pytest tests/unit/core/agents/ -v
    ```
-   **Running Tests**:
    -   Prompt Manager: `tests/unit/core/prompts/test_prompt_manager.py` (✅ Passing)
    -   Structured Output: `tests/unit/core/agents/test_structured_output.py` (✅ Passing)
    -   State Management: `tests/unit/core/agents/test_state_management.py` (✅ Passing - 2 tests)

## Backlog (Prioritized)
1.  ✅ ~~Agent State Management~~ (Completed)
2.  **API Routes**: Implement `src/api/routes/agents.py` (Run/Stream endpoints) - **NEXT**
3.  **Memory API**: Implement `src/api/routes/memory.py`.
4.  **Long-Term Memory**: Connect `LongTermMemory` to the agent lifecycle (retrieval/storage).
5.  **Pipelines**: Implement `src/core/pipeline/`.

## Notes for the Agent
-   **Do NOT** revert changes to `test_prompt_manager.py` or `registry.py`. The sandboxing logic is delicate and currently passing.
-   **Structured Output**: The agent returns a Pydantic model (`StandardResponse`). When saving to memory, we save the full JSON dump via `result.output.model_dump_json()`.
-   **Memory Implementation**: The `ConversationMemory` instance must be loaded from Redis before adding new messages, otherwise it will overwrite existing history. See `src/core/agents/base.py:181-182` for the correct pattern.
-   **Task Tracking**: Use `mcp__archon__find_tasks` to browse available tasks in Archon.
