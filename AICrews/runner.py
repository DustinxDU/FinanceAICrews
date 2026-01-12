"""
Configuration-Driven Crew Runner - 配置驱动的 Crew 执行器

4 层架构的统一入口点
支持多种投资风格（Standard, Buffett, Bridgewater, Soros）

Library 集成：
- 分析完成后自动写入 user_asset_insights, insight_traces, insight_attachments 表
"""

import asyncio
import os
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from AICrews.observability.logging import get_logger
from AICrews.application.crew import get_crew_assembler
from AICrews.database.db_manager import DBManager
from AICrews.database.models import CrewDefinition, User
from AICrews.database.vector_utils import VectorUtil
from AICrews.config import get_settings
from AICrews.config.constants import AGENT_ROLE_TO_REPORT_TYPE

logger = get_logger(__name__)


class CrewRunner:
    """
    配置驱动的 Crew 执行器
    
    支持:
    1. 多种投资风格切换
    2. 原生知识源集成 (CrewAI Knowledge Sources)
    3. 结果归档到数据库
    4. MCP 工具自动初始化
    """
    
    def __init__(
        self,
        config_dir: Optional[str] = None,
        deep_model_name: Optional[str] = None,
        light_model_name: Optional[str] = None,
        enable_mcp: bool = True,
    ):
        self.config_dir = config_dir
        self.enable_mcp = enable_mcp
        
        # 初始化 Assembler
        self.assembler = get_crew_assembler()
        
        # 数据库管理器
        try:
            self.db = DBManager()
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            self.db = None
        
        self._mcp_initialized = False
        
        if deep_model_name or light_model_name:
            logger.info("Model overrides provided but currently ignored by CrewAssembler (uses DB config)")
    
    async def _init_mcp(self) -> None:
        """初始化 MCP 连接（已弃用自研管理器，使用 CrewAI 原生 MCP 自动处理）"""
        self._mcp_initialized = True  # no-op placeholder
    
    def _resolve_crew_id(self, crew_name_or_key: str, session) -> Optional[int]:
        """Resolve crew name/key to DB ID"""
        # 1. Exact Name Match
        crew = session.query(CrewDefinition).filter_by(name=crew_name_or_key, is_active=True).first()
        if crew: return crew.id
        
        # 2. Key Mapping (CLI friendly names)
        mapping = {
            "standard": "Standard Stock Analysis",
            "buffett": "Buffett Value Investing",
            "bridgewater": "Bridgewater Macro Strategy",
            "soros": "Soros Reflexivity Trading"
        }
        mapped_name = mapping.get(crew_name_or_key.lower())
        if mapped_name:
            crew = session.query(CrewDefinition).filter_by(name=mapped_name, is_active=True).first()
            if crew: return crew.id
            
        return None

    def list_crews(self) -> List[Dict[str, Any]]:
        """列出可用的 Crew 配置"""
        crews = []
        if not self.db:
            return []
            
        with self.db.get_session() as session:
            definitions = session.query(CrewDefinition).filter_by(is_active=True).all()
            for crew_def in definitions:
                # 简单的 phases 提取
                phases = ["Execution"] 
                crews.append({
                    "name": crew_def.name,
                    "display_name": crew_def.name,
                    "description": crew_def.description or "",
                    "phases": phases,
                })
        return crews
    
    def run(
        self,
        ticker: str,
        date: Optional[str] = None,
        crew_name: str = "standard",
        selected_analysts: Optional[List[str]] = None,
        debate_rounds: Optional[int] = None,
        archive_results: bool = True,
        user_id: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        运行分析 Crew
        
        Args:
            ticker: 股票代码
            date: 分析日期
            crew_name: Crew 配置名称 (standard, buffett, bridgewater, soros)
            selected_analysts: 选择的分析师 (Note: CrewAssembler handles this via variables/structure if supported)
            debate_rounds: 辩论轮数
            archive_results: 是否归档结果
            user_id: 用户 ID (用于加载用户特定工具和知识源)
            run_id: 运行 ID (可选，如果提供则使用，否则自动生成)
        
        Returns:
            分析结果字典
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if not run_id:
            run_id = str(uuid.uuid4())
        
        logger.info(f"Starting {crew_name} crew for {ticker} on {date} (User: {user_id})")
        logger.info(f"Run ID: {run_id}")

        # Best-effort: ensure observability hooks are registered for standalone runs.
        # In FastAPI, this is done in backend/app/core/lifespan.py.
        try:
            from AICrews.observability.crewai_event_listener import (
                register_crewai_event_listeners,
                register_litellm_callback,
            )

            event_level = get_settings().tracking.event_tracking_level
            register_crewai_event_listeners(level=event_level)
            register_litellm_callback(level=event_level)
        except Exception:
            # Never block runs due to observability
            pass
        
        if not self.db:
             return {"status": "failed", "error": "Database not connected"}

        with self.db.get_session() as session:
            crew_id = self._resolve_crew_id(crew_name, session)
            if not crew_id:
                 return {"status": "failed", "error": f"Crew not found: {crew_name}"}
            
            crew_def = session.get(CrewDefinition, crew_id)
            crew_real_name = crew_def.name

        # 初始化 MCP
        if self.enable_mcp and not self._mcp_initialized:
            try:
                asyncio.get_event_loop().run_until_complete(self._init_mcp())
            except Exception as e:
                logger.warning(f"MCP initialization skipped: {e}")
        
        # 准备变量
        variables = {
            "ticker": ticker,
            "date": date,
            "debate_rounds": debate_rounds or 1
        }

        # 组装 Crew
        try:
            crew, preflight = self.assembler.assemble(
                crew_id=crew_id,
                variables=variables,
                job_id=run_id,
                user_id=user_id
            )
            
            if not preflight.success:
                 return {"status": "failed", "error": f"Preflight failed: {preflight.errors}"}

        except Exception as e:
             logger.exception("Assembly failed")
             return {"status": "failed", "error": f"Assembly failed: {e}"}
        
        result = {
            "run_id": run_id,
            "ticker": ticker,
            "date": date,
            "crew_name": crew_real_name,
            "status": "pending",
            "result": None,
            "tasks_completed": [],
            "error": None,
        }
        
        try:
            # 执行 Crew
            from AICrews.observability.logging import LogContext

            with LogContext(
                job_id=run_id,
                run_id=run_id,
                user_id=user_id,
                ticker=ticker,
            ):
                crew_result = crew.kickoff()
            
            result["status"] = "completed"
            result["result"] = str(crew_result)
            
            # 归档结果 (异步执行)
            if archive_results:
                threading.Thread(
                    target=self._archive_results,
                    args=(run_id, ticker, crew),
                    daemon=True
                ).start()
                result["tasks_completed"] = [t.description[:50] for t in crew.tasks if t.output]
            
            logger.info(f"Crew completed successfully: {run_id}")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Crew execution failed: {e}")
            
            if archive_results:
                try:
                    threading.Thread(
                        target=self._archive_results,
                        args=(run_id, ticker, crew),
                        daemon=True
                    ).start()
                except Exception as archive_error:
                    logger.warning(f"Failed to start async archive: {archive_error}")
        
        return result
    
    def _archive_results(self, run_id: str, ticker: str, crew) -> None:
        """归档 Crew 结果到数据库 (同时写入旧表和新 Library 表)"""
        if not self.db:
            return
        
        completed_tasks = [t for t in crew.tasks if t.output]
        logger.info(f"Archiving {len(completed_tasks)} completed tasks")
        
        # 收集所有任务内容和 Agent 追踪信息
        all_content = []
        traces = []
        
        for i, task in enumerate(completed_tasks):
            if not task.output:
                continue
            
            agent_role = task.agent.role
            agent_name = task.agent.role # Agent name might be role in assembled crew
            content = str(task.output)
            
            all_content.append(f"## {agent_role}\n{content}")
            
            # 构建追踪日志
            traces.append({
                "agent_name": agent_name,
                "agent_role": agent_role,
                "action_type": "task_output",
                "content": content[:1000],  # 限制长度
                "step_order": i,
            })
        
        # 生成综合报告
        full_report = "\n\n".join(all_content)
        
        # 确定报告类型
        report_type = "analysis"
        for task in completed_tasks:
            if task.agent.role:
                for role_keyword, rtype in AGENT_ROLE_TO_REPORT_TYPE.items():
                    if role_keyword in task.agent.role:
                        report_type = rtype
                        break
        
        # 生成向量嵌入
        embedding = None
        try:
            embedding = VectorUtil.get_embedding(full_report[:8000])
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
        
        # 保存到旧的 analysis_reports 表
        for task in completed_tasks:
            if not task.output:
                continue
            try:
                self.db.save_analysis_report(
                    run_id=run_id,
                    ticker=ticker,
                    role=task.agent.role,
                    content=str(task.output),
                    report_type=report_type,
                    embedding=embedding,
                )
            except Exception as e:
                logger.warning(f"Failed to save report for {task.agent.role}: {e}")
        
        # 保存到新的 Library 表
        self._archive_to_library(run_id, ticker, crew_name=crew.key if hasattr(crew, 'key') else "Unknown", report_type=report_type, traces=traces)
    
    def _archive_to_library(
        self,
        run_id: str,
        ticker: str,
        crew_name: str,
        report_type: str = "analysis",
        traces: Optional[List[Dict[str, Any]]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """归档到新的 Library 表 (user_asset_insights, insight_traces, insight_attachments)"""
        try:
            # 尝试导入新模型
            from AICrews.database.models import (
                UserAssetInsight,
                InsightTrace,
                InsightAttachment,
                User,
            )
            from AICrews.database.session import SessionLocal
        except ImportError as e:
            logger.warning(f"Library models not available: {e}")
            return
        
        # 查找一个有效的用户 ID (默认为 1，或使用第一个用户)
        user_id = 1
        try:
            with SessionLocal() as db:
                first_user = db.query(User).first()
                if first_user:
                    user_id = first_user.id
        except Exception as e:
            logger.warning(f"Failed to get user ID: {e}")
        
        # 构建报告内容
        completed_tasks_content = []
        for trace in (traces or []):
            if trace.get("action_type") == "task_output":
                completed_tasks_content.append(f"## {trace.get('agent_role', 'Agent')}\n{trace.get('content', '')}")
        
        content = "\n\n".join(completed_tasks_content) if completed_tasks_content else f"Crew Analysis for {ticker}"
        
        # 分析整体 sentiment
        sentiment = "neutral"
        bullish_count = content.lower().count("bullish")
        bearish_count = content.lower().count("bearish")
        if bullish_count > bearish_count:
            sentiment = "bullish"
        elif bearish_count > bullish_count:
            sentiment = "bearish"
        
        # 生成 summary
        summary = content[:500] + "..." if len(content) > 500 else content
        
        try:
            with SessionLocal() as db:
                # 创建 insight 记录
                insight = UserAssetInsight(
                    user_id=user_id,
                    ticker=ticker,
                    source_type="crew_analysis",
                    source_id=run_id,
                    crew_name=crew_name,
                    title=f"{crew_name.title()} Analysis: {ticker}",
                    summary=summary,
                    content=content,
                    sentiment=sentiment,
                    tags=["crew_analysis", crew_name, report_type],
                    analysis_date=datetime.now(),
                )
                db.add(insight)
                db.flush()  # 获取 insight.id
                
                # 创建 trace 记录
                for trace_data in (traces or []):
                    trace = InsightTrace(
                        insight_id=insight.id,
                        agent_name=trace_data.get("agent_name"),
                        agent_role=trace_data.get("agent_role"),
                        action_type=trace_data.get("action_type", "task_output"),
                        content=trace_data.get("content"),
                        step_order=trace_data.get("step_order"),
                        duration_ms=trace_data.get("duration_ms"),
                    )
                    db.add(trace)
                
                db.commit()
                logger.info(f"Archived Crew analysis to Library: run_id={run_id}, ticker={ticker}")
                
        except Exception as e:
            logger.warning(f"Failed to archive to Library: {e}")
    
    async def cleanup(self) -> None:
        """清理资源（MCP 清理由 CrewAI 内部处理）"""
        self._mcp_initialized = False


def run_analysis(
    ticker: str,
    date: Optional[str] = None,
    crew_name: str = "standard",
    selected_analysts: Optional[List[str]] = None,
    debate_rounds: Optional[int] = None,
    deep_model: Optional[str] = None,
    light_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    便捷函数：运行股票分析
    """
    runner = CrewRunner(
        deep_model_name=deep_model,
        light_model_name=light_model,
    )
    
    return runner.run(
        ticker=ticker,
        date=date,
        crew_name=crew_name,
        selected_analysts=selected_analysts,
        debate_rounds=debate_rounds,
    )


def list_available_crews() -> List[Dict[str, Any]]:
    """列出所有可用的 Crew 配置"""
    runner = CrewRunner()
    return runner.list_crews()
