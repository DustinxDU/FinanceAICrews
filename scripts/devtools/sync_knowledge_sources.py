#!/usr/bin/env python3
"""
Knowledge Sources Sync Script

Syncs knowledge sources to the database for frontend display.
Creates proper knowledge sources with correct tiers and categories.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AICrews.database.db_manager import DBManager
from AICrews.database.models import KnowledgeSource, User, UserKnowledgeSubscription


# Knowledge sources configuration
KNOWLEDGE_SOURCES = [
    # Free Investment Philosophy
    {
        "source_key": "buffett_letters",
        "display_name": "巴菲特致股东信",
        "description": "沃伦·巴菲特历年致伯克希尔·哈撒韦股东的信件合集，包含价值投资的核心理念和实战智慧。",
        "source_type": "file",
        "category": "investment_philosophy",
        "scope": "system",
        "tier": "free",
        "icon": "📜",
        "tags": ["buffett", "value_investing", "philosophy", "letters"]
    },
    {
        "source_key": "intelligent_investor",
        "display_name": "聪明的投资者",
        "description": "本杰明·格雷厄姆的经典著作，被誉为价值投资的圣经，巴菲特推荐的必读书籍。",
        "source_type": "file",
        "category": "investment_books",
        "scope": "system",
        "tier": "free",
        "icon": "📚",
        "tags": ["graham", "value_investing", "classic", "book"]
    },
    {
        "source_key": "security_analysis",
        "display_name": "证券分析",
        "description": "格雷厄姆与多德合著的投资分析经典，详细阐述了证券估值的方法论。",
        "source_type": "file",
        "category": "investment_books",
        "scope": "system",
        "tier": "free",
        "icon": "📊",
        "tags": ["graham", "dodd", "analysis", "valuation"]
    },
    {
        "source_key": "poor_charlies_almanack",
        "display_name": "穷查理宝典",
        "description": "查理·芒格的智慧箴言集，涵盖多元思维模型和投资哲学。",
        "source_type": "file",
        "category": "investment_philosophy",
        "scope": "system",
        "tier": "free",
        "icon": "🧠",
        "tags": ["munger", "mental_models", "philosophy"]
    },
    
    # Premium Market Data
    {
        "source_key": "fed_minutes",
        "display_name": "美联储会议纪要",
        "description": "美联储FOMC会议纪要和政策声明，包含货币政策走向的关键信息。",
        "source_type": "api",
        "category": "monetary_policy",
        "scope": "system",
        "tier": "premium",
        "icon": "🏛️",
        "tags": ["fed", "fomc", "monetary_policy", "macroeconomics"]
    },
    {
        "source_key": "earnings_transcripts",
        "display_name": "财报电话会议记录",
        "description": "标普500公司季度财报电话会议的完整记录，包含管理层问答。",
        "source_type": "api",
        "category": "earnings",
        "scope": "system",
        "tier": "premium",
        "icon": "📞",
        "tags": ["earnings", "transcripts", "sp500", "quarterly"]
    },
    {
        "source_key": "institutional_research",
        "display_name": "机构研究报告",
        "description": "来自顶级投行和研究机构的深度研究报告，包含行业分析和个股推荐。",
        "source_type": "api",
        "category": "research",
        "scope": "system",
        "tier": "premium",
        "icon": "🔬",
        "tags": ["research", "institutional", "analysis", "reports"]
    },
    {
        "source_key": "sec_filings",
        "display_name": "SEC 监管文件",
        "description": "美国证券交易委员会的公司监管文件，包含10-K、10-Q、8-K等重要披露。",
        "source_type": "api",
        "category": "regulatory",
        "scope": "system",
        "tier": "premium",
        "icon": "📋",
        "tags": ["sec", "filings", "10k", "regulatory"]
    },
    
    # China Market Premium
    {
        "source_key": "china_policy_docs",
        "display_name": "中国政策文件库",
        "description": "中国重要经济政策文件汇编，包含五年规划、行业政策、监管文件等。",
        "source_type": "file",
        "category": "policy",
        "scope": "system",
        "tier": "premium",
        "icon": "🇨🇳",
        "tags": ["china", "policy", "regulation", "government"]
    },
    {
        "source_key": "china_research_reports",
        "display_name": "中国券商研报",
        "description": "国内头部券商的研究报告，覆盖A股市场的行业和个股分析。",
        "source_type": "api",
        "category": "research",
        "scope": "system",
        "tier": "premium",
        "icon": "📈",
        "tags": ["china", "research", "a_stock", "broker"]
    },
    
    # Strategy & Trading
    {
        "source_key": "trading_strategies",
        "display_name": "量化交易策略库",
        "description": "经过验证的量化交易策略集合，包含因子模型、动量策略、均值回归等。",
        "source_type": "file",
        "category": "strategy",
        "scope": "system",
        "tier": "premium",
        "icon": "⚡",
        "tags": ["quant", "strategy", "trading", "factors"]
    },
    {
        "source_key": "risk_management",
        "display_name": "风险管理框架",
        "description": "专业的投资组合风险管理方法论，包含VaR、压力测试、情景分析等。",
        "source_type": "file",
        "category": "risk",
        "scope": "system",
        "tier": "premium",
        "icon": "🛡️",
        "tags": ["risk", "management", "var", "portfolio"]
    },
    
    # Market History
    {
        "source_key": "market_history_crashes",
        "display_name": "历史市场崩盘案例",
        "description": "历史上重大市场崩盘事件的详细分析，包含1929、1987、2000、2008等。",
        "source_type": "file",
        "category": "market_history",
        "scope": "system",
        "tier": "free",
        "icon": "📉",
        "tags": ["history", "crash", "crisis", "lessons"]
    },
    {
        "source_key": "bubble_analysis",
        "display_name": "泡沫分析研究",
        "description": "金融泡沫的形成机制和识别方法研究，帮助识别市场过热信号。",
        "source_type": "file",
        "category": "market_history",
        "scope": "system",
        "tier": "free",
        "icon": "🫧",
        "tags": ["bubble", "analysis", "speculation", "history"]
    },
]


def sync_knowledge_sources(session) -> int:
    """Sync knowledge sources to database"""
    print("📚 Syncing knowledge sources...")
    
    synced_count = 0
    
    for ks_data in KNOWLEDGE_SOURCES:
        source_key = ks_data["source_key"]
        
        # Check if source already exists
        existing = session.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key
        ).first()
        
        if existing:
            # Update existing source
            existing.display_name = ks_data["display_name"]
            existing.description = ks_data["description"]
            existing.source_type = ks_data["source_type"]
            existing.category = ks_data["category"]
            existing.scope = ks_data["scope"]
            existing.tier = ks_data["tier"]
            existing.icon = ks_data.get("icon")
            existing.tags = ks_data.get("tags", [])
            existing.is_active = True
            existing.updated_at = datetime.now()
            print(f"  ✅ Updated: {ks_data['display_name']}")
        else:
            # Create new source
            new_source = KnowledgeSource(
                source_key=source_key,
                display_name=ks_data["display_name"],
                description=ks_data["description"],
                source_type=ks_data["source_type"],
                category=ks_data["category"],
                scope=ks_data["scope"],
                tier=ks_data["tier"],
                icon=ks_data.get("icon"),
                tags=ks_data.get("tags", []),
                is_system=True,
                is_active=True
            )
            session.add(new_source)
            print(f"  ✅ Created: {ks_data['display_name']}")
        
        synced_count += 1
    
    return synced_count


def setup_user_subscriptions(session, user_id: int):
    """Setup default subscriptions for a user"""
    print(f"\n👤 Setting up subscriptions for user {user_id}...")
    
    # Get all free sources
    free_sources = session.query(KnowledgeSource).filter(
        KnowledgeSource.tier == "free",
        KnowledgeSource.is_active == True
    ).all()
    
    subscribed = 0
    for source in free_sources:
        existing = session.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == user_id,
            UserKnowledgeSubscription.source_id == source.id
        ).first()
        
        if not existing:
            subscription = UserKnowledgeSubscription(
                user_id=user_id,
                source_id=source.id,
                is_active=True
            )
            session.add(subscription)
            subscribed += 1
    
    print(f"  ✅ Subscribed to {subscribed} free knowledge sources")
    return subscribed


def main():
    """Main function"""
    print("🚀 Knowledge Sources Sync")
    print("=" * 60)
    
    db = DBManager()
    session = db.get_session()
    
    try:
        # Sync knowledge sources
        synced = sync_knowledge_sources(session)
        
        # Get or create test user
        test_user = session.query(User).filter(
            User.email == "test@financeai.com"
        ).first()
        
        if test_user:
            setup_user_subscriptions(session, test_user.id)
        
        session.commit()
        
        print(f"\n{'=' * 60}")
        print(f"🎉 Sync completed!")
        
        # Print summary
        print(f"\n📊 Knowledge Sources Summary:")
        free_count = session.query(KnowledgeSource).filter(
            KnowledgeSource.tier == "free"
        ).count()
        premium_count = session.query(KnowledgeSource).filter(
            KnowledgeSource.tier == "premium"
        ).count()
        
        print(f"  - Free sources: {free_count}")
        print(f"  - Premium sources: {premium_count}")
        print(f"  - Total: {free_count + premium_count}")
        
        # List by category
        print(f"\n📂 By Category:")
        categories = session.query(KnowledgeSource.category).distinct().all()
        for (category,) in categories:
            count = session.query(KnowledgeSource).filter(
                KnowledgeSource.category == category
            ).count()
            print(f"  - {category}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
