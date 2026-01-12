# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinanceAICrews is a multi-agent financial analysis platform built on CrewAI, featuring collaborative AI agents for stock analysis (fundamental, technical, sentiment) with multi-LLM support, MCP protocol integration for data sources, and a 3-layer subscription-based market data architecture.

**Core Philosophy**: "Code is Engine, Config is Soul" - Variable logic (prompts, workflows, thresholds) belongs in config/DB, not hardcoded.

## Essential Commands

### Backend Development
```bash
# Start backend (FastAPI)
source venv/bin/activate
python -m backend.app.main

# Run tests
pytest tests/
```

### Frontend Development
```bash
cd frontend
npm install           # Install dependencies
npm run dev          # Development mode (port 3000)
npm run build        # Production build
```

### Database Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Docker Deployment
```bash
# Start all services
docker compose up -d

# Or start core services only
docker compose up -d db redis
```

## Architecture Overview

### 3-Layer Data Architecture
```
Layer 1: assets            → Basic info (ticker, name, sector, exchange)
         ↓ Subscription sync
Layer 2: realtime_quotes   → Live snapshots (price, volume, 5min updates)
         ↓ Daily archival
Layer 3: market_prices     → Historical OHLCV data (for agent analysis)
```

### Project Structure

```
FinanceAICrews/
├── AICrews/                    # 🔵 Agent Engine & Business Logic
│   ├── application/crew/       #    Crew assembly, preflight checks
│   ├── services/              #    Business services (analysis, sync)
│   ├── tools/                 #    Tool implementations + registry
│   ├── llm/                   #    Unified LLM management
│   ├── infrastructure/        #    MCP, Redis, Jobs, Storage
│   ├── database/              #    DBManager, Models
│   └── schemas/               #    Pydantic v2 schemas (shared)
│
├── backend/                   # 🟡 FastAPI API Layer
│   └── app/
│       ├── api/v1/endpoints/  #    REST endpoints (thin)
│       ├── ws/                #    WebSocket routes
│       └── core/lifespan.py   #    Startup/shutdown
│
├── frontend/                  # 🔴 Next.js Frontend
│   ├── app/                   #    Pages (App Router)
│   ├── components/            #    Reusable components
│   └── lib/api.ts             # client
│
├── config/                    # ⚪ YAML Configuration
│   ├── agents/                #    Agent personas, tasks, crews
│   ├── llm/                   #    LLM provider configs
│   └── prompts/               #    Prompt templates
│
└── docker/mcp/                # 🟣 MCP Data Servers
    ├── akshare/               #    A-share (China) market data
    └── yfinance/              #    US/Global market data
```

### Key Entry Points

- `AICrews/runner.py`: Config-driven crew execution
- `AICrews/application/crew/assembler.py`: Assembles CrewAI from DB config
- `AICrews/llm/unified_manager.py`: Unified LLM access point
- `backend/app/main.py`: FastAPI app entry
- `frontend/app/layout.tsx`: Root layout

## Development Guidelines

### Layer Separation
- **Backend** (`backend/`): API orchestration ONLY - keep endpoints thin
- **AICrews** (`AICrews/`): Business logic, services, tools
- **Frontend** (`frontend/`): Presentation layer

### Configuration First
- **Don't hardcode** agent personas, task flows, or thresholds
- **Do configure** via `config/agents/*.yaml` or DB updates

### Schema Management
- **All schemas** go in `AICrews/schemas/*` (Pydantic v2)
- Import schemas from `AICrews.schemas.*`

### Tool Development
When adding tools (`AICrews/tools/*`):
1. Input validation: Validate ticker, date ranges, limits
2. Timeout/retry: All external I/O must have timeouts
3. Serializable output: Return JSON-compatible types
4. Error handling: Don't leak secrets/stack traces
5. Register: Add to `AICrews/tools/registry/tool_registry.py`

### Database Access
```python
# Sync context
from AICrews.database.db_manager import DBManager
db = DBManager()
with db.get_session() as session:
    # Your code
    session.commit()

# Async context (in endpoints)
from backend.app.security import get_db
async def endpoint(db: Session = Depends(get_db)):
    # Your code
```

### LLM Usage
- **Always use** `AICrews.llm.unified_manager` - no direct SDK calls
- **Never hardcode** API keys - use environment variables

## URLs & Ports

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/n- **Database**: localhost:5432
- **Redis**: localhost:6379

## Code Style

### Python
- Type hints required
- Google-style docstrings
- PEP 8 compliant

### TypeScript
- Prefer `interface` over `type`
- Strict mode enabled
- Avoid `any`

---

**License**: MIT
