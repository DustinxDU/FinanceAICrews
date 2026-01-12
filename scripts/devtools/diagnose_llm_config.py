#!/usr/bin/env python3
"""诊断并修复 LLM 配置中的 NULL max_tokens"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AICrews.database.db_manager import DBManager
from AICrews.database.models.llm import (
    UserLLMConfig,
    UserModelConfig,
    CrewAgentLLMConfig,
    LLMModel
)
from sqlalchemy import select


def diagnose_null_max_tokens():
    """诊断所有可能导致 NoneType 比较错误的配置"""
    db = DBManager()

    print("🔍 检查 LLM 配置中的 NULL max_tokens...\n")

    with db.get_session() as session:
        # 检查 UserLLMConfig
        print("1️⃣ 检查 UserLLMConfig.default_max_tokens")
        stmt = select(UserLLMConfig).where(UserLLMConfig.default_max_tokens.is_(None))
        configs = session.execute(stmt).scalars().all()
        print(f"   发现 {len(configs)} 个配置的 default_max_tokens 为 NULL")
        for cfg in configs:
            print(f"   - ID: {cfg.id}, Name: {cfg.config_name}, Provider: {cfg.provider_id}")

        # 检查 UserModelConfig
        print("\n2️⃣ 检查 UserModelConfig.max_tokens")
        stmt = select(UserModelConfig).where(UserModelConfig.max_tokens.is_(None))
        model_configs = session.execute(stmt).scalars().all()
        print(f"   发现 {len(model_configs)} 个配置的 max_tokens 为 NULL")
        for cfg in model_configs:
            stmt_model = select(LLMModel).where(LLMModel.id == cfg.model_id)
            model = session.execute(stmt_model).scalar_one_or_none()
            print(f"   - ID: {cfg.id}, Model: {model.model_key if model else 'Unknown'}, User: {cfg.user_id}")

        # 检查 CrewAgentLLMConfig
        print("\n3️⃣ 检查 CrewAgentLLMConfig.max_tokens")
        stmt = select(CrewAgentLLMConfig).where(CrewAgentLLMConfig.max_tokens.is_(None))
        agent_configs = session.execute(stmt).scalars().all()
        print(f"   发现 {len(agent_configs)} 个配置的 max_tokens 为 NULL")
        for cfg in agent_configs:
            print(f"   - ID: {cfg.id}, Crew: {cfg.crew_name}, Agent: {cfg.agent_role}")

        print("\n" + "="*60)
        print("💡 建议:")
        print("   - 如果发现 NULL 配置,运行 fix_null_max_tokens() 自动修复")
        print("   - 或手动在数据库中设置合理的默认值(如 4096)")
        print("="*60)


def fix_null_max_tokens(default_value: int = 4096, dry_run: bool = True):
    """修复所有 NULL max_tokens 配置

    Args:
        default_value: 默认的 max_tokens 值
        dry_run: 如果为 True,只显示将要修改的内容,不实际执行
    """
    db = DBManager()

    mode = "🔍 DRY RUN 模式" if dry_run else "✏️ 执行修复"
    print(f"{mode} - 设置默认值: {default_value}\n")

    with db.get_session() as session:
        # 修复 UserLLMConfig
        stmt = select(UserLLMConfig).where(UserLLMConfig.default_max_tokens.is_(None))
        configs = session.execute(stmt).scalars().all()
        print(f"1️⃣ 将修复 {len(configs)} 个 UserLLMConfig")
        if not dry_run:
            for cfg in configs:
                cfg.default_max_tokens = default_value
            session.commit()
            print("   ✅ 已提交")

        # 修复 UserModelConfig
        stmt = select(UserModelConfig).where(UserModelConfig.max_tokens.is_(None))
        model_configs = session.execute(stmt).scalars().all()
        print(f"\n2️⃣ 将修复 {len(model_configs)} 个 UserModelConfig")
        if not dry_run:
            for cfg in model_configs:
                cfg.max_tokens = default_value
            session.commit()
            print("   ✅ 已提交")

        # 修复 CrewAgentLLMConfig
        stmt = select(CrewAgentLLMConfig).where(CrewAgentLLMConfig.max_tokens.is_(None))
        agent_configs = session.execute(stmt).scalars().all()
        print(f"\n3️⃣ 将修复 {len(agent_configs)} 个 CrewAgentLLMConfig")
        if not dry_run:
            for cfg in agent_configs:
                cfg.max_tokens = default_value
            session.commit()
            print("   ✅ 已提交")

    if dry_run:
        print("\n⚠️ DRY RUN 完成 - 未实际修改数据")
        print("   运行 fix_null_max_tokens(dry_run=False) 执行实际修复")
    else:
        print("\n✅ 修复完成!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="诊断和修复 LLM 配置中的 NULL max_tokens")
    parser.add_argument("--diagnose", action="store_true", help="仅诊断问题,不修复")
    parser.add_argument("--fix", action="store_true", help="执行修复")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="DRY RUN 模式(默认)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="实际执行修复")
    parser.add_argument("--default-value", type=int, default=4096, help="默认 max_tokens 值(默认4096)")

    args = parser.parse_args()

    if args.fix:
        fix_null_max_tokens(
            default_value=args.default_value,
            dry_run=args.dry_run
        )
    else:
        diagnose_null_max_tokens()
