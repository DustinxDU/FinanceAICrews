#!/usr/bin/env python3
"""
Seed Builtin Providers

Populates the database with builtin providers (CrewAI tools) as CapabilityProvider entries
with appropriate capability mappings.

This script is idempotent - it won't create duplicate providers or mappings.

Usage:
    python scripts/seed_builtin_providers.py                    # Dry-run mode
    python scripts/seed_builtin_providers.py --execute          # Execute mode
    python scripts/seed_builtin_providers.py --provider serper  # Seed specific provider
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, List, Optional
from AICrews.database.db_manager import DBManager
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from sqlalchemy import select


# =============================================================================
# BUILTIN PROVIDER DEFINITIONS
# =============================================================================

BUILTIN_PROVIDERS: Dict[str, Dict] = {
    'duckduckgo_search_tool': {
        'provider_key': 'builtin:duckduckgo_search_tool',
        'provider_type': 'builtin_external',
        'name': 'DuckDuckGo Search',
        'description': 'Free web search via DuckDuckGo - no API key required. Rate limited to ~30 req/min, ~500 req/day.',
        'connection_schema': {},  # No API key required - completely free!
        'capabilities': ['web_search'],
        'priority': 10,  # Default choice - free for all users
        'mapping_priority': 50,  # Default mapping priority for free tool
        'enabled': True,
    },
    'serper_dev_tool': {
        'provider_key': 'builtin:serper_dev_tool',
        'provider_type': 'builtin_external',
        'name': 'Serper Dev Tool',
        'description': 'Google search via Serper API - provides web search capability using the Serper.dev service',
        'connection_schema': {
            'requires_env': ['SERPER_API_KEY']
        },
        'capabilities': ['web_search'],
        'priority': 20,  # Higher priority when API key is configured (premium upgrade)
        'mapping_priority': 70,  # Higher mapping priority - user explicitly configured API key
        'enabled': True,
    },
    'scrape_website_tool': {
        'provider_key': 'builtin:scrape_website_tool',
        'provider_type': 'builtin_external',
        'name': 'Website Scraper',
        'description': 'Web page content scraper - extracts text content from web pages using BeautifulSoup',
        'connection_schema': {},  # No env vars required, uses httpx + beautifulsoup
        'capabilities': ['web_scrape'],
        'priority': 10,
        'mapping_priority': 50,  # Default mapping priority
        'enabled': True,
    },
    'firecrawl_tool': {
        'provider_key': 'builtin:firecrawl_tool',
        'provider_type': 'builtin_external',
        'name': 'Firecrawl Tool',
        'description': 'Advanced web scraping via Firecrawl API - handles JavaScript rendering and complex sites',
        'connection_schema': {
            'requires_env': ['FIRECRAWL_API_KEY']
        },
        'capabilities': ['web_scrape'],
        'priority': 20,  # Higher priority than basic scraper
        'mapping_priority': 70,  # Higher mapping priority - premium tool
        'enabled': False,  # Optional, disabled by default
    },
    'file_read_tool': {
        'provider_key': 'builtin:file_read_tool',
        'provider_type': 'builtin_external',
        'name': 'File Read Tool',
        'description': 'Read file contents - reads and returns content from local files',
        'connection_schema': {},
        'capabilities': [],  # No standard capability mapping yet
        'priority': 0,
        'mapping_priority': 50,
        'enabled': False,  # Not mapped to capabilities yet
    },
    'directory_read_tool': {
        'provider_key': 'builtin:directory_read_tool',
        'provider_type': 'builtin_external',
        'name': 'Directory Read Tool',
        'description': 'List directory contents - lists files and directories in a given path',
        'connection_schema': {},
        'capabilities': [],  # No standard capability mapping yet
        'priority': 0,
        'mapping_priority': 50,
        'enabled': False,  # Not mapped to capabilities yet
    },
    # =========================================================================
    # Phase 1: Free Tools (No API Key Required)
    # =========================================================================
    'code_interpreter_tool': {
        'provider_key': 'builtin:code_interpreter_tool',
        'provider_type': 'builtin_external',
        'name': 'Code Interpreter',
        'description': 'Execute Python code for calculations, data analysis, and financial computations. Runs in isolated Docker container.',
        'connection_schema': {},  # No API key required - uses local Docker
        'capabilities': ['code_execution', 'data_analysis'],
        'priority': 10,
        'mapping_priority': 50,
        'enabled': True,
    },
    'scrape_element_from_website_tool': {
        'provider_key': 'builtin:scrape_element_from_website_tool',
        'provider_type': 'builtin_external',
        'name': 'Scrape Element From Website',
        'description': 'Extract specific elements from web pages using CSS selectors. Ideal for extracting stock prices, financial data tables, etc.',
        'connection_schema': {},  # No API key required - uses httpx + beautifulsoup
        'capabilities': ['web_scrape', 'element_extraction'],
        'priority': 15,  # Higher than basic scraper for targeted extraction
        'mapping_priority': 55,  # Slightly higher - more specialized
        'enabled': True,
    },
    'file_writer_tool': {
        'provider_key': 'builtin:file_writer_tool',
        'provider_type': 'builtin_external',
        'name': 'File Writer',
        'description': 'Write content to files. Useful for saving analysis reports, data exports, and generated content.',
        'connection_schema': {},  # No API key required
        'capabilities': ['file_write'],
        'priority': 10,
        'mapping_priority': 50,
        'enabled': True,
    },
    'file_compressor_tool': {
        'provider_key': 'builtin:file_compressor_tool',
        'provider_type': 'builtin_external',
        'name': 'File Compressor',
        'description': 'Compress files into ZIP archives. Useful for packaging multiple reports or data files.',
        'connection_schema': {},  # No API key required
        'capabilities': ['file_compress'],
        'priority': 10,
        'mapping_priority': 50,
        'enabled': True,
    },
    'vision_tool': {
        'provider_key': 'builtin:vision_tool',
        'provider_type': 'builtin_external',
        'name': 'Vision Tool',
        'description': 'Analyze images using LLM vision capabilities. Can analyze K-line charts, financial graphs, and screenshots.',
        'connection_schema': {
            'requires_llm': True,  # Requires a vision-capable LLM (already configured)
        },
        'capabilities': ['image_analysis', 'chart_analysis'],
        'priority': 10,
        'mapping_priority': 50,
        'enabled': True,
    },
    'ocr_tool': {
        'provider_key': 'builtin:ocr_tool',
        'provider_type': 'builtin_external',
        'name': 'OCR Tool',
        'description': 'Extract text from images using OCR. Useful for reading scanned financial reports, receipts, and documents.',
        'connection_schema': {},  # Uses pytesseract (local)
        'capabilities': ['ocr', 'text_extraction'],
        'priority': 10,
        'mapping_priority': 50,
        'enabled': True,
    },
}


# =============================================================================
# SEED FUNCTIONS
# =============================================================================

def seed_builtin_providers(
    dry_run: bool = True,
    provider_filter: Optional[str] = None
) -> None:
    """
    Seed builtin providers into the database.

    Args:
        dry_run: If True, only show what would be done (no database changes)
        provider_filter: If provided, only seed this specific provider (e.g., 'serper_dev_tool')
    """
    db = DBManager()

    # Filter providers if requested
    providers_to_seed = BUILTIN_PROVIDERS
    if provider_filter:
        if provider_filter not in BUILTIN_PROVIDERS:
            print(f"❌ Provider '{provider_filter}' not found in BUILTIN_PROVIDERS")
            print(f"   Available providers: {', '.join(BUILTIN_PROVIDERS.keys())}")
            sys.exit(1)
        providers_to_seed = {provider_filter: BUILTIN_PROVIDERS[provider_filter]}

    with db.get_session() as session:
        print(f"\n{'='*70}")
        print(f"{'DRY RUN - ' if dry_run else ''}SEED BUILTIN PROVIDERS")
        print(f"{'='*70}\n")

        providers_created = 0
        providers_updated = 0
        providers_skipped = 0
        mappings_created = 0
        mappings_skipped = 0

        for provider_id, config in providers_to_seed.items():
            provider_key = config['provider_key']

            print(f"Processing: {config['name']} ({provider_key})")

            # Check if provider already exists
            existing_provider = session.execute(
                select(CapabilityProvider).where(
                    CapabilityProvider.provider_key == provider_key
                )
            ).scalar_one_or_none()

            if existing_provider:
                # Provider exists - check if we need to update it
                needs_update = False
                updates = {}

                if existing_provider.provider_type != config['provider_type']:
                    needs_update = True
                    updates['provider_type'] = config['provider_type']

                if existing_provider.connection_schema != config['connection_schema']:
                    needs_update = True
                    updates['connection_schema'] = config['connection_schema']

                if existing_provider.priority != config['priority']:
                    needs_update = True
                    updates['priority'] = config['priority']

                if needs_update:
                    if not dry_run:
                        for key, value in updates.items():
                            setattr(existing_provider, key, value)
                        session.flush()  # Flush to make changes visible for mappings
                    print(f"  ✓ Updated provider (changes: {', '.join(updates.keys())})")
                    providers_updated += 1
                else:
                    print(f"  ⊗ Provider already exists (no changes needed)")
                    providers_skipped += 1

                provider_obj = existing_provider
            else:
                # Create new provider
                provider_obj = CapabilityProvider(
                    provider_key=provider_key,
                    provider_type=config['provider_type'],
                    connection_schema=config['connection_schema'],
                    enabled=config['enabled'],
                    healthy=False,  # Will be set by health checks
                    priority=config['priority'],
                )

                if not dry_run:
                    session.add(provider_obj)
                    session.flush()  # Flush to get ID without committing
                    session.refresh(provider_obj)

                print(f"  + Created provider (enabled={config['enabled']}, priority={config['priority']})")
                providers_created += 1

            # Process capability mappings
            if config['capabilities']:
                print(f"  Capabilities: {', '.join(config['capabilities'])}")

                # Get existing mappings - for existing providers, check even in dry-run
                if provider_obj.id:
                    existing_mappings = session.execute(
                        select(ProviderCapabilityMapping).where(
                            ProviderCapabilityMapping.provider_id == provider_obj.id
                        )
                    ).scalars().all()
                else:
                    # New provider in dry-run - no existing mappings to check
                    existing_mappings = []

                existing_cap_ids = {m.capability_id for m in existing_mappings}

                for capability_id in config['capabilities']:
                    if capability_id in existing_cap_ids:
                        print(f"    ⊗ Capability '{capability_id}' already mapped")
                        mappings_skipped += 1
                    else:
                        if not dry_run and provider_obj.id:
                            # Get mapping priority from config (default 50)
                            mapping_priority = config.get('mapping_priority', 50)
                            mapping = ProviderCapabilityMapping(
                                provider_id=provider_obj.id,
                                capability_id=capability_id,
                                raw_tool_name=provider_id,  # Use provider_id as raw tool name
                                priority=mapping_priority,  # Use configured priority
                            )
                            session.add(mapping)

                        print(f"    + Mapped capability '{capability_id}' (priority={config.get('mapping_priority', 50)})")
                        mappings_created += 1
            else:
                print(f"  ⚠ No capabilities defined (provider not yet integrated)")

            print()  # Blank line between providers

        # Commit all changes for all providers in a single transaction
        if not dry_run:
            session.commit()

        # Summary
        print(f"{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        print(f"Providers created:  {providers_created}")
        print(f"Providers updated:  {providers_updated}")
        print(f"Providers skipped:  {providers_skipped}")
        print(f"Mappings created:   {mappings_created}")
        print(f"Mappings skipped:   {mappings_skipped}")
        print()

        if dry_run:
            print(f"✓ Dry run complete. Run with --execute to apply changes.\n")
        else:
            print(f"✅ Seed complete!\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed builtin providers into the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default)
  python scripts/seed_builtin_providers.py

  # Execute changes
  python scripts/seed_builtin_providers.py --execute

  # Seed only serper_dev_tool
  python scripts/seed_builtin_providers.py --execute --provider serper_dev_tool

Available providers:
  - duckduckgo_search_tool         : Free web search (no API key)
  - serper_dev_tool                : Google search via Serper API
  - scrape_website_tool            : Basic web scraping
  - firecrawl_tool                 : Advanced web scraping (optional)
  - file_read_tool                 : File reading (not yet mapped)
  - directory_read_tool            : Directory listing (not yet mapped)

  Phase 1 Free Tools:
  - code_interpreter_tool          : Execute Python code (Docker)
  - scrape_element_from_website_tool: Extract specific web elements
  - file_writer_tool               : Write files
  - file_compressor_tool           : Compress files to ZIP
  - vision_tool                    : Analyze images (requires LLM)
  - ocr_tool                       : Extract text from images
        """
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help="Actually perform the seed (default is dry-run)"
    )
    parser.add_argument(
        '--provider',
        choices=list(BUILTIN_PROVIDERS.keys()),
        help="Only seed specific provider"
    )

    args = parser.parse_args()

    try:
        seed_builtin_providers(
            dry_run=not args.execute,
            provider_filter=args.provider
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if "--execute" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
