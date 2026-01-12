"""
Knowledge Citations System - 知识引用可观测性

实现强制引用 (Enforced Citations)，让用户知道 Agent 的决策是否参考了知识源。

功能：
1. Prompt 注入：在 Agent 的 system_prompt 中强制要求引用格式
2. 引用解析：从 Agent 输出中提取 [Source: xxx] 标记
3. 引用验证：验证引用的知识源是否存在

Usage:
    from AICrews.utils.citations import CitationInjector, CitationParser
    
    # 注入引用要求到 backstory
    injector = CitationInjector()
    enhanced_backstory = injector.inject(backstory, knowledge_sources)
    
    # 解析输出中的引用
    parser = CitationParser()
    citations = parser.extract("... [Source: buffett_principles.md] ...")
"""

import re
from AICrews.observability.logging import get_logger
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from AICrews.config.prompt_config import get_prompt_config_loader

logger = get_logger(__name__)

# 获取配置加载器
prompt_loader = get_prompt_config_loader()
internal_config = prompt_loader.get_config("internal")
citation_config = internal_config.get("citations", {})

# 引用格式正则表达式
CITATION_PATTERN = re.compile(r'\[Source:\s*([^\]]+)\]', re.IGNORECASE)


@dataclass
class Citation:
    """引用信息"""
    source_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_valid: bool = True


# 强制引用的 Prompt 模板
CITATION_PROMPT_TEMPLATE = citation_config.get("template", """
## Knowledge Citation Requirements

You have access to the following knowledge sources:
{knowledge_list}

**IMPORTANT**: When you use information from these knowledge sources in your analysis:
1. You MUST cite the source using the format: [Source: <filename>]
2. Place the citation immediately after the information you reference
3. If you synthesize information from multiple sources, cite all of them
4. If you are NOT using any knowledge source, state: "Based on general market knowledge"

Example:
- "According to historical patterns, high inflation typically leads to defensive stock outperformance [Source: crisis_2008.md]"
- "Value investing principles suggest looking for companies with strong moats [Source: buffett_principles.md]"
""")


class CitationInjector:
    """
    引用要求注入器
    
    在 Agent 的 backstory 或 system_prompt 中注入引用要求，
    强制 Agent 在使用知识时标注来源。
    """
    
    def __init__(self, template: Optional[str] = None):
        self.template = template or CITATION_PROMPT_TEMPLATE
    
    def inject(
        self,
        backstory: str,
        knowledge_sources: List[Any],
    ) -> str:
        """
        注入引用要求到 backstory
        
        Args:
            backstory: 原始 backstory
            knowledge_sources: 知识源列表
            
        Returns:
            增强后的 backstory，包含引用要求
        """
        if not knowledge_sources:
            return backstory
        
        # 构建知识源列表
        knowledge_list = self._format_knowledge_list(knowledge_sources)
        
        # 生成引用提示
        citation_prompt = self.template.format(knowledge_list=knowledge_list)
        
        # 注入到 backstory
        enhanced_backstory = f"{backstory}\n\n{citation_prompt}"
        
        logger.debug(f"Injected citation requirements for {len(knowledge_sources)} knowledge sources")
        return enhanced_backstory
    
    def _format_knowledge_list(self, knowledge_sources: List[Any]) -> str:
        """格式化知识源列表"""
        lines = []
        for i, source in enumerate(knowledge_sources, 1):
            # 获取知识源名称
            source_name = self._get_source_name(source)
            description = self._get_source_description(source)
            
            if description:
                lines.append(f"{i}. **{source_name}**: {description}")
            else:
                lines.append(f"{i}. **{source_name}**")
        
        return "\n".join(lines)
    
    def _get_source_name(self, source: Any) -> str:
        """获取知识源名称"""
        # LegacyLessonKnowledgeSource
        if hasattr(source, 'SOURCE_NAME'):
            return source.SOURCE_NAME
        
        # 文件知识源
        if hasattr(source, 'file_paths') and source.file_paths:
            from pathlib import Path
            return Path(source.file_paths[0]).name
        
        # 数据库知识源
        if hasattr(source, 'display_name'):
            return source.display_name
        
        # 字符串知识源
        if hasattr(source, 'content'):
            return "inline_knowledge.txt"
        
        return "unknown_source"
    
    def _get_source_description(self, source: Any) -> Optional[str]:
        """获取知识源描述"""
        if hasattr(source, 'description'):
            return source.description
        
        # LegacyLessonKnowledgeSource
        if hasattr(source, 'SOURCE_NAME') and source.SOURCE_NAME == "trading_lessons.db":
            return "Historical trading lessons and market experiences from database"
        
        return None


