# OpenBB MCP Server

OpenBB MCP server for global market data access via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Overview

This server wraps the official `openbb-mcp-server` package, providing access to OpenBB's extensive financial data APIs through MCP.

| Property | Value |
|----------|-------|
| **Transport** | Streamable HTTP |
| **Endpoint** | `/mcp` |
| **Container Port** | 8001 |
| **Host Port (default)** | 8008 (mapped via docker-compose) |
| **Health Check** | `GET /mcp/` |

## Quick Start

```bash
# Build and run with docker-compose (from project root)
docker-compose up openbb_mcp -d

# Or build standalone
docker build -t openbb-mcp ./docker/mcp/openbb
docker run -p 8001:8001 openbb-mcp
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENBB_MCP_HOST` | Server bind host | `0.0.0.0` |
| `OPENBB_MCP_PORT` | Server port | `8001` |
| `OPENBB_MCP_DEFAULT_TOOL_CATEGORIES` | Tool categories to expose | `equity,news` |

### Data Providers & API Keys

OpenBB supports multiple data providers. Configure API keys via environment variables or the Tools → Providers UI.

#### Market Data
| Provider | Env Variable | Description |
|----------|--------------|-------------|
| **Polygon.io** | `OPENBB_POLYGON_API_KEY` | US equities, options, forex, crypto (Free: 5 req/min) |
| **Alpha Vantage** | `OPENBB_ALPHA_VANTAGE_API_KEY` | Stocks, forex, crypto, technical indicators |
| **Finnhub** | `OPENBB_FINNHUB_API_KEY` | Real-time quotes, estimates, earnings |
| **Yahoo Finance** | - | Free tier (default, no key required) |

#### Fundamentals
| Provider | Env Variable | Description |
|----------|--------------|-------------|
| **FMP** | `OPENBB_FMP_API_KEY` | Fundamentals, financials, real-time quotes |
| **Intrinio** | `OPENBB_INTRINIO_API_KEY` | Institutional-grade fundamentals |

#### News & Sentiment
| Provider | Env Variable | Description |
|----------|--------------|-------------|
| **Benzinga** | `OPENBB_BENZINGA_API_KEY` | News, analyst ratings, corporate actions |
| **News API** | `OPENBB_NEWSAPI_API_KEY` | Global news from 80,000+ sources |

#### Economic Data
| Provider | Env Variable | Description |
|----------|--------------|-------------|
| **FRED** | `OPENBB_FRED_API_KEY` | Federal Reserve economic data (GDP, CPI, rates) |
| **Trading Economics** | `OPENBB_TRADINGECONOMICS_API_KEY` | Global macro indicators, forecasts |

#### Crypto & Options
| Provider | Env Variable | Description |
|----------|--------------|-------------|
| **CoinMarketCap** | `OPENBB_COINMARKETCAP_API_KEY` | Cryptocurrency prices, market cap |
| **Tradier** | `OPENBB_TRADIER_API_KEY` | Options chains, brokerage integration |

> **Note**: API keys can also be configured per-user via the Tools → Providers page in the UI.

## MCP Integration

Add to `config/mcp_servers.yaml`:

```yaml
openbb:
  enabled: true
  transport: streamable_http
  # Host port 8008 maps to container port 8001
  url: "http://localhost:8008/mcp"
  description: "OpenBB global market data"
  cache_tools_list: true
  tool_filter:
    allowlist: []  # Empty = all tools
    blocklist: []
```

> **Note**: Use environment variable `OPENBB_MCP_URL` to configure the URL. Default: `http://localhost:8008/mcp`

## Available Tools

The server exposes OpenBB's tools based on `OPENBB_MCP_DEFAULT_TOOL_CATEGORIES`:

- **equity** - Stock quotes, historical data, fundamentals
- **news** - Market news, company news
- **economy** - Economic indicators
- **crypto** - Cryptocurrency data
- **forex** - Foreign exchange rates

## Troubleshooting

```bash
# Check health (use host port 8008)
curl http://localhost:8008/mcp/

# View logs
docker logs openbb_mcp

# Test tool listing (via MCP client)
# Tools are discovered via the MCP protocol, not REST
```
