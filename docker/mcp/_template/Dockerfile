# MCP Server Template - Replace <SERVER_NAME> with your server name
# Transport: SSE (recommended) or Streamable HTTP

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (add more as needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Environment variables - customize for your server
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=8010

# Expose port
EXPOSE 8010

# Health check - adjust endpoint as needed
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

# Run the server
CMD ["python", "server.py"]
