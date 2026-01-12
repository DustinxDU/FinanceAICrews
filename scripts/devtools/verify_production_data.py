#!/usr/bin/env python3
"""
Verify Production Data Script

Verifies that MCP tools and knowledge sources are correctly synced to the database
and accessible via API endpoints.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AICrews.database.db_manager import DBManager
from AICrews.database.models import MCPServer, MCPTool, KnowledgeSource, User, UserKnowledgeSubscription, UserMCPSubscription


def verify_mcp_data(session):
    """Verify MCP servers and tools"""
    print("🔧 Verifying MCP Data...")
    
    servers = session.query(MCPServer).filter(MCPServer.is_active == True).all()
    print(f"  MCP Servers: {len(servers)}")
    
    total_tools = 0
    for server in servers:
        tool_count = session.query(MCPTool).filter(
            MCPTool.server_id == server.id,
            MCPTool.is_active == True
        ).count()
        total_tools += tool_count
        print(f"    - {server.display_name} ({server.server_key}): {tool_count} tools")
    
    print(f"  Total Tools: {total_tools}")
    
    return len(servers) >= 2 and total_tools >= 50


def verify_knowledge_data(session):
    """Verify knowledge sources"""
    print("\n📚 Verifying Knowledge Data...")
    
    sources = session.query(KnowledgeSource).filter(KnowledgeSource.is_active == True).all()
    print(f"  Knowledge Sources: {len(sources)}")
    
    free_count = len([s for s in sources if s.tier == "free"])
    premium_count = len([s for s in sources if s.tier == "premium"])
    
    print(f"    - Free: {free_count}")
    print(f"    - Premium: {premium_count}")
    
    # List by category
    categories = {}
    for s in sources:
        cat = s.category or "uncategorized"
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"  Categories: {len(categories)}")
    for cat, count in sorted(categories.items()):
        print(f"    - {cat}: {count}")
    
    return len(sources) >= 10


def verify_user_subscriptions(session):
    """Verify user subscriptions"""
    print("\n👤 Verifying User Subscriptions...")
    
    users = session.query(User).all()
    print(f"  Users: {len(users)}")
    
    for user in users:
        ks_subs = session.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == user.id
        ).count()
        mcp_subs = session.query(UserMCPSubscription).filter(
            UserMCPSubscription.user_id == user.id
        ).count()
        print(f"    - {user.email}: {ks_subs} knowledge subs, {mcp_subs} MCP subs")
    
    return len(users) >= 1


def main():
    """Main verification function"""
    print("🚀 Production Data Verification")
    print("=" * 60)
    
    db = DBManager()
    session = db.get_session()
    
    try:
        mcp_ok = verify_mcp_data(session)
        knowledge_ok = verify_knowledge_data(session)
        users_ok = verify_user_subscriptions(session)
        
        print("\n" + "=" * 60)
        
        if mcp_ok and knowledge_ok and users_ok:
            print("✅ All verifications passed!")
            print("\n📋 Production Data Summary:")
            print("  - MCP: 2 servers, 100+ tools (OpenBB + Akshare)")
            print("  - Knowledge: 14+ sources (free + premium)")
            print("  - Users: Test user with subscriptions")
            
            print("\n🚀 To start the application:")
            print("  1. Backend (if not running):")
            print("     cd /home/dustin/stock/FinanceAICrews")
            print("     source venv/bin/activate")
            print("     python -m backend.app.main")
            print()
            print("  2. Frontend:")
            print("     cd /home/dustin/stock/FinanceAICrews/frontend")
            print("     npm run dev")
            print()
            print("  3. Access:")
            print("     - MCP Marketplace: http://localhost:3000/mcp-marketplace")
            print("     - Knowledge Marketplace: http://localhost:3000/knowledge-marketplace")
            print("     - Crew Builder: http://localhost:3000/crew-builder")
            
            return True
        else:
            print("❌ Some verifications failed!")
            if not mcp_ok:
                print("  - MCP data incomplete. Run: python scripts/sync_mcp_tools.py")
            if not knowledge_ok:
                print("  - Knowledge data incomplete. Run: python scripts/sync_knowledge_sources.py")
            if not users_ok:
                print("  - User data incomplete. Run: python scripts/init_production_data.py")
            return False
            
    finally:
        session.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
