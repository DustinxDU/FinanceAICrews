FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install basic build tools for any native deps openbb may require
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools

# OpenBB MCP server dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Default host/port; can be overridden by env or docker-compose
ENV OPENBB_MCP_HOST=0.0.0.0
ENV OPENBB_MCP_PORT=8001

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/mcp/ || exit 1

CMD ["openbb-mcp", "--host", "0.0.0.0", "--port", "8001", "--transport", "streamable-http"]
