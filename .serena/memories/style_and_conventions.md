# Code Style and Conventions

## General
- Python 3.11+ syntax (union types with `|`, `match` statements allowed)
- No docstrings on functions (per CLAUDE.md: minimal changes, no extra comments)
- Type hints used on function signatures where meaningful
- No logging to files — console output via `rich` only

## Agent Pattern
Each agent module exposes a single `run(state: CaseState) -> CaseState` function.
Agents are pure functions: receive state, mutate fields, return state.
LLM agents call `call_llm()` from `llm_client.py`. Non-LLM agents are pure Python.

## LLM Calls
- Always via `call_llm(system, user, expect_json=True/False)`
- JSON agents: set `expect_json=True`, parse result dict directly
- Text agents (response_writer): set `expect_json=False`, `max_tokens=1000`
- Retry logic (3 attempts) is inside `call_llm` — agents don't retry

## State
`CaseState` is a `dataclass` in `state.py`. All agents read/write fields on this shared object.
No deep copies — agents mutate state in place and return it.

## Imports
- Relative imports not used — all imports use full package path: `from dispute_ai.state import CaseState`

## Naming
- snake_case for functions and variables
- UPPER_SNAKE_CASE for module-level constants (e.g., `SYSTEM_PROMPT`, `DATA_DIR`)
- Agent files named by role: `classifier.py`, `strategy.py`, etc.

## No-go list (per spec)
- No web server, Flask, FastAPI
- No database
- No LangChain/LangGraph
- No streaming LLM responses
- No async/await outside `pipeline.py`
- No backwards-compat shims
