# Suggested Commands

## Setup (first time)
```bash
cd dispute_ai
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Run (local)
```bash
# Ensure Ollama is running with gemma3
ollama pull gemma3
ollama serve

# Run scenarios
python -m dispute_ai.main CB-2024-001   # strong case → file_dispute
python -m dispute_ai.main CB-2024-002   # moderate case → file_dispute
python -m dispute_ai.main CB-2024-003   # weak case → settle_with_customer
```

## Run (Docker)
```bash
cd dispute_ai
docker compose build
docker compose run dispute-ai CB-2024-001
docker compose run dispute-ai CB-2024-003
```

## No linting/testing commands defined
The spec explicitly says: do not add unit tests unless asked. No formatter or linter configured.

## Git
```bash
git status
git log --oneline
```
