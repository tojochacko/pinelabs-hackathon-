FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Create venv
RUN uv venv $VIRTUAL_ENV

# Copy dependency manifest and pre-install dependencies (layer cache)
COPY pyproject.toml .
RUN uv pip install --python $VIRTUAL_ENV/bin/python --no-install-project -e .

# Copy source and install the package
COPY . .
RUN uv pip install --python $VIRTUAL_ENV/bin/python -e .

# Output directory must exist
RUN mkdir -p output

# Default: run CB-2024-001. Override with: docker run dispute-ai CB-2024-003
ENTRYPOINT ["python", "-m", "dispute_ai.main"]
CMD ["CB-2024-001"]
