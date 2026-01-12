#!/usr/bin/env python3
"""
生成合并的 Alembic 迁移文件

此脚本分析所有现有迁移，按依赖顺序排序，
然后生成一个包含所有 schema 变更的单一初始迁移文件。

用法:
    python scripts/generate_consolidated_migration.py [output_path]

    output_path: 输出文件路径 (默认: stdout)
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"


def parse_migration(filepath: Path) -> Dict:
    """解析迁移文件，提取关键信息"""
    content = filepath.read_text()

    # 提取 revision
    rev_match = re.search(r"revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content)
    revision = rev_match.group(1) if rev_match else None

    # 提取 down_revision (可能是 None, 字符串, 或元组)
    down_match = re.search(
        r"down_revision.*?=\s*(?:Union\[.*?\]\s*=\s*)?(None|['\"]([^'\"]+)['\"]|\(([^)]+)\))",
        content
    )
    if down_match:
        if down_match.group(1) == 'None':
            down_revision = None
        elif down_match.group(2):
            down_revision = down_match.group(2)
        elif down_match.group(3):
            # 元组形式 - 取第一个
            tuple_content = down_match.group(3)
            first_match = re.search(r"['\"]([^'\"]+)['\"]", tuple_content)
            down_revision = first_match.group(1) if first_match else None
        else:
            down_revision = None
    else:
        down_revision = None

    # 提取 upgrade 函数
    upgrade_match = re.search(
        r"def upgrade\(\)[^:]*:\s*\n(.*?)(?=\ndef downgrade|\Z)",
        content,
        re.DOTALL
    )
    upgrade_body = upgrade_match.group(1) if upgrade_match else ""

    # 提取 imports
    imports = []
    for line in content.split('\n'):
        if line.startswith('from ') or line.startswith('import '):
            if 'alembic' in line or 'sqlalchemy' in line or 'pgvector' in line:
                imports.append(line)

    return {
        'filepath': filepath,
        'filename': filepath.name,
        'revision': revision,
        'down_revision': down_revision,
        'upgrade_body': upgrade_body,
        'imports': imports,
    }


def sort_migrations(migrations: List[Dict]) -> List[Dict]:
    """按依赖顺序排序迁移"""
    sorted_list = []
    revision_map = {m['revision']: m for m in migrations}
    processed = set()

    # 找到根迁移 (down_revision = None)
    for m in migrations:
        if m['down_revision'] is None:
            sorted_list.append(m)
            processed.add(m['revision'])
            break

    # 按依赖链排序
    max_iterations = len(migrations) * 2
    iterations = 0
    while len(sorted_list) < len(migrations) and iterations < max_iterations:
        iterations += 1
        for m in migrations:
            if m['revision'] in processed:
                continue
            # 检查依赖是否已处理
            if m['down_revision'] in processed:
                sorted_list.append(m)
                processed.add(m['revision'])

    return sorted_list


def generate_consolidated_migration(output_path: Optional[str] = None) -> str:
    """生成合并的迁移文件"""

    # 收集所有迁移
    migrations = []
    for filepath in VERSIONS_DIR.glob("*.py"):
        if filepath.name.startswith('__'):
            continue
        try:
            migration = parse_migration(filepath)
            if migration['revision']:
                migrations.append(migration)
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)

    # 排序
    sorted_migrations = sort_migrations(migrations)

    print(f"找到 {len(migrations)} 个迁移文件", file=sys.stderr)
    print(f"排序后: {len(sorted_migrations)} 个迁移", file=sys.stderr)

    # 收集所有 imports
    all_imports = set()
    for m in sorted_migrations:
        all_imports.update(m['imports'])

    # 生成合并的 upgrade 函数体
    combined_upgrade = []
    for m in sorted_migrations:
        body = m['upgrade_body'].strip()
        if body and body != 'pass':
            combined_upgrade.append(f"    # --- From: {m['filename']} ---")
            # 确保正确缩进 - 所有行都需要 4 空格缩进
            for line in body.split('\n'):
                stripped = line.strip()
                if stripped:
                    # 计算原始缩进
                    original_indent = len(line) - len(line.lstrip())
                    # 确保至少有 4 空格缩进（函数体内）
                    if original_indent < 4:
                        combined_upgrade.append('    ' + stripped)
                    else:
                        combined_upgrade.append(line)
                else:
                    combined_upgrade.append('')
            combined_upgrade.append('')

    # 生成最终文件
    output = f'''"""Initial schema for FinanceAICrews Community Edition.

This is a consolidated migration that creates the complete database schema.
All {len(sorted_migrations)} incremental migrations from development have been squashed into this single file.

For fresh installations:
    1. Configure your DATABASE_URL in .env
    2. Run: alembic upgrade head
    3. Run: python scripts/seeding/seed_all.py

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
'''

    # 添加额外的 imports
    extra_imports = []
    for imp in all_imports:
        if 'pgvector' in imp:
            extra_imports.append(imp)
    if extra_imports:
        output += '\n'.join(extra_imports) + '\n'

    output += '''

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
'''

    if combined_upgrade:
        output += '\n'.join(combined_upgrade)
    else:
        output += '    pass\n'

    output += '''

def downgrade() -> None:
    # Downgrade is not supported for consolidated migration
    # To reset, drop all tables and run upgrade again
    raise NotImplementedError(
        "Downgrade is not supported for consolidated migration. "
        "To reset the database, drop all tables and run 'alembic upgrade head' again."
    )
'''

    if output_path:
        Path(output_path).write_text(output)
        print(f"已生成: {output_path}", file=sys.stderr)

    return output


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_consolidated_migration(output_path)
    if not output_path:
        print(result)
