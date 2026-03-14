FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Create venv
RUN uv venv $VIRTUAL_ENV

# Copy source and install
COPY . .
RUN uv pip install --python $VIRTUAL_ENV/bin/python -e .

# Output directory must exist
RUN mkdir -p output

EXPOSE 8000

# Webhook server (use CLI entrypoint by overriding CMD)
CMD ["uvicorn", "dispute_ai.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
