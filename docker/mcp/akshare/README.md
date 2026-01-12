# Akshare MCP Server

Standard MCP server for China A-share market data via [Akshare](https://github.com/akfamily/akshare).

## Overview

This server provides access to China A-share and Hong Kong stock market data through the Model Context Protocol (MCP) using SSE transport.

| Property | Value |
|----------|-------|
| **Transport** | SSE (Server-Sent Events) |
| **Endpoint** | `/sse` |
| **Default Port** | 8009 |
| **Health Check** | `GET /health` |
| **Tools List** | `GET /tools` |

## Quick Start

```bash
# Build and run with docker-compose (from project root)
docker-compose up akshare_mcp -d

# Or build standalone
docker build -t akshare-mcp ./docker/mcp/akshare
docker run -p 8009:8009 akshare-mcp
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AKSHARE_MCP_HOST` | Server bind host | `0.0.0.0` |
| `AKSHARE_MCP_PORT` | Server port | `8009` |
| `AKSHARE_MCP_CACHE` | Enable caching | `true` |
| `AKSHARE_MCP_RATE_LIMIT` | Requests per minute | `60` |

### Cache TTL by Data Type

| Data Type | TTL (seconds) |
|-----------|---------------|
| Stock Price | 60 |
| HK Stock | 60 |
| Fundamentals | 3600 |
| Financial Statements | 86400 |
| Macro Data | 86400 |
| News | 300 |

## MCP Integration

Add to `config/mcp_servers.yaml`:

```yaml
akshare:
  enabled: true
  transport: sse
  url: "http://localhost:8009/sse"
  description: "China A-share market data via Akshare"
  cache_tools_list: true
  tool_filter:
    allowlist: []
    blocklist: []
```

## Available Tools

| Tool | Description |
|------|-------------|
| `akshare_stock_price` | China A-share historical OHLCV data |
| `akshare_hk_stock_price` | Hong Kong stock historical data |
| `akshare_fundamentals` | Financial indicators (profit/balance/cash) |
| `akshare_income_statement` | Income statement data |
| `akshare_balance_sheet` | Balance sheet data |
| `akshare_cashflow` | Cash flow statement data |
| `akshare_macro` | Macro economic data (GDP, CPI, PMI, M2, PPI) |
| `akshare_news` | Market news (sina, eastmoney) |
| `akshare_stock_info` | Basic stock information |

## API Endpoints

```bash
# Health check
curl http://localhost:8009/health

# List available tools (REST, for debugging)
curl http://localhost:8009/tools

# MCP SSE endpoint (for MCP clients)
# Connect via SSE client to: http://localhost:8009/sse
```

## Example Usage

```python
# Via CrewAI native MCP
from crewai import Agent
from crewai.mcp import MCPServerSSE

agent = Agent(
    role="China Market Analyst",
    mcps=[
        MCPServerSSE(
            name="akshare",
            url="http://localhost:8009/sse",
        )
    ]
)
```

## Troubleshooting

```bash
# Check container status
docker ps | grep akshare

# View logs
docker logs akshare_mcp

# Test health endpoint
curl http://localhost:8009/health

# Test tools listing
curl http://localhost:8009/tools
```
