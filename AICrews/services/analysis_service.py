"""
分析服务

提供股票分析的高层业务接口
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from AICrews.runner import CrewRunner
from AICrews.config import get_settings
from AICrews.database.db_manager import DBManager
from AICrews.database.vector_utils import VectorUtil
from AICrews.schemas.analysis import StructuredResult, CitationInfo, CrewInfo
from AICrews.utils.citations import CitationParser, CitationEnricher
from AICrews.infrastructure.jobs import JobManager, get_job_manager, JobStatus


class AnalysisService:
    """
    分析服务
    
    封装 TradingCrew，提供更友好的业务接口
    """
    
    def __init__(self):
        """初始化分析服务"""
        self.settings = get_settings()
        self.db = DBManager()
        self.job_manager = get_job_manager()

    def submit_analysis_job(
        self,
        ticker: str,
        crew_name: str,
        analysts: Optional[List[str]] = None,
        debate_rounds: int = 1,
        date: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> str:
        """
        提交分析任务
        """
        # 准备参数
        analysis_date = date or datetime.now().strftime("%Y-%m-%d")
        
        # 定义执行函数
        def run_crew(job_id: str = None):
            result_dict = self.run_analysis(
                ticker=ticker,
                date=analysis_date,
                crew_name=crew_name,
                analysts=analysts,
                debate_rounds=debate_rounds,
                user_id=user_id,
                run_id=job_id,
            )
            return str(result_dict.get("result", ""))
        
        # 提交到任务管理器
        job_id = self.job_manager.submit(
            run_crew,
            ticker=ticker,
            crew_name=crew_name,
            user_id=user_id,
        )
        return job_id

    def get_job_status(self, job_id: str, user_id: Optional[int] = None) -> Optional[Any]:
        """获取任务状态"""
        return self.job_manager.get_status(job_id, user_id=user_id)

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 50, user_id: Optional[int] = None) -> List[Any]:
        """列出任务"""
        return self.job_manager.list_jobs(status=status, limit=limit, user_id=user_id)

    def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        return self.job_manager.cancel(job_id)

    def add_chat_message(self, job_id: str, role: str, content: str):
        """添加聊天记录"""
        self.job_manager.add_chat_message(job_id, role, content)

    def list_available_crews(self) -> List[str]:
        """列出可用 Crew 名称"""
        runner = CrewRunner()
        crews = runner.list_crews()
        return [c["name"] for c in crews]

    def get_crew_info(self, crew_name: str) -> CrewInfo:
        """获取 Crew 详细信息"""
        import yaml
        project_root = Path(__file__).parent.parent.parent
        crew_file = project_root / "config" / "crews" / f"{crew_name}.yaml"
        
        if not crew_file.exists():
            raise ValueError(f"Crew not found: {crew_name}")
            
        with open(crew_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            
        phases = data.get("phases", [])
        phase_names = [p.get("name", "") for p in phases] if isinstance(phases, list) else []
        debate_config = data.get("debate", {})
        
        return CrewInfo(
            name=data.get("name", crew_name),
            description=data.get("description", ""),
            phases=phase_names,
            debate_rounds=debate_config.get("rounds", 1) if isinstance(debate_config, dict) else 1,
            optional_analysts=data.get("optional_analysts", []),
            style_config=data.get("style_config"),
        )

    def process_job_result(self, result_text: str) -> StructuredResult:
        """处理任务结果：解析引用并丰富信息"""
        if not result_text:
            return StructuredResult(text="", citations=[], citation_count=0, has_citations=False)
            
        try:
            parser = CitationParser()
            citations = parser.extract(result_text)
            
            with self.db.get_session() as session:
                enricher = CitationEnricher(session)
                enriched_citations = enricher.enrich(citations)
                
                return StructuredResult(
                    text=result_text,
                    citations=[
                        CitationInfo(
                            source_name=c.source_name,
                            display_name=c.display_name,
                            description=c.description,
                            category=c.category,
                            is_valid=c.is_valid,
                        )
                        for c in enriched_citations
                    ],
                    citation_count=len(enriched_citations),
                    has_citations=len(enriched_citations) > 0,
                )
        except Exception as e:
            return StructuredResult(
                text=result_text,
                citations=[],
                citation_count=0,
                has_citations=False,
            )

    def generate_chat_reply(self, message: str, context: str) -> str:
        """生成聊天回复"""
        return f"关于您的问题「{message}」，基于分析报告，这是一个很好的问题。详细的 AI 回复功能正在开发中..."
    
    def run_analysis(
        self,
        ticker: str,
        date: Optional[str] = None,
        crew_name: str = "standard",
        market: str = "US",
        analysts: Optional[List[str]] = None,
        deep_model: Optional[str] = None,
        light_model: Optional[str] = None,
        debate_rounds: int = 1,
        user_id: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        运行股票分析
        
        Args:
            ticker: 股票代码
            date: 分析日期 (默认今天)
            market: 市场代码 (US/CN/HK 等)
            analysts: 选择的分析师列表
            deep_model: 深度思考模型
            light_model: 快速思考模型
            debate_rounds: 辩论轮数
            user_id: 用户 ID
            run_id: 运行 ID
            
        Returns:
            分析结果字典
        """
        # 默认值处理
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if analysts is None:
            analysts = ["Fundamental", "Technical", "Sentiment"]
        
        # 组装完整的 ticker 格式
        full_ticker = f"{market}:{ticker}" if ":" not in ticker else ticker
        
        runner = CrewRunner(
            deep_model_name=deep_model,
            light_model_name=light_model,
            enable_mcp=True,
        )
        run_result = runner.run(
            ticker=full_ticker,
            date=date,
            crew_name="standard",
            selected_analysts=analysts,
            debate_rounds=debate_rounds,
            archive_results=True,
            user_id=user_id,
            run_id=run_id,
        )
        
        # run_result already includes run_id/result/status
        return {
            "success": run_result.get("status") == "completed",
            "ticker": run_result.get("ticker"),
            "date": run_result.get("date"),
            "result": run_result.get("result"),
            "run_id": run_result.get("run_id"),
            "crew_name": run_result.get("crew_name"),
        }
    
    def save_report(
        self,
        ticker: str,
        date: str,
        result: str,
        output_dir: Optional[str] = None
    ) -> Path:
        """
        保存分析报告到文件
        
        Args:
            ticker: 股票代码
            date: 分析日期
            result: 分析结果
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        # 提取纯股票代码（去除市场前缀）
        pure_ticker = ticker.split(":")[-1] if ":" in ticker else ticker
        
        # 确定输出目录
        if output_dir is None:
            output_dir = Path(self.settings.results_dir) / "reports" / pure_ticker
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{date}_{timestamp}.md"
        file_path = output_dir / filename
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Trading Analysis Report: {ticker}\n")
            f.write(f"**Date:** {date}\n")
            f.write(f"**Generated At:** {datetime.now()}\n\n")
            f.write("## Final CrewAI Output\n\n")
            f.write(result)
        
        return file_path
    
    # =========================================================================
    # 历史分析查询 API
    # =========================================================================
    
    def get_historical_reports(
        self,
        ticker: Optional[str] = None,
        report_type: Optional[str] = None,
        agent_role: Optional[str] = None,
        days_back: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        查询历史分析报告
        
        Args:
            ticker: 股票代码筛选
            report_type: 报告类型 ('analysis', 'plan', 'critique')
            agent_role: Agent 角色筛选
            days_back: 查询多少天内的报告
            limit: 返回数量限制
            
        Returns:
            报告列表
        """
        from sqlalchemy import select, and_
        from AICrews.database.models import AnalysisReport
        
        with self.db.get_session() as session:
            query = select(AnalysisReport)
            
            # 添加筛选条件
            filters = []
            
            if ticker:
                filters.append(AnalysisReport.ticker == ticker)
            
            if report_type:
                filters.append(AnalysisReport.report_type == report_type)
            
            if agent_role:
                filters.append(AnalysisReport.agent_role.like(f"%{agent_role}%"))
            
            if days_back:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                filters.append(AnalysisReport.date >= cutoff_date)
            
            if filters:
                query = query.where(and_(*filters))
            
            # 按日期降序
            query = query.order_by(AnalysisReport.date.desc()).limit(limit)
            
            results = session.scalars(query).all()
            
            return [
                {
                    "id": r.id,
                    "run_id": r.run_id,
                    "ticker": r.ticker,
                    "date": r.date.isoformat(),
                    "agent_role": r.agent_role,
                    "report_type": r.report_type,
                    "content_preview": r.content[:500] + "..." if len(r.content) > 500 else r.content,
                    "content_length": len(r.content),
                }
                for r in results
            ]
    
    def get_report_detail(self, report_id: int) -> Optional[Dict[str, Any]]:
        """
        获取报告完整内容
        
        Args:
            report_id: 报告 ID
            
        Returns:
            完整报告数据
        """
        from sqlalchemy import select
        from AICrews.database.models import AnalysisReport
        
        with self.db.get_session() as session:
            stmt = select(AnalysisReport).where(AnalysisReport.id == report_id)
            result = session.scalars(stmt).first()
            
            if not result:
                return None
            
            return {
                "id": result.id,
                "run_id": result.run_id,
                "ticker": result.ticker,
                "date": result.date.isoformat(),
                "agent_role": result.agent_role,
                "report_type": result.report_type,
                "content": result.content,
                "i18n_summary": result.i18n_summary,
            }
    
    def search_similar_reports(
        self,
        query_text: str,
        ticker: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        语义搜索相似报告
        
        Args:
            query_text: 搜索查询文本
            ticker: 股票代码筛选
            limit: 返回数量
            
        Returns:
            相似报告列表
        """
        from sqlalchemy import select
        from AICrews.database.models import AnalysisReport
        
        # 生成查询向量
        query_embedding = VectorUtil.get_embedding(query_text)
        
        with self.db.get_session() as session:
            stmt = select(AnalysisReport).order_by(
                AnalysisReport.embedding.l2_distance(query_embedding)
            )
            
            if ticker:
                stmt = stmt.where(AnalysisReport.ticker == ticker)
            
            stmt = stmt.limit(limit)
            
            results = session.scalars(stmt).all()
            
            return [
                {
                    "id": r.id,
                    "run_id": r.run_id,
                    "ticker": r.ticker,
                    "date": r.date.isoformat(),
                    "agent_role": r.agent_role,
                    "report_type": r.report_type,
                    "content_preview": r.content[:300] + "..." if len(r.content) > 300 else r.content,
                }
                for r in results
            ]
    
    def get_ticker_analysis_history(
        self,
        ticker: str,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        获取股票的完整分析历史
        
        Args:
            ticker: 股票代码
            days_back: 查询多少天内的历史
            
        Returns:
            按类型分组的分析历史
        """
        from sqlalchemy import select, and_, func
        from AICrews.database.models import AnalysisReport
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with self.db.get_session() as session:
            # 获取所有报告
            stmt = select(AnalysisReport).where(
                and_(
                    AnalysisReport.ticker == ticker,
                    AnalysisReport.date >= cutoff_date
                )
            ).order_by(AnalysisReport.date.desc())
            
            all_reports = session.scalars(stmt).all()
            
            # 按类型分组
            grouped = {
                "analysis": [],
                "plan": [],
                "critique": [],
            }
            
            for r in all_reports:
                report_data = {
                    "id": r.id,
                    "run_id": r.run_id,
                    "date": r.date.isoformat(),
                    "agent_role": r.agent_role,
                    "content_preview": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                }
                
                if r.report_type in grouped:
                    grouped[r.report_type].append(report_data)
            
            # 统计信息
            total_reports = len(all_reports)
            report_counts = {
                k: len(v) for k, v in grouped.items()
            }
            
            return {
                "ticker": ticker,
                "period_days": days_back,
                "total_reports": total_reports,
                "report_counts": report_counts,
                "reports": grouped,
            }
