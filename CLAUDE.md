# CLAUDE.md

## Communication
- Be concise. Lead with action/answer, skip preamble.
- No emojis unless asked.
- Reference code as `file:line`.

## Code
- Minimal changes — only what's asked.
- No extra comments, docstrings, error handling, or abstractions unless needed.
- Prefer editing existing files over creating new ones.
- No backwards-compat shims for removed code.

## Git
- Never commit unless explicitly asked.
- Never force-push or run destructive git commands without confirmation.

## Session End
- After every session, write/update `PRIMER.md` in the project root summarizing: what was done, current state, and next steps.

## Token Efficiency
- Skip restating the user's request.
- Omit filler text and transitions.
- Use parallel tool calls where possible.
