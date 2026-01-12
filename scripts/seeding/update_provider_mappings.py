#!/usr/bin/env python3
"""
Update Provider Capability Mappings

Applies enhanced mapping rules to add more capability mappings for YFinance and Akshare providers.
This script is idempotent - it won't create duplicate mappings.
"""
import sys
from typing import Dict
from AICrews.database.db_manager import DBManager
from AICrews.database.models.mcp import MCPServer, MCPTool
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from sqlalchemy import select


# ============================================================================
# YFINANCE EXTENDED MAPPINGS
# One tool per capability (due to unique constraint on provider_id+capability_id)
# ============================================================================

YFINANCE_MAPPINGS = {
    # Core capabilities - MUST HAVE
    'stock_history': 'equity_history',       # Historical OHLCV data
    'stock_quote': 'equity_quote',           # Real-time quote
    'stock_info': 'equity_fundamentals',     # Company overview (stock_key_stats is subset)

    # Financials - prefer annual cash flow (most comprehensive)
    'stock_cash_flow': 'equity_financials',

    # Corporate actions - dividends as primary
    'stock_dividends': 'equity_corporate_actions',

    # Ownership
    'stock_holders': 'equity_ownership',

    # Earnings
    'stock_earnings': 'equity_earnings',

    # Analyst research
    'stock_recommendations': 'equity_analyst_research',

    # Market overview
    'trending_tickers': 'market_overview',

    # Index data
    'index_history': 'index_history',

    # Funds & ETFs - etf_info as primary
    'etf_info': 'funds_etfs',

    # Options
    'options_chain': 'options',

    # Crypto
    'crypto_quote': 'crypto',

    # Forex
    'forex_quote': 'forex',

    # ESG
    'stock_sustainability': 'esg',
}


# ============================================================================
# AKSHARE EXTENDED MAPPINGS
# One tool per capability (due to unique constraint on provider_id+capability_id)
# ============================================================================

AKSHARE_MAPPINGS = {
    # Core capabilities - MUST HAVE
    'stock_zh_a_hist': 'equity_history',                    # A-share historical data
    'stock_zh_a_spot_em': 'equity_quote',                   # A-share real-time quote
    'stock_balance_sheet_by_report_em': 'equity_financials', # Financial statements
    'stock_financial_analysis_indicator': 'equity_fundamentals',  # Financial indicators

    # Funds & ETFs - spot data as primary
    'fund_etf_spot_em': 'funds_etfs',

    # Futures & Commodities - main contract as primary
    'futures_main_sina': 'futures',

    # Macro indicators - CPI as most commonly referenced
    'macro_china_cpi': 'macro_indicators',

    # Sector/Industry - industry spot as primary
    'stock_board_industry_spot_em': 'sector_industry',

    # Market overview - TTM P/E as primary overview metric
    'stock_a_ttm_lyr': 'market_overview',

    # Order book
    'stock_bid_ask_em': 'equity_orderbook',

    # Fund flow - market level fund flow as primary
    'stock_market_fund_flow': 'fund_flow',

    # Index data
    'index_investing_global': 'index_history',

    # Bonds
    'macro_china_bond_10y': 'bonds',
}


# ============================================================================
# OPENBB EXTENDED MAPPINGS
# One tool per capability (due to unique constraint on provider_id+capability_id)
# ============================================================================

OPENBB_MAPPINGS = {
    # Core capabilities - MUST HAVE
    'equity_price_historical': 'equity_history',      # Historical OHLCV data
    'equity_price_quote': 'equity_quote',             # Real-time quote
    'equity_profile': 'equity_fundamentals',          # Company profile
    'equity_fundamental_income': 'equity_financials', # Financial statements

    # Extended capabilities
    'equity_calendar_earnings': 'equity_earnings',
    'equity_calendar_dividend': 'equity_corporate_actions',
    'equity_ownership_institutional': 'equity_ownership',
    'equity_estimates_price_target': 'equity_analyst_research',
    'equity_discovery_active': 'market_overview',
    'index_price_historical': 'index_history',
    'etf_historical': 'funds_etfs',
    'derivatives_options_chains': 'options',
    'crypto_price_historical': 'crypto',
    'currency_price_historical': 'forex',
    'derivatives_futures_historical': 'futures',
    'equity_fundamental_esg_score': 'esg',
    'economy_cpi': 'macro_indicators',
}