class CitationParser:
    """
    引用解析器
    
    从 Agent 输出中提取引用信息，用于前端展示和验证。
    """
    
    def __init__(self, valid_sources: Optional[Set[str]] = None):
        self.valid_sources = valid_sources or set()
    
    def extract(self, text: str) -> List[Citation]:
        """
        从文本中提取所有引用
        
        Args:
            text: Agent 输出文本
            
        Returns:
            Citation 列表
        """
        citations = []
        seen = set()
        
        for match in CITATION_PATTERN.finditer(text):
            source_name = match.group(1).strip()
            
            # 去重
            if source_name in seen:
                continue
            seen.add(source_name)
            
            # 验证引用
            is_valid = self._validate_source(source_name)
            
            citations.append(Citation(
                source_name=source_name,
                is_valid=is_valid,
            ))
        
        return citations
    
    def _validate_source(self, source_name: str) -> bool:
        """验证引用的知识源是否存在"""
        if not self.valid_sources:
            return True  # 没有验证集时默认有效
        
        return source_name in self.valid_sources
    
    def highlight_citations(self, text: str) -> str:
        """
        为引用添加 HTML 高亮标记（用于前端渲染）
        
        Args:
            text: 原始文本
            
        Returns:
            带有 HTML 标记的文本
        """
        def replace_citation(match):
            source_name = match.group(1).strip()
            is_valid = self._validate_source(source_name)
            
            css_class = "citation-valid" if is_valid else "citation-invalid"
            return f'<span class="citation {css_class}" data-source="{source_name}">[Source: {source_name}]</span>'
        
        return CITATION_PATTERN.sub(replace_citation, text)
    
    def to_json(self, text: str) -> Dict[str, Any]:
        """
        解析文本并返回 JSON 格式的引用信息
        
        用于前端 API 响应
        """
        citations = self.extract(text)
        
        return {
            "text": text,
            "citations": [
                {
                    "source_name": c.source_name,
                    "display_name": c.display_name,
                    "description": c.description,
                    "category": c.category,
                    "is_valid": c.is_valid,
                }
                for c in citations
            ],
            "citation_count": len(citations),
            "has_citations": len(citations) > 0,
        }


class CitationEnricher:
    """
    引用信息丰富器
    
    从数据库获取引用的知识源详细信息，用于前端 Tooltip 展示。
    """
    
    def __init__(self, db_session):
        self.db_session = db_session
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def enrich(self, citations: List[Citation]) -> List[Citation]:
        """
        丰富引用信息
        
        从数据库获取知识源的详细信息（display_name, description, category）
        """
        from AICrews.database.models import KnowledgeSource
        
        for citation in citations:
            if citation.source_name in self._cache:
                cached = self._cache[citation.source_name]
                citation.display_name = cached.get("display_name")
                citation.description = cached.get("description")
                citation.category = cached.get("category")
                continue
            
            # 查询数据库
            source = self._find_source(citation.source_name)
            if source:
                citation.display_name = source.display_name
                citation.description = source.description
                citation.category = source.category
                citation.is_valid = True
                
                self._cache[citation.source_name] = {
                    "display_name": source.display_name,
                    "description": source.description,
                    "category": source.category,
                }
            else:
                # 特殊处理 trading_lessons.db
                if citation.source_name == "trading_lessons.db":
                    citation.display_name = "历史交易教训"
                    citation.description = "从数据库中检索的历史市场经验"
                    citation.category = "market_history"
                    citation.is_valid = True
        
        return citations
    
    def _find_source(self, source_name: str) -> Optional[Any]:
        """查找知识源"""
        from AICrews.database.models import KnowledgeSource
        
        # 尝试按文件名匹配
        source = self.db_session.query(KnowledgeSource).filter(
            KnowledgeSource.file_path.ilike(f"%{source_name}%")
        ).first()
        
        if source:
            return source
        
        # 尝试按 source_key 匹配
        key = source_name.replace(".md", "").replace(".txt", "").replace(".pdf", "")
        source = self.db_session.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == key
        ).first()
        
        return source


def get_citation_injector() -> CitationInjector:
    """获取引用注入器实例"""
    return CitationInjector()


def get_citation_parser(valid_sources: Optional[Set[str]] = None) -> CitationParser:
    """获取引用解析器实例"""
    return CitationParser(valid_sources)
