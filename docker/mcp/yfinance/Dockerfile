FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Environment variables
ENV YFINANCE_MCP_HOST=0.0.0.0
ENV YFINANCE_MCP_PORT=8010
ENV YFINANCE_MCP_CACHE=true
ENV YFINANCE_MCP_RATE_LIMIT=120

# Expose MCP SSE port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

# Run the server
CMD ["python", "server.py"]