def update_provider_mappings(server_key: str, tool_mappings: Dict[str, str], dry_run: bool = True):
    """
    Update capability mappings for a provider.

    Args:
        server_key: MCP server key (e.g., 'yfinance', 'akshare')
        tool_mappings: Dict mapping tool_name -> capability_id
        dry_run: If True, only show what would be done
    """
    db = DBManager()

    with db.get_session() as session:
        # Get provider
        provider = session.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.provider_key == f'mcp:{server_key}'
            )
        ).scalar_one_or_none()

        if not provider:
            print(f"❌ Provider mcp:{server_key} not found")
            return

        # Get MCP server to access tools
        mcp_server = session.execute(
            select(MCPServer).where(MCPServer.server_key == server_key)
        ).scalar_one_or_none()

        if not mcp_server:
            print(f"❌ MCP Server {server_key} not found")
            return

        # Get existing mappings
        existing_mappings = session.execute(
            select(ProviderCapabilityMapping).where(
                ProviderCapabilityMapping.provider_id == provider.id
            )
        ).scalars().all()

        existing_tools = {m.raw_tool_name: m.capability_id for m in existing_mappings}
        existing_capabilities = {m.capability_id: m.raw_tool_name for m in existing_mappings}

        print(f"\n{'='*70}")
        print(f"{'DRY RUN - ' if dry_run else ''}UPDATE MAPPINGS: {provider.provider_key}")
        print(f"{'='*70}\n")

        print(f"Existing mappings: {len(existing_tools)}")

        # Count what can be added
        to_add = []
        skipped = []

        for tool_name, capability_id in tool_mappings.items():
            # Check if tool exists in MCP server
            tool_exists = session.execute(
                select(MCPTool).where(
                    MCPTool.server_id == mcp_server.id,
                    MCPTool.tool_name == tool_name
                )
            ).scalar_one_or_none()

            if not tool_exists:
                skipped.append((tool_name, "Tool not found in MCP server"))
                continue

            # Check if capability is already mapped
            if capability_id in existing_capabilities:
                if existing_capabilities[capability_id] == tool_name:
                    skipped.append((tool_name, f"Already mapped to {capability_id}"))
                else:
                    skipped.append((tool_name, f"Capability {capability_id} already mapped to {existing_capabilities[capability_id]}"))
                continue

            to_add.append((tool_name, capability_id))

        print(f"Tools to add: {len(to_add)}")
        print(f"Skipped: {len(skipped)}")

        if to_add:
            # Group by capability
            by_capability = {}
            for tool_name, capability_id in to_add:
                if capability_id not in by_capability:
                    by_capability[capability_id] = []
                by_capability[capability_id].append(tool_name)

            print(f"\n--- NEW MAPPINGS ({len(to_add)} tools) ---\n")
            for capability_id in sorted(by_capability.keys()):
                tools = by_capability[capability_id]
                print(f"{capability_id} ({len(tools)} tools):")
                for tool_name in tools[:5]:  # Show first 5
                    print(f"  + {tool_name}")
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more")
                print()

            if not dry_run:
                # Create mappings
                for tool_name, capability_id in to_add:
                    mapping = ProviderCapabilityMapping(
                        provider_id=provider.id,
                        capability_id=capability_id,
                        raw_tool_name=tool_name,
                    )
                    session.add(mapping)

                session.commit()
                print(f"✅ Added {len(to_add)} new mappings")

        if skipped and len(skipped) <= 10:
            print(f"\n--- SKIPPED ({len(skipped)} tools) ---")
            for tool_name, reason in skipped[:10]:
                print(f"  ⊗ {tool_name}: {reason}")

        print(f"\n{'='*70}\n")

        if dry_run:
            print(f"✓ Dry run complete. Run with --execute to apply changes.\n")
        else:
            # Show final summary
            final_mappings = session.execute(
                select(ProviderCapabilityMapping).where(
                    ProviderCapabilityMapping.provider_id == provider.id
                )
            ).scalars().all()
            print(f"✅ Update complete!")
            print(f"   Total mappings: {len(final_mappings)}")

            # Group by capability
            cap_counts = {}
            for m in final_mappings:
                cap_counts[m.capability_id] = cap_counts.get(m.capability_id, 0) + 1

            print(f"\n   Capabilities covered: {len(cap_counts)}")
            for cap_id, count in sorted(cap_counts.items()):
                print(f"   - {cap_id}: {count} tools")
            print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update provider capability mappings")
    parser.add_argument('--execute', action='store_true', help="Actually perform the update (default is dry-run)")
    parser.add_argument('--server', choices=['yfinance', 'akshare', 'openbb', 'all'], default='all',
                        help="Which server to update (default: all)")

    args = parser.parse_args()

    if args.server in ['yfinance', 'all']:
        update_provider_mappings('yfinance', YFINANCE_MAPPINGS, dry_run=not args.execute)

    if args.server in ['akshare', 'all']:
        update_provider_mappings('akshare', AKSHARE_MAPPINGS, dry_run=not args.execute)

    if args.server in ['openbb', 'all']:
        update_provider_mappings('openbb', OPENBB_MAPPINGS, dry_run=not args.execute)


if __name__ == "__main__":
    main()
