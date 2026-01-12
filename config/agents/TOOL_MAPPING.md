# Agent YAML Tool Name Mapping

## Overview

The `agents.yaml` file serves as a **template** for initial agent configuration. At runtime, agents are loaded from the **database** (`AgentDefinition` table), not directly from YAML.

This document maps the legacy tool names in YAML templates to the standard tool ID format used by the system.

## Tool Name → Tool ID Mapping

### MCP Tools (mcp_*)

**New Namespaced Format** (v2.0+):

| Legacy Tool Name | Namespaced Tool ID | MCP Server | Description |
|------------------|-------------------|------------|-------------|
| `stock_price` | `mcp_akshare_stock_price` | Akshare | Real-time stock prices (A-shares) |
| `balance_sheet` | `mcp_akshare_balance_sheet` | Akshare | Balance sheet data |
| `stock_info` | `mcp_yfinance_stock_info` | YFinance | Stock information (US/Global) |
| `equity.price.historical` | `mcp_openbb_equity.price.historical` | OpenBB | Historical equity prices |

**Format**: `mcp_{server_key}_{tool_name}`

- `mcp_` prefix indicates this is an MCP tool
- `{server_key}` is the server identifier (e.g., `akshare`, `yfinance`, `openbb`)
- `{tool_name}` is the original tool name from the MCP server

**Backward Compatibility**: Legacy tool names (without `mcp_` prefix) are still supported but will emit deprecation warnings. They will be removed in v3.0.

### Data Tools (data:*)

| YAML Tool Name | Standard Tool ID | Description |
|----------------|------------------|-------------|
| `get_fundamentals` | `data:fundamental:get_fundamentals` | Fetch fundamental data (PE, PS, PB, etc.) |
| `get_financial_statements` | `data:financial:get_financial_statements` | Fetch income statement, balance sheet, cash flow |
| `get_stock_prices` | `data:price:get_stock_price` | Fetch historical OHLCV price data |
| `get_technical_indicators` | `quant:indicator:calculate_indicator` | Calculate technical indicators (MA, RSI, MACD) |

### External Tools (external:*)

| YAML Tool Name | Standard Tool ID | Description |
|----------------|------------------|-------------|
| `get_news` | `external:news:get_stock_news` | Fetch stock-specific news |
| `get_global_news` | `external:news:get_global_news` | Fetch global market news |
| `get_insider_trades` | `external:insider:get_insider_trades` | Fetch insider trading activity |
| `get_social_sentiment` | `external:sentiment:get_social_sentiment` | Fetch social media sentiment |

### Quant Tools (quant:*)

| YAML Tool Name | Standard Tool ID | Description |
|----------------|------------------|-------------|
| `calculate_indicator` | `quant:indicator:calculate_indicator` | Calculate technical indicators |
| `evaluate_strategy` | `quant:expression:evaluate_strategy` | Evaluate quantitative expressions |

## Important Notes

### 1. YAML is Template Only

The `agents.yaml` file is **NOT** used directly at runtime. It serves as:
- Initial seed data for the database
- Documentation for agent personas
- Template for creating new agents

**Runtime behavior**: Agents are loaded from the `AgentDefinition` table in the database.

### 2. Database Tool Bindings

Agent tool bindings are stored in:
- **Modern format**: `AgentDefinition.loadout_data` (4-tier structure: data_tools, quant_tools, external_tools, strategies)
- **Legacy format**: `AgentDefinition.tool_ids` (flat list, deprecated)

Example `loadout_data` structure:
```json
{
  "data_tools": [
    "data:price:get_stock_price",
    "data:fundamental:get_fundamentals"
  ],
  "quant_tools": [
    "quant:indicator:calculate_indicator"
  ],
  "external_tools": [
    "external:news:get_stock_news"
  ],
  "strategies": []
}
```

### 3. Tool Registry Resolution

The `ToolRegistry` automatically resolves tool names to tool objects:
1. Check if tool ID is in standard format (`data:*`, `quant:*`, etc.)
2. If not, attempt legacy name mapping
3. If MCP tool, fetch from MCP server
4. Return tool object with metadata (args_schema, description)

### 4. Migration Path

To update agents from YAML templates to database:

**Option A: Manual Update via Frontend**
1. Open Crew Builder UI
2. Select agent
3. Use Tool Selector to add tools
4. Save agent configuration

**Option B: Database Migration Script**
```bash
# Use the provided migration script
python scripts/migrate_agent_tool_ids.py
```

This script:
- Reads current `AgentDefinition.tool_ids`
- Converts legacy names to standard format
- Updates `loadout_data` structure
- Preserves agent configuration

### 5. Validation

The system validates tool IDs at multiple points:
- **Frontend**: `frontend/lib/validation.ts` validates format before save
- **Backend**: `backend/app/api/v1/endpoints/crew_builder.py` validates on agent create/update
- **Preflight**: `AICrews/application/crew/preflight.py` validates before crew execution

Invalid tool IDs will be rejected with clear error messages.

## Example: Updating an Agent

### Before (YAML Template)
```yaml
fundamental_analyst:
  role: "Senior Fundamental Analyst"
  tools: ["get_fundamentals", "get_financial_statements"]
```

### After (Database)
```python
# AgentDefinition record
{
  "name": "fundamental_analyst",
  "role": "Senior Fundamental Analyst",
  "loadout_data": {
    "data_tools": [
      "data:fundamental:get_fundamentals",
      "data:financial:get_financial_statements"
    ],
    "quant_tools": [],
    "external_tools": [],
    "strategies": []
  }
}
```

## Tool Capability Reference

For detailed tool capabilities and supported operations, see:
- `docs/TOOL_CAPABILITIES.md` - Comprehensive tool documentation
- `docs/TOOL_ID_FORMAT_STANDARD.md` - Tool ID format specification

## FAQ

**Q: Why can't I just use tool names like "get_stock_prices"?**  
A: Legacy names lack namespace information and can cause conflicts. Standard format (`data:price:get_stock_price`) provides:
- Clear capability identification
- Namespace isolation
- Better error messages
- Frontend categorization

**Q: Do I need to update existing YAML files?**  
A: No, YAML files are templates only. Update database records instead.

**Q: What happens if I use an invalid tool ID?**  
A: The system will reject it at validation time with a clear error message pointing to this documentation.

**Q: Can I add custom tools?**  
A: Yes, register them in `AICrews/tools/registry/tool_registry.py` following the standard format.

---

**Last Updated**: 2025-12-30  
**Related Docs**: `docs/TOOL_ID_FORMAT_STANDARD.md`, `config/TOOL_ID_MIGRATION_GUIDE.md`
