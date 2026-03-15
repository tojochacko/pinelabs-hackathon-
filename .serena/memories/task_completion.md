# What to Do When a Task is Completed

1. **No automatic commits** — never commit unless explicitly asked (per CLAUDE.md).
2. **No tests to run** — no test suite configured.
3. **No linter/formatter** — no ruff, black, or mypy configured.
4. **Update PRIMER.md** in the project root after every session — summarise what was done, current state, and next steps.
5. **Check imports** — ensure all new modules use full package paths (`from dispute_ai.X import Y`).
6. **Verify agent interface** — any new agent must expose `run(state: CaseState) -> CaseState`.
7. **Verify STAGES list** in `pipeline.py` if a new agent is added.
