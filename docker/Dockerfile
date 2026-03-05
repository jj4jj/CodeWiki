# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*


# Install Claude CLI (claude-code)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Install opencode (CLI Agent)
#RUN curl -fsSL https://opencode.ai/install | bash
#RUN npm install --registry=https://registry.npmmirror.com/
RUN npm install -g opencode-ai --registry=https://registry.npmmirror.com/


# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Persist and prewarm tiktoken cache for environments with unstable outbound SSL/network.
ENV TIKTOKEN_CACHE_DIR=/app/output/tiktoken_cache
RUN mkdir -p "$TIKTOKEN_CACHE_DIR" && \
    python - <<'PY' || true
import tiktoken
print("Prewarming tiktoken encodings into cache...")
for model in ("gpt-4", "gpt-4o"):
    try:
        tiktoken.encoding_for_model(model)
        print(f"  model ok: {model}")
    except Exception as exc:
        print(f"  model skip: {model} ({exc})")
for encoding_name in ("cl100k_base",):
    try:
        tiktoken.get_encoding(encoding_name)
        print(f"  encoding ok: {encoding_name}")
    except Exception as exc:
        print(f"  encoding skip: {encoding_name} ({exc})")
PY

# Copy application code
COPY codewiki ./codewiki
COPY img ./img
COPY pyproject.toml .
COPY README.md .

# Create output directories
RUN mkdir -p output/cache output/temp output/docs output/dependency_graphs "$TIKTOKEN_CACHE_DIR"

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command
CMD ["python", "codewiki/run_web_app.py", "--host", "0.0.0.0", "--port", "8000"]
