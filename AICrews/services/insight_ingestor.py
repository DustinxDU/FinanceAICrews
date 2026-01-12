"""
Insight Ingestor Service - Library 数据埋点服务

负责接收并存储来自以下来源的分析数据：
- Cockpit: Quick Scan, Technical Diagnostic
- Workbench: Agent Deploy 产物

数据会存储到 user_asset_insights, insight_attachments, insight_traces 表
"""

from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from AICrews.database.models import (
    UserAssetInsight,
    InsightAttachment,
    InsightTrace,
    User,
)

logger = get_logger(__name__)


class InsightIngestor:
    """分析数据摄入服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # Quick Scan 埋点
    # ============================================
    
    async def save_quick_scan(
        self,
        user_id: int,
        ticker: str,
        title: str,
        summary: str,
        sentiment: str,
        sentiment_score: float,
        key_metrics: Optional[Dict[str, Any]] = None,
        signal: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        content: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        analysis_date: Optional[datetime] = None,
    ) -> UserAssetInsight:
        """
        保存 Quick Scan 分析结果
        
        Args:
            user_id: 用户 ID
            ticker: 股票代码
            title: 分析标题
            summary: 摘要
            sentiment: 情感 (bullish/bearish/neutral)
            sentiment_score: 情感分数 (-1 to 1)
            key_metrics: 关键指标
            signal: 信号 (buy/sell/hold/watch/neutral)
            target_price: 目标价
            stop_loss: 止损价
            content: 完整内容
            raw_data: 原始数据
            tags: 标签
            analysis_date: 分析时间
            
        Returns:
            UserAssetInsight: 创建的分析记录
        """
        import uuid
        
        # 使用 UUID 确保唯一性，避免并发请求冲突
        source_id = f"quick_scan_{ticker}_{uuid.uuid4().hex[:12]}"
        
        insight = UserAssetInsight(
            user_id=user_id,
            ticker=ticker,
            source_type="quick_scan",
            source_id=source_id,
            title=title,
            summary=summary,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            key_metrics=key_metrics,
            signal=signal,
            target_price=target_price,
            stop_loss=stop_loss,
            content=content,
            raw_data=raw_data,
            tags=tags or ["quick_scan"],
            analysis_date=analysis_date or datetime.now(),
        )
        
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        
        logger.info(f"Saved Quick Scan for {ticker}: {insight.id}")
        return insight
    
    # ============================================
    # Technical Diagnostic 埋点
    # ============================================
    
    async def save_technical_diagnostic(
        self,
        user_id: int,
        ticker: str,
        title: str,
        summary: str,
        sentiment: str,
        sentiment_score: float,
        key_metrics: Optional[Dict[str, Any]] = None,
        signal: Optional[str] = None,
        content: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        analysis_date: Optional[datetime] = None,
    ) -> UserAssetInsight:
        """
        保存 Technical Diagnostic 分析结果
        """
        import uuid
        
        # 使用 UUID 确保唯一性，避免并发请求冲突
        source_id = f"tech_diagnostic_{ticker}_{uuid.uuid4().hex[:12]}"
        
        insight = UserAssetInsight(
            user_id=user_id,
            ticker=ticker,
            source_type="technical_diagnostic",
            source_id=source_id,
            title=title,
            summary=summary,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            key_metrics=key_metrics,
            signal=signal,
            content=content,
            raw_data=raw_data,
            tags=tags or ["technical_diagnostic"],
            analysis_date=analysis_date or datetime.now(),
        )
        
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        
        logger.info(f"Saved Technical Diagnostic for {ticker}: {insight.id}")
        return insight
    
    # ============================================
    # Crew Analysis 埋点 (Workbench)
    # ============================================
    
    async def save_crew_analysis(
        self,
        user_id: int,
        ticker: str,
        crew_name: str,
        run_id: str,
        title: str,
        summary: str,
        content: str,
        sentiment: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        signal: Optional[str] = None,
        key_metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        analysis_date: Optional[datetime] = None,
    ) -> UserAssetInsight:
        """
        保存 Crew Analysis 分析结果
        
        Args:
            user_id: 用户 ID
            ticker: 股票代码
            crew_name: Crew 名称
            run_id: 运行 ID
            title: 分析标题
            summary: 摘要
            content: 完整内容 (Markdown)
            sentiment: 情感
            sentiment_score: 情感分数
            signal: 信号
            key_metrics: 关键指标
            tags: 标签
            analysis_date: 分析时间
        """
        insight = UserAssetInsight(
            user_id=user_id,
            ticker=ticker,
            source_type="crew_analysis",
            source_id=run_id,
            crew_name=crew_name,
            title=title,
            summary=summary,
            content=content,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            signal=signal,
            key_metrics=key_metrics,
            tags=tags or ["crew_analysis", crew_name],
            analysis_date=analysis_date or datetime.now(),
        )
        
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        
        logger.info(f"Saved Crew Analysis for {ticker} ({crew_name}): {insight.id}")
        return insight
    
    async def add_attachment(
        self,
        insight_id: int,
        file_name: str,
        file_type: str,
        storage_path: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        description: Optional[str] = None,
        sheet_name: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> InsightAttachment:
        """
        添加分析附件
        
        Args:
            insight_id: 分析记录 ID
            file_name: 文件名
            file_type: 文件类型 (xlsx, pdf, md, json, png, jpg)
            storage_path: 存储路径
            file_size: 文件大小
            mime_type: MIME 类型
            description: 描述
            sheet_name: Excel 工作表名
            page_number: PDF 页码
        """
        attachment = InsightAttachment(
            insight_id=insight_id,
            file_name=file_name,
            file_type=file_type,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            description=description,
            sheet_name=sheet_name,
            page_number=page_number,
        )
        
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        
        logger.info(f"Added attachment {file_name} to insight {insight_id}")
        return attachment
    
    async def add_trace(
        self,
        insight_id: int,
        agent_name: str,
        action_type: str,
        content: Optional[str] = None,
        step_order: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> InsightTrace:
        """
        添加追溯日志
        
        Args:
            insight_id: 分析记录 ID
            agent_name: Agent 名称
            action_type: 动作类型 (think, tool_call, tool_result, output)
            content: 内容
            step_order: 步骤序号
            input_data: 输入数据
            output_data: 输出数据
            tokens_used: 使用的 token 数
            duration_ms: 耗时 (毫秒)
            model_name: 模型名称
        """
        trace = InsightTrace(
            insight_id=insight_id,
            agent_name=agent_name,
            action_type=action_type,
            content=content,
            step_order=step_order,
            input_data=input_data,
            output_data=output_data,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            model_name=model_name,
        )
        
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        
        logger.info(f"Added trace for insight {insight_id}: {agent_name}/{action_type}")
        return trace
    
    async def save_crew_result_with_artifacts(
        self,
        user_id: int,
        ticker: str,
        crew_name: str,
        run_id: str,
        title: str,
        summary: str,
        content: str,
        artifacts: List[Dict[str, Any]],
        traces: List[Dict[str, Any]],
        sentiment: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        signal: Optional[str] = None,
        key_metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        analysis_date: Optional[datetime] = None,
    ) -> UserAssetInsight:
        """
        完整保存 Crew 执行结果（包含附件、日志和执行摘要）
        
        Args:
            user_id: 用户 ID
            ticker: 股票代码
            crew_name: Crew 名称
            run_id: 运行 ID
            title: 标题
            summary: 摘要
            content: 内容
            artifacts: 附件列表 [{file_name, file_type, storage_path, ...}]
            traces: 日志列表 [{agent_name, action_type, ...}]
            sentiment: 情感
            sentiment_score: 情感分数
            signal: 信号
            key_metrics: 关键指标 (包含 Token、耗时、版本等)
            tags: 标签
            analysis_date: 分析时间
        """
        # 补充执行摘要到 key_metrics
        final_metrics = key_metrics or {}
        
        # 保存分析记录
        insight = await self.save_crew_analysis(
            user_id=user_id,
            ticker=ticker,
            crew_name=crew_name,
            run_id=run_id,
            title=title,
            summary=summary,
            content=content,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            signal=signal,
            key_metrics=final_metrics,
            tags=tags,
            analysis_date=analysis_date or datetime.now(),
        )
        
        # 保存附件 (Artifacts)
        # Supports two artifact formats for backward compatibility:
        # 1. Storage-based (preferred): {file_name, file_type, storage_path, ...}
        # 2. Inline content (legacy): {path, content, content_type}
        #    - For inline content, we log a warning as content is not persisted
        for artifact in artifacts:
            # Detect artifact format
            if "file_name" in artifact and "storage_path" in artifact:
                # Storage-based format (preferred)
                await self.add_attachment(
                    insight_id=insight.id,
                    file_name=artifact["file_name"],
                    file_type=artifact["file_type"],
                    storage_path=artifact["storage_path"],
                    file_size=artifact.get("file_size"),
                    mime_type=artifact.get("mime_type"),
                    description=artifact.get("description"),
                    sheet_name=artifact.get("sheet_name"),
                    page_number=artifact.get("page_number"),
                )
            elif "path" in artifact:
                # Inline content format (legacy - content not persisted to disk)
                # Extract file_name from path (e.g., "artifacts/job123/tasks_output.json" -> "tasks_output.json")
                path = artifact["path"]
                file_name = path.split("/")[-1] if "/" in path else path
                content_type = artifact.get("content_type", "application/octet-stream")

                # Map content_type to file_type
                file_type = "json" if "json" in content_type else "txt"

                logger.warning(
                    f"Inline artifact '{file_name}' received but content not persisted to disk. "
                    f"Use storage-based format for proper artifact storage."
                )

                await self.add_attachment(
                    insight_id=insight.id,
                    file_name=file_name,
                    file_type=file_type,
                    storage_path=path,  # Virtual path (file may not exist)
                    file_size=len(artifact.get("content", "")) if artifact.get("content") else None,
                    mime_type=content_type,
                    description=f"Inline artifact (content not persisted): {file_name}",
                )
            else:
                logger.warning(f"Skipping artifact with unknown format: {list(artifact.keys())}")
        
        # 保存追溯日志 (Traces / Events)
        for i, trace in enumerate(traces):
            await self.add_trace(
                insight_id=insight.id,
                agent_name=trace.get("agent_name", "System"),
                action_type=trace.get("action_type") or trace.get("event_type", "activity"),
                content=trace.get("content") or str(trace.get("payload", "")),
                step_order=i,
                input_data=trace.get("input_data"),
                output_data=trace.get("output_data"),
                tokens_used=trace.get("tokens_used"),
                duration_ms=trace.get("duration_ms"),
                model_name=trace.get("model_name"),
            )
        
        logger.info(f"Saved complete crew result for {ticker} ({crew_name}) [V3]: insight_id={insight.id}, artifacts={len(artifacts)}, events={len(traces)}")
        return insight


# 便捷函数
def get_insight_ingestor(db: Session) -> InsightIngestor:
    """获取 InsightIngestor 实例"""
    return InsightIngestor(db)
