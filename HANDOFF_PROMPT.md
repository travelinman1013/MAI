# Handoff Prompt: MAI Framework Implementation - Prompt Management & Core Completion

## Problem Summary

You are continuing the implementation of **MAI Framework** (Modern AI Framework), a production-ready, reusable AI application framework.

**Current Status**: 
- ✅ Phase 1 & 2: Completed.
- ⏳ Phase 3: Core Framework (Close to completion)
  - ✅ Base Agent System
  - ✅ Tool System
  - ✅ Memory System (Short-term & Long-term)
  - ⏳ **Prompt Management System** (In Progress - **Debugging Sandboxing**)

**Your Mission**: 
1.  **Fix the Prompt Manager Sandboxing**: The unit test `test_render_template_sandboxing` in `tests/unit/core/prompts/test_prompt_manager.py` is failing. The custom `SecureSandbox` in `src/core/prompts/registry.py` needs to strictly prevent unsafe attribute access (like `config.SECRET_KEY` or internal Python attributes) while allowing standard template rendering.
2.  **Verify Prompt Manager**: Ensure all tests in `tests/unit/core/prompts/test_prompt_manager.py` pass.
3.  **Move to Next Feature**: Once Prompt Management is done, start the **Structured Output / Response Model** implementation.

---

## Environment Details

-   **Working Directory**: `/Users/maxwell/Projects/ai_framework_1`
-   **Virtual Env**: `.venv` (Active)
-   **Test Command**: `export PYTHONPATH=$PYTHONPATH:. && .venv/bin/pytest tests/unit/core/prompts/test_prompt_manager.py -v`
-   **Dependencies**: `jinja2`, `pyyaml` (installed).

## Current Task: Prompt Management System (Task ID: `2fc62572-b8cd-4787-8484-c73bc7067ec8`)

### File State
-   **`src/core/prompts/registry.py`**: Implements `PromptManager` and `SecureSandbox`.
    -   *Issue*: The `is_safe_attribute` method in `SecureSandbox` is currently too permissible or not triggering the expected `SecurityError` (which `render_template` wraps in `MAIException`) for the dictionary attribute access test case.
-   **`src/core/prompts/models.py`**: `PromptTemplate` Pydantic model (✅ Done).
-   **`tests/unit/core/prompts/test_prompt_manager.py`**: Comprehensive unit tests.
    -   *Failing Test*: `test_render_template_sandboxing` - specifically the assertion checking for `MAIException` when accessing `config.SECRET_KEY` (where `config` is a dict).

### Debugging Context
The test `test_render_template_sandboxing` fails with `Failed: DID NOT RAISE <class 'src.core.utils.exceptions.MAIException'>`. This means Jinja2 allowed `{{ config.SECRET_KEY }}` to execute inside the sandbox, which it should not have if configured correctly to block attribute access on dictionaries or generally unsafe attributes.

**Goal for Sandboxing**:
-   Allow standard usage: `{{ variable }}`, `{{ my_dict['key'] }}`.
-   **Block** attribute access on dictionaries if possible, or at least block access to unsafe attributes/methods like `__class__`, `__mro__`, etc.
-   The test expects `config.SECRET_KEY` to raise a security error.

## Next Steps

1.  **Analyze `src/core/prompts/registry.py`**: Review the `SecureSandbox` class.
2.  **Fix `is_safe_attribute`**: Ensure it correctly returns `False` for the cases being tested. You might need to verify how Jinja2 handles `getattr` vs `getitem` in the sandbox.
3.  **Run Tests**: Execute the specific test file.
4.  **Mark Task Done**: Update Archon task `2fc62572-b8cd-4787-8484-c73bc7067ec8` to `done`.

## Upcoming Tasks (Core Framework)

1.  **Structured Output / Response Model** (Task ID: `e8a7b6c5-d4e3-4f2a-9b1c-8d7e6f5a4b3c`)
    -   Implement standardized response wrappers.
    -   Integration with Pydantic output parsers.
2.  **Agent State Management** (Task ID: `b4c9a8d2-1e3f-4a5b-9c8d-7e6f5a4b3c2d`)
    -   Managing agent lifecycle and context window.

## Reference Commands

```bash
# Run specific test
export PYTHONPATH=$PYTHONPATH:. && .venv/bin/pytest tests/unit/core/prompts/test_prompt_manager.py -v

# Check Tasks
mcp__archon__find_tasks(filter_by="status", filter_value="doing")
```
