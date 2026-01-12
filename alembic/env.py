"""
Alembic Environment Configuration for FinanceAICrews

自动从环境变量读取 DATABASE_URL，并导入项目 ORM 模型
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 导入项目的 ORM Base 和所有模型
# 从拆分后的 models 目录导入
from AICrews.database.models.base import Base

# 导入所有模型模块以确保它们被注册
from AICrews.database.models import (
    user, market, llm, mcp, knowledge, 
    agent, cockpit, analysis, insight
)

# Alembic Config 对象
config = context.config

# 从环境变量覆盖 sqlalchemy.url
database_url = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5432/financeai")
config.set_main_option("sqlalchemy.url", database_url)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据 - 用于 autogenerate
# Base.metadata 包含所有已导入的模型
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 比较类型变化
            compare_type=True,
            # 比较服务器默认值
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
