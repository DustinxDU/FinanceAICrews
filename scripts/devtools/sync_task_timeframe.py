#!/usr/bin/env python3
"""
同步 tasks.yaml 中的 {timeframe} 占位符到数据库

此脚本将更新 TaskDefinition 表中的 description 字段，
添加 {timeframe} 占位符以确保 Agent 知道分析的时间范围。

Usage:
    python scripts/sync_task_timeframe.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AICrews.database.db_manager import DBManager
from AICrews.database.models import TaskDefinition
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# 任务名称到新描述的映射（从 tasks.yaml 中提取）
TASK_DESCRIPTION_UPDATES = {
    "Fundamental Deep Dive": """Conduct a comprehensive fundamental analysis of {ticker} for the {timeframe} horizon.
**Steps:**
1. **Financial Health**: Analyze Balance Sheet.
2. **Profitability**: Analyze Income Statement margins.
3. **Cash Flow**: Check Free Cash Flow trends.
4. **Valuation**: Compare PE, PB vs historicals.
State "N/A" if data missing.""",

    "Sentiment & News Scan": """Analyze market sentiment for {ticker} over the {timeframe} period.
**Steps:**
1. News tone and major headlines
2. Insider transactions / institutional flows (if available)
3. Social/alt data signals
State "Data Unavailable" if missing.""",

    "Trading Plan": """Turn the verdict into an actionable trading plan for {ticker} with a {timeframe} horizon.
Include entry, stops, targets, sizing, and time horizon.""",

    "Economic Cycle Analysis": """Analyze the current position in debt cycles for a {timeframe} investment horizon.
**Steps:**
1. **Short-term Cycle**: Where are we in the 5-8 year cycle?
2. **Long-term Cycle**: Assess debt/GDP trends.
3. **Policy**: Analyze central bank stance (Hawkish/Dovish).""",

    "Macro Fit Analysis": """Analyze how {ticker} fits into the current macro regime for a {timeframe} investment horizon.
Does it benefit from the current cycle phase?
Build a Bull/Bear case based purely on macro factors.""",

    "Risk Parity Allocation": """Determine position sizing for {ticker} based on volatility and correlation over {timeframe}.
Ensure it fits a risk parity framework (equal risk contribution).""",

    "Intrinsic Value Calculation": """Calculate intrinsic value for {ticker} using Buffett's methods with a {timeframe} holding period perspective.
**Steps:**
1. **Owner Earnings**: Net Income + Depr - CapEx.
2. **Moat Check**: Is there a durable advantage?
3. **Margin of Safety**: Compare Price vs Value.""",

    "Final Value Verdict": """Make a final Buy/Pass decision for {ticker} with a {timeframe} holding period based on the 4 Buffett tenets:
1. Understandable business?
2. Favorable long-term prospects?
3. Honest/Competent management?
4. Sensible price?""",

    "Market Narrative Scan": """Identify the dominant story driving {ticker}'s price over the {timeframe} trade horizon.
What do the Bulls believe? What do the Bears believe?""",

    "Reflexivity Mapping": """Identify feedback loops for {ticker} within the {timeframe} trade horizon.
**Steps:**
1. **Premise Test**: Is the market narrative factually true?
2. **Loop Check**: Is price influencing fundamentals? (e.g. high stock price -> cheap capital -> growth).
3. **Boom/Bust**: Where are we in the cycle?""",

    "Asymmetric Trade Structure": """Structure a trade for {ticker} with a {timeframe} horizon, targeting limited downside and high upside based on the reflexivity analysis.
"Find the trend whose premise is false, and bet against it.\""""
}


def sync_task_descriptions(dry_run: bool = False):
    """同步任务描述到数据库"""
    db = DBManager()
    updated_count = 0
    skipped_count = 0

    with db.get_session() as session:
        for task_name, new_description in TASK_DESCRIPTION_UPDATES.items():
            # 查找所有匹配名称的任务
            tasks = session.query(TaskDefinition).filter(
                TaskDefinition.name == task_name
            ).all()

            for task in tasks:
                # 检查是否已经有 {timeframe}
                if "{timeframe}" in task.description:
                    logger.info(f"[SKIP] Task {task.id} '{task.name}' already has {{timeframe}}")
                    skipped_count += 1
                    continue

                if dry_run:
                    logger.info(f"[DRY-RUN] Would update Task {task.id} '{task.name}'")
                    logger.debug(f"  Old: {task.description[:80]}...")
                    logger.debug(f"  New: {new_description[:80]}...")
                else:
                    task.description = new_description
                    logger.info(f"[UPDATED] Task {task.id} '{task.name}'")

                updated_count += 1

        if not dry_run:
            session.commit()
            logger.info(f"Committed {updated_count} updates to database")

    return updated_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description="Sync {timeframe} placeholder to TaskDefinition descriptions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Task Description Sync - Adding {timeframe} placeholder")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY-RUN MODE] No changes will be made\n")

    updated, skipped = sync_task_descriptions(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Updated: {updated}")
    print(f"  - Skipped (already has {{timeframe}}): {skipped}")
    print("=" * 60)

    if args.dry_run and updated > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
