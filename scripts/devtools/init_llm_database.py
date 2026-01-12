#!/usr/bin/env python3
"""
LLM 种子数据同步脚本

职责：将 LLM 提供商和模型的种子数据同步到数据库
注意：本脚本不负责建表，建表请使用 Alembic 迁移：
    alembic upgrade head

使用方法：
    python scripts/init_llm_database.py
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from AICrews.database.models import Base, LLMProvider, LLMModel
from AICrews.llm.unified_manager import get_unified_llm_manager


def create_database_session(database_url: str = None):
    """创建数据库会话（不再负责建表）"""
    if not database_url:
        import os
        database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql://admin:password123@localhost:5432/financeai'
        )
    
    engine = create_engine(database_url)
    # 注意：不再调用 Base.metadata.create_all(engine)
    # 建表职责已移交给 Alembic 迁移
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def initialize_providers(db_session):
    """初始化LLM提供商"""
    print("🚀 初始化LLM提供商...")
    
    manager = get_unified_llm_manager()
    providers_data = manager.get_all_providers()
    
    created_count = 0
    updated_count = 0
    
    for provider_info in providers_data:
        existing = db_session.query(LLMProvider).filter(
            LLMProvider.provider_key == provider_info["provider_key"]
        ).first()
        
        if existing:
            # 更新现有提供商
            existing.display_name = provider_info["display_name"]
            existing.provider_type = provider_info["provider_type"]
            existing.requires_api_key = provider_info["requires_api_key"]
            existing.requires_base_url = provider_info["requires_base_url"]
            existing.requires_custom_model_name = provider_info["requires_custom_model_name"]
            existing.default_base_url = provider_info.get("default_base_url")
            existing.updated_at = datetime.now()
            updated_count += 1
            print(f"  ✅ 更新提供商: {existing.display_name}")
        else:
            # 创建新提供商
            new_provider = LLMProvider(
                provider_key=provider_info["provider_key"],
                display_name=provider_info["display_name"],
                provider_type=provider_info["provider_type"],
                requires_api_key=provider_info["requires_api_key"],
                requires_base_url=provider_info["requires_base_url"],
                requires_custom_model_name=provider_info["requires_custom_model_name"],
                default_base_url=provider_info.get("default_base_url"),
                sort_order=created_count
            )
            db_session.add(new_provider)
            created_count += 1
            print(f"  🆕 创建提供商: {new_provider.display_name}")
    
    db_session.commit()
    print(f"📊 提供商初始化完成: 创建 {created_count} 个，更新 {updated_count} 个")
    return created_count + updated_count


def initialize_models(db_session):
    """初始化LLM模型"""
    print("\n🧠 初始化LLM模型...")
    
    manager = get_unified_llm_manager()
    total_created = 0
    total_updated = 0
    
    # 获取所有提供商
    providers = db_session.query(LLMProvider).all()
    
    for provider in providers:
        print(f"\n  📝 处理提供商: {provider.display_name}")
        
        # 获取该提供商的模型列表
        models_data = manager.get_provider_models(provider.provider_key)
        
        if not models_data:
            print(f"    ⚠️  没有找到 {provider.display_name} 的模型数据")
            continue
        
        created_count = 0
        updated_count = 0
        
        for model_info in models_data:
            existing = db_session.query(LLMModel).filter(
                LLMModel.provider_id == provider.id,
                LLMModel.model_key == model_info["model_key"]
            ).first()
            
            if existing:
                # 更新现有模型
                existing.display_name = model_info["display_name"]
                existing.context_length = model_info.get("context_length")
                existing.supports_tools = model_info.get("supports_tools", False)
                existing.supports_vision = model_info.get("supports_vision", False)
                existing.recommended_for = model_info.get("recommended_for")
                existing.updated_at = datetime.now()
                existing.last_updated_from_api = datetime.now()
                
                # 火山引擎特殊处理
                if provider.provider_key == "volcengine":
                    existing.volcengine_endpoint_template = "ep-{endpoint_id}"
                
                updated_count += 1
                print(f"    ✅ 更新模型: {existing.display_name}")
            else:
                # 创建新模型
                new_model = LLMModel(
                    provider_id=provider.id,
                    model_key=model_info["model_key"],
                    display_name=model_info["display_name"],
                    context_length=model_info.get("context_length"),
                    supports_tools=model_info.get("supports_tools", False),
                    supports_vision=model_info.get("supports_vision", False),
                    supports_streaming=True,
                    recommended_for=model_info.get("recommended_for"),
                    model_category="general",
                    is_active=True,  # 基础模型表中的模型默认是可用的
                    sort_order=created_count,
                    last_updated_from_api=datetime.now()
                )
                
                # 火山引擎特殊处理
                if provider.provider_key == "volcengine":
                    new_model.volcengine_endpoint_template = "ep-{endpoint_id}"
                
                db_session.add(new_model)
                created_count += 1
                print(f"    🆕 创建模型: {new_model.display_name}")
        
        print(f"    📊 {provider.display_name}: 创建 {created_count} 个，更新 {updated_count} 个")
        total_created += created_count
        total_updated += updated_count
    
    db_session.commit()
    print(f"\n📊 模型初始化完成: 创建 {total_created} 个，更新 {total_updated} 个")
    return total_created + total_updated


def validate_initialization(db_session):
    """验证初始化结果"""
    print("\n🔍 验证初始化结果...")
    
    providers_count = db_session.query(LLMProvider).count()
    models_count = db_session.query(LLMModel).count()
    
    print(f"  📊 数据库统计:")
    print(f"    - 提供商总数: {providers_count}")
    print(f"    - 模型总数: {models_count}")
    
    # 按提供商统计模型
    providers = db_session.query(LLMProvider).all()
    for provider in providers:
        model_count = db_session.query(LLMModel).filter(
            LLMModel.provider_id == provider.id
        ).count()
        print(f"    - {provider.display_name}: {model_count} 个模型")
    
    if providers_count == 0 or models_count == 0:
        print("  ⚠️  警告: 数据库中没有足够的数据")
        return False
    
    print("  ✅ 初始化验证通过")
    return True


async def main():
    """主函数"""
    print("🎯 开始同步 LLM 种子数据...")
    print("=" * 60)
    print("📌 提示：本脚本仅同步种子数据，不负责建表")
    print("   如需建表，请先运行：alembic upgrade head")
    print("=" * 60)
    
    try:
        # 创建数据库连接
        print("\n🔗 连接数据库...")
        db_session = create_database_session()
        
        # 初始化提供商
        providers_count = initialize_providers(db_session)
        
        # 初始化模型
        models_count = initialize_models(db_session)
        
        # 验证结果
        success = validate_initialization(db_session)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 LLM 种子数据同步成功!")
            print(f"📊 总计: {providers_count} 个提供商, {models_count} 个模型")
            
            print("\n📋 下一步操作:")
            print("1. 在前端 LLM 配置页面添加您的 API Key")
            print("2. 验证提供商连接")
            print("3. 配置模型参数")
            print("4. 在 Crew 配置中选择合适的模型")
        else:
            print("❌ 同步过程中出现问题，请检查日志")
            return 1
        
    except Exception as e:
        print(f"\n❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if 'db_session' in locals():
            db_session.close()
    
    return 0


if __name__ == "__main__":
    try:
        # 运行异步主函数
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  初始化被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 未处理的异常: {e}")
        sys.exit(1)
