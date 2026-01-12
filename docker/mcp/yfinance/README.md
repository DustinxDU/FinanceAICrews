# YFinance MCP Server

Standard MCP (Model Context Protocol) server for US and global market data via yfinance library.

## Features

- **Stock Data**: Historical prices, real-time quotes, company info
- **Financial Statements**: Income statement, balance sheet, cash flow (annual & quarterly)
- **Dividends & Splits**: Corporate actions history
- **Holders**: Major, institutional, and mutual fund shareholders
- **Analyst Data**: Recommendations, price targets
- **Options**: Options chain data with calls/puts
- **Cryptocurrency**: BTC, ETH, and other crypto prices
- **Market Overview**: Major indices, sector performance
- **ETF/Index/Forex/Futures**: Historical data for various asset classes
- **ESG**: Sustainability scores

## Tools (35 Core Tools)

| Category | Tools |
|----------|-------|
| Stock Price | `stock_history`, `stock_info`, `stock_key_stats`, `stock_quote` |
| Financials | `stock_income_statement`, `stock_balance_sheet`, `stock_cash_flow`, `stock_quarterly_*` |
| Corporate Actions | `stock_dividends`, `stock_splits`, `stock_actions` |
| Holders | `stock_major_holders`, `stock_institutional_holders`, `stock_mutual_fund_holders` |
| Analyst | `stock_recommendations`, `stock_price_targets` |
| Earnings | `stock_earnings`, `stock_calendar` |
| News | `stock_news` |
| Options | `options_chain`, `options_expirations` |
| Crypto | `crypto_history`, `crypto_info` |
| Market | `market_summary`, `sector_performance`, `trending_tickers` |
| Batch | `download_multiple` |
| ESG | `stock_sustainability` |
| Other | `index_history`, `etf_history`, `etf_info`, `forex_history`, `futures_history` |

## Quick Start

### Docker

```bash
# Build
docker build -t yfinance-mcp .

# Run
docker run -d -p 8010:8010 --name yfinance-mcp yfinance-mcp

# Check health
curl http://localhost:8010/health

# List tools
curl http://localhost:8010/tools

# Call a tool
curl -X POST http://localhost:8010/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "stock_history", "arguments": {"symbol": "AAPL", "period": "1mo"}}'
```

### Docker Compose

```yaml
services:
  yfinance-mcp:
    build: ./docker/mcp/yfinance
    ports:
      - "8010:8010"
    environment:
      - YFINANCE_MCP_CACHE=true
      - YFINANCE_MCP_RATE_LIMIT=120
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tools` | GET | List available tools |
| `/call` | POST | Call a tool directly (REST API) |
| `/sse` | GET | MCP SSE endpoint |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `YFINANCE_MCP_HOST` | `0.0.0.0` | Server host |
| `YFINANCE_MCP_PORT` | `8010` | Server port |
| `YFINANCE_MCP_CACHE` | `true` | Enable caching |
| `YFINANCE_MCP_RATE_LIMIT` | `120` | Requests per minute |

## Cache TTL

| Data Type | TTL (seconds) |
|-----------|---------------|
| Stock Price | 60 |
| Fundamentals | 3600 |
| Financial Statements | 86400 |
| Options | 300 |
| Crypto | 60 |
| News | 300 |
| Info | 3600 |

## Example Usage

### Get Stock History
```json
{
  "tool": "stock_history",
  "arguments": {
    "symbol": "AAPL",
    "period": "3mo",
    "interval": "1d"
  }
}
```

### Get Financial Statements
```json
{
  "tool": "stock_income_statement",
  "arguments": {
    "symbol": "MSFT"
  }
}
```

### Get Options Chain
```json
{
  "tool": "options_chain",
  "arguments": {
    "symbol": "TSLA",
    "date": "2024-01-19"
  }
}
```

### Get Crypto Data
```json
{
  "tool": "crypto_history",
  "arguments": {
    "symbol": "BTC",
    "period": "1mo"
  }
}
```

## Integration with FinanceAI

This MCP server can be integrated with the FinanceAI platform by adding it to the MCP client configuration:

```python
from AICrews.mcp.client import MCPClient

# Connect to YFinance MCP
yfinance_client = MCPClient("http://localhost:8010")

# Call tools
result = await yfinance_client.call_tool("stock_history", {"symbol": "AAPL"})
```
