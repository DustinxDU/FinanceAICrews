"""
Tool Registry - 统一工具注册中心

整合所有工具来源（Builtin, MCP, Custom等），提供统一的工具查询接口。
同时支持知识源加载，与原有的 backend/app/tools/registry.py 功能对齐。
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import time
import concurrent.futures
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from AICrews.observability.logging import get_logger

from .base import BaseTool, ToolSource, ToolTier
from AICrews.database.models.insight import BuiltinTool
from AICrews.database.models.mcp import (
    MCPServer,
    MCPTool,
    UserMCPServer,
    UserMCPTool,
    UserToolConfig,
)
from AICrews.database.models.agent import AgentDefinition
from AICrews.database.models.knowledge import UserKnowledgeSource
from AICrews.database.models.user import UserStrategy

logger = get_logger(__name__)


class ToolRegistry:
    """统一工具注册中心

    整合所有工具来源：
    - Tier 1: Builtin Tools (内置工具)
    - Tier 2: Data Connectors (MCP Servers)
    - Tier 3: Knowledge RAG (知识源)
    - Tier 4: Agent Actions (Agent 特定工具)

    同时支持量化工具和用户自定义策略工具。
    """

    def __init__(self, db: Session):
        """初始化工具注册中心

        Args:
            db: 数据库会话
        """
        self.db = db
        self._tool_cache: Dict[str, BaseTool] = {}
        self._crewai_tools_cache: Dict[Optional[int], List[Callable]] = {}
        self._cache_timestamp: Dict[Optional[int], datetime] = {}
        self._cache_ttl = 300  # 5分钟缓存

    # =========================================================================
    # 工具注册与注销
    # =========================================================================

    def register_tool(self, tool: BaseTool) -> None:
        """注册工具

        Args:
            tool: 工具对象
        """
        self._tool_cache[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具

        Args:
            tool_name: 工具名称

        Returns:
            注销成功返回 True，否则返回 False
        """
        if tool_name in self._tool_cache:
            del self._tool_cache[tool_name]
            logger.debug(f"Unregistered tool: {tool_name}")
            return True
        return False

    def clear_cache(self) -> None:
        """清空工具缓存"""
        self._tool_cache.clear()
        self._crewai_tools_cache.clear()
        self._cache_timestamp.clear()
        logger.debug("Cleared tool cache")

    # =========================================================================
    # CrewAI 工具获取接口 (与原有 API 对齐)
    # =========================================================================

    def get_user_tools(
        self,
        user_id: Optional[int] = None,
        categories: Optional[List[str]] = None,
        include_disabled: bool = False,
    ) -> List[Callable]:
        """获取用户可用的 CrewAI 工具列表

        Args:
            user_id: 用户 ID，如果为 None 则返回系统默认工具
            categories: 过滤的工具类别列表
            include_disabled: 是否包含被禁用的工具

        Returns:
            CrewAI 工具列表
        """
        # 检查缓存 - 按 user_id 分桶
        if (
            user_id in self._crewai_tools_cache
            and user_id in self._cache_timestamp
            and (datetime.now() - self._cache_timestamp[user_id]).seconds
            < self._cache_ttl
        ):
            logger.debug(f"Using cached CrewAI tools for user {user_id}")
            return self._crewai_tools_cache[user_id]

        tools = []

        # Group 1: System basic capabilities
        # 方案一落地: 实现系统内置工具按需启用/禁用机制
        tools.extend(self._get_system_mcp_tools(user_id, include_disabled))
        tools.extend(self._get_quant_tools(user_id, include_disabled))
        # NOTE: _get_external_tools removed - use LoadoutResolver + ToolsFactory instead
        # External tools (web_search, scrape, etc.) are now loaded via provider priority system

        # Group 2: User Custom MCP (needs user_id)
        if user_id:
            user_mcp_tools = self._get_user_mcp_tools(user_id)
            tools.extend(user_mcp_tools)

            # Group 3: 用户自定义策略
            strategy_tools = self._get_user_strategy_tools(user_id)
            tools.extend(strategy_tools)

        # 更新缓存 - 按 user_id 分桶
        self._crewai_tools_cache[user_id] = tools
        self._cache_timestamp[user_id] = datetime.now()

        logger.info(f"Loaded {len(tools)} CrewAI tools for user {user_id}")
        return tools

    def _get_system_mcp_tools(
        self, user_id: Optional[int] = None, include_disabled: bool = False
    ) -> List[Callable]:
        """获取系统内置 MCP 工具"""
        all_tools = []
        try:
            from AICrews.tools.market_data_tools import (
                get_stock_price,
                get_stock_fundamentals,
                get_stock_news,
            )

            # 应用统一包装器
            all_tools = [
                self._standard_tool_wrapper(get_stock_price, "get_stock_price"),
                self._standard_tool_wrapper(
                    get_stock_fundamentals, "get_stock_fundamentals"
                ),
                self._standard_tool_wrapper(get_stock_news, "get_stock_news"),
            ]
        except ImportError as e:
            logger.warning(f"Failed to import system MCP tools: {e}")
            return []

        return self._filter_enabled_tools(all_tools, user_id, include_disabled)

    def _get_quant_tools(
        self, user_id: Optional[int] = None, include_disabled: bool = False
    ) -> List[Callable]:
        """获取原生量化与分析工具"""
        all_tools = []
        try:
            from AICrews.tools.quant_tools import (
                get_technical_summary,
                calculate_indicator,
                check_trend,
            )
            from AICrews.tools.expression_tools import evaluate_strategy
            from AICrews.tools.sentiment_tools import analyze_stock_sentiment

            # 应用统一包装器
            all_tools = [
                self._standard_tool_wrapper(
                    get_technical_summary, "get_technical_summary"
                ),
                self._standard_tool_wrapper(calculate_indicator, "calculate_indicator"),
                self._standard_tool_wrapper(check_trend, "check_trend"),
                self._standard_tool_wrapper(evaluate_strategy, "evaluate_strategy"),
                self._standard_tool_wrapper(
                    analyze_stock_sentiment, "analyze_stock_sentiment"
                ),
            ]
        except ImportError as e:
            logger.warning(f"Failed to import quant tools: {e}")

        return self._filter_enabled_tools(all_tools, user_id, include_disabled)

    def _filter_enabled_tools(
        self, tools: List[Callable], user_id: Optional[int], include_disabled: bool
    ) -> List[Callable]:
        """根据 DB 配置过滤已启用的工具"""
        if include_disabled or not self.db:
            return tools

        from AICrews.database.models import UserToolConfig, MCPTool

        enabled_tools = []
        for tool_func in tools:
            tool_name = getattr(tool_func, "__name__", str(tool_func))

            # 检查该工具在 mcp_tools 表中的定义
            mcp_tool = (
                self.db.query(MCPTool).filter(MCPTool.tool_name == tool_name).first()
            )
            if not mcp_tool:
                # 如果没在 mcp_tools 里定义，默认认为系统内置且启用（除非有明确排除逻辑）
                enabled_tools.append(tool_func)
                continue

            # 如果 mcp_tool 标记为非激活，直接跳过
            if not mcp_tool.is_active:
                continue

            # 检查用户配置
            if user_id:
                user_config = (
                    self.db.query(UserToolConfig)
                    .filter(
                        UserToolConfig.user_id == user_id,
                        UserToolConfig.tool_id == mcp_tool.id,
                    )
                    .first()
                )

                # 如果有用户配置，遵循用户配置；否则遵循 mcp_tool.is_active (默认启用)
                if user_config:
                    if user_config.is_enabled:
                        enabled_tools.append(tool_func)
                else:
                    enabled_tools.append(tool_func)
            else:
                # 无用户 ID 时，只看 mcp_tool 自身状态
                enabled_tools.append(tool_func)

        return enabled_tools

    def _get_user_mcp_tools(self, user_id: int) -> List[Callable]:
        """获取用户自定义 MCP 工具

        遍历 user_mcp_servers 表，动态连接第三方 MCP 并获取其工具列表

        Args:
            user_id: 用户 ID

        Returns:
            用户 MCP 工具函数列表
        """
        if not self.db:
            return []

        try:
            # 获取用户启用的 MCP 服务器
            user_servers = (
                self.db.query(UserMCPServer)
                .filter(
                    UserMCPServer.user_id == user_id, UserMCPServer.is_active == True
                )
                .all()
            )

            tools = []
            for server in user_servers:
                # 获取服务器上已启用的工具
                server_tools = (
                    self.db.query(UserMCPTool)
                    .filter(
                        UserMCPTool.server_id == server.id,
                        UserMCPTool.is_enabled == True,
                    )
                    .all()
                )

                for tool_config in server_tools:
                    # 动态创建工具包装函数
                    wrapped_tool = self._create_mcp_tool_wrapper(
                        server=server,
                        tool_name=tool_config.tool_name,
                        description=tool_config.description
                        or f"Tool from {server.display_name}",
                        input_schema=tool_config.input_schema,
                    )
                    if wrapped_tool:
                        tools.append(wrapped_tool)

            return tools

        except Exception as e:
            logger.error(f"Error loading user MCP tools: {e}")
            return []

    def _get_user_strategy_tools(self, user_id: int) -> List[Callable]:
        """获取用户自定义策略工具

        遍历 user_strategies 表，为每个策略动态生成 CrewAI Tool

        Args:
            user_id: 用户 ID

        Returns:
            用户策略工具列表
        """
        if not self.db:
            return []

        try:
            # 获取用户启用的策略
            strategies = (
                self.db.query(UserStrategy)
                .filter(UserStrategy.user_id == user_id, UserStrategy.is_active == True)
                .all()
            )

            tools = []
            for strategy in strategies:
                wrapped_tool = self._create_strategy_tool(strategy)
                if wrapped_tool:
                    tools.append(wrapped_tool)

            return tools

        except Exception as e:
            logger.error(f"Error loading user strategy tools: {e}")
            return []

    def _standard_tool_wrapper(
        self,
        func: Callable,
        tool_name: str,
        timeout: int = 30,
        max_retries: int = 2,
        *,
        as_crewai_tool: bool = True,
    ) -> Callable:
        """统一工具包装器（偏同步、可测试）。

        目标：
        - 返回一个普通可调用对象（sync），避免事件循环嵌套导致的死锁/卡死
        - 保留尽可能多的元数据（`__name__`/`__doc__`/`__signature__`/`__annotations__`）
        - 对 CrewAI `Tool` 对象优先调用其 `func`（原始函数）或 `run()`
        """

        def _redact_sensitive(data: Any) -> Any:
            if isinstance(data, dict):
                out = {}
                for k, v in data.items():
                    key = str(k)
                    if any(
                        s in key.lower()
                        for s in ["api_key", "token", "password", "secret"]
                    ):
                        out[key] = "********"
                    else:
                        out[key] = _redact_sensitive(v)
                return out
            if isinstance(data, list):
                return [_redact_sensitive(v) for v in data]
            return data

        def _call_underlying(*args, **kwargs) -> Any:
            underlying = getattr(func, "func", None)
            if callable(underlying):
                return underlying(*args, **kwargs)
            if callable(func):
                return func(*args, **kwargs)
            runner = getattr(func, "run", None)
            if callable(runner):
                return runner(*args, **kwargs)
            raise TypeError(f"Tool is not callable: {func}")

        def sync_wrapper(*args, **kwargs) -> str:
            start_time = time.time()
            try:
                result = _call_underlying(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    try:
                        result = asyncio.run(result)
                    except RuntimeError:
                        # Running loop: best-effort fallback without blocking the loop
                        result = "Error: Tool returned coroutine in running event loop"
                duration = int((time.time() - start_time) * 1000)
                return str(_redact_sensitive(result))
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                logger.error(
                    "Tool %s execution failed after %sms: %s",
                    tool_name,
                    duration,
                    e,
                    exc_info=True,
                )
                return f"Error: {str(e)}"

        sync_wrapper.__name__ = getattr(func, "__name__", tool_name)
        sync_wrapper.__doc__ = (
            getattr(func, "__doc__", None) or getattr(func, "description", None) or ""
        )
        try:
            import inspect

            sync_wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(f"Failed to copy function signature for {tool_name}: {e}")
        try:
            sync_wrapper.__annotations__ = dict(
                getattr(func, "__annotations__", {}) or {}
            )
        except Exception as e:
            logger.debug(f"Failed to copy function annotations for {tool_name}: {e}")

        return sync_wrapper

    def _create_mcp_tool_wrapper(
        self,
        server: UserMCPServer,
        tool_name: str,
        description: str,
        input_schema: Optional[Dict],
    ) -> Optional[Callable]:
        """创建 MCP 工具的包装函数

        动态连接远程 MCP 服务并调用工具

        Args:
            server: MCP 服务器配置
            tool_name: 工具名称
            description: 工具描述
            input_schema: 输入 schema

        Returns:
            包装后的工具函数
        """
        try:
            # 创建异步工具函数
            async def mcp_tool_call(**kwargs):
                from mcp import ClientSession
                from mcp.client.sse import sse_client

                async with sse_client(server.url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments=kwargs)
                        return str(result.content) if result.content else "No result"

            # 使用统一包装器
            sync_wrapper = self._standard_tool_wrapper(
                mcp_tool_call, tool_name=f"mcp_{server.server_key}_{tool_name}"
            )

            # 设置增强后的文档字符串
            sync_wrapper.__doc__ = (
                f"{description}\n\nFrom MCP Server: {server.display_name}"
            )

            # 使用 @tool 装饰器
            from crewai.tools import tool

            return tool(sync_wrapper.__name__)(sync_wrapper)

        except Exception as e:
            logger.error(f"Error creating MCP tool wrapper: {e}")
            return None

    def _create_strategy_tool(self, strategy: UserStrategy) -> Optional[Callable]:
        """创建策略工具

        将用户定义的策略公式转换为 CrewAI 可调用的工具

        Args:
            strategy: 用户策略配置

        Returns:
            包装后的工具函数（Callable）
        """
        try:
            strategy_id = strategy.id
            strategy_name = strategy.name
            strategy_formula = strategy.formula
            strategy_description = (
                strategy.description or f"Custom strategy: {strategy_name}"
            )

            def evaluate_custom_strategy(ticker: str) -> str:
                """评估自定义策略"""
                from AICrews.tools.expression_tools import evaluate_strategy

                # evaluate_strategy is a Tool object, need to call its run() method
                return evaluate_strategy.run(ticker=ticker, formula=strategy_formula)

            # 设置工具名称和文档
            tool_name = f"check_strategy_{strategy_id}"
            evaluate_custom_strategy.__name__ = tool_name
            evaluate_custom_strategy.__doc__ = f"""{strategy_description}

Strategy Formula: {strategy_formula}

Args:
    ticker: Stock ticker symbol (e.g., "AAPL")

Returns:
    Strategy evaluation result (True/False signal with indicator values)
"""

            # 使用统一包装器包装函数
            sync_wrapper = self._standard_tool_wrapper(
                evaluate_custom_strategy, tool_name=tool_name
            )

            # 返回可调用的包装后函数（不应用 @tool 装饰器，避免重复装饰）
            return sync_wrapper

        except Exception as e:
            import traceback

            logger.error(f"Error creating strategy tool: {e}\n{traceback.format_exc()}")
            return None

    # =========================================================================
    # 4-Tier Loadout 系统支持
    # =========================================================================

    def get_tools_by_namespaced_ids(
        self, tool_ids: List[str], user_id: Optional[int] = None
    ) -> List[Callable]:
        """根据命名空间 ID 列表获取工具

        支持 4-Tier Loadout 系统的工具 ID 格式:
        - Tier 1: "data:price", "data:fundamentals", "data:news"
        - Tier 2: "quant:technical_summary", "quant:calculate_indicator"
        - Tier 3: "external:web_search", "external:scrape_website"
        - Tier 4: "strategy:123" (策略 ID)

        Args:
            tool_ids: 命名空间工具 ID 列表
            user_id: 用户 ID（用于获取用户自定义工具）

        Returns:
            CrewAI 工具列表
        """
        if not tool_ids:
            return []

        tools = []
        all_available = self.get_user_tools(user_id)

        # 创建工具名称到工具对象的映射
        tool_map = {}
        for t in all_available:
            tool_name = getattr(t, "__name__", str(t))
            # 为系统工具添加命名空间前缀
            tool_key = self._get_tool_key(t)
            tool_map[tool_key] = t
            # 同时也存储不带前缀的名称（向后兼容）
            tool_map[tool_name] = t

        # 根据 ID 获取工具
        for tool_id in tool_ids:
            if ":" in tool_id:
                # 命名空间格式: "tier:key"
                if tool_id.startswith("strategy:"):
                    # 特殊处理：动态加载策略工具
                    strategy_id_str = tool_id.split(":", 1)[1]
                    try:
                        strategy_id = int(strategy_id_str)
                        strategy = (
                            self.db.query(UserStrategy)
                            .filter(
                                UserStrategy.id == strategy_id,
                                UserStrategy.user_id == user_id,
                                UserStrategy.is_active == True,
                            )
                            .first()
                        )

                        if strategy:
                            tool = self._create_strategy_tool(strategy)
                            if tool:
                                tools.append(tool)
                                logger.info(f"Created strategy tool: {tool_id}")
                            else:
                                logger.warning(
                                    f"Failed to create strategy tool: {tool_id}"
                                )
                        else:
                            logger.warning(f"Strategy not found: {tool_id}")
                    except ValueError:
                        logger.warning(f"Invalid strategy ID format: {tool_id}")

                elif tool_id in tool_map:
                    tools.append(tool_map[tool_id])
                else:
                    logger.warning(f"Tool not found: {tool_id}")
            else:
                # 直接工具名称 - 支持 MCP 工具命名空间格式
                found = False

                # 1. Check if it's in the tool_map (existing tools)
                if tool_id in tool_map:
                    tools.append(tool_map[tool_id])
                    found = True

                # 2. Check if it's a namespaced MCP tool (mcp_server_tool)
                elif tool_id.startswith("mcp_"):
                    tool = self._get_tool_by_namespaced_name(tool_id, user_id)
                    if tool:
                        tools.append(tool)
                        found = True
                        logger.info(f"Loaded MCP tool by namespaced name: {tool_id}")

                # 3. Fallback to legacy name lookup (backward compatibility)
                if not found:
                    tool = self._get_tool_by_legacy_name(tool_id, user_id)
                    if tool:
                        tools.append(tool)
                        found = True

                if not found:
                    logger.warning(f"Tool not found: {tool_id}")

        logger.info(
            f"[4-Tier Loadout] Loaded {len(tools)} tools from {len(tool_ids)} IDs"
        )
        return tools

    def _get_tool_key(self, tool: Any) -> str:
        """获取工具的命名空间键

        根据工具的来源和名称生成命名空间 ID

        Args:
            tool: 工具函数或对象

        Returns:
            命名空间键
        """
        tool_name = getattr(tool, "__name__", str(tool))
        tool_doc = getattr(tool, "__doc__", "")

        # Tier 4: User Strategies (check_strategy_X format)
        if tool_name.startswith("check_strategy_"):
            # Extract strategy ID from name
            try:
                strategy_id = tool_name.split("_", 2)[2]  # check_strategy_123
                return f"strategy:{strategy_id}"
            except (IndexError, ValueError):
                return tool_name

        # Tier 1: Data Feeds
        if "price" in tool_name.lower():
            return f"data:{tool_name}"
        elif "fundamental" in tool_name.lower():
            return f"data:{tool_name}"
        elif "news" in tool_name.lower():
            return f"data:{tool_name}"

        # Tier 2: Quant Skills
        elif "technical" in tool_name.lower() or "indicator" in tool_name.lower():
            return f"quant:{tool_name}"
        elif "trend" in tool_name.lower():
            return f"quant:{tool_name}"
        elif "strategy" in tool_name.lower() and "check" in tool_name.lower():
            return f"quant:{tool_name}"

        # Tier 3: External Access
        elif "search" in tool_name.lower():
            return f"external:{tool_name}"
        elif "scrape" in tool_name.lower():
            return f"external:{tool_name}"

        # 默认：不加前缀
        return tool_name

    def _get_tool_by_namespaced_name(self, namespaced_name: str, user_id: Optional[int] = None) -> Optional[Callable]:
        """Get tool by its namespaced name (e.g., mcp_akshare_stock_price)
        
        DEPRECATED for MCP tools: The HTTP-based MCP client has been removed.
        MCP tools should be loaded via NativeMCPConfigLoader for CrewAI native integration.
        
        This method still works for non-MCP tools registered in the registry.
        
        Args:
            namespaced_name: Namespaced tool name
            user_id: Optional user ID for user-specific MCP tools
            
        Returns:
            Tool callable or None if not found
        """
        # First check local registry for non-MCP tools
        if namespaced_name in self._tools:
            return self._tools[namespaced_name]
        
        if not self.db:
            return None
            
        try:
            # Query system MCP tools - will return None with deprecation warning
            tool_config = (
                self.db.query(MCPTool)
                .filter(MCPTool.namespaced_name == namespaced_name, MCPTool.is_active == True)
                .first()
            )
            
            if tool_config:
                # Log deprecation notice for MCP tool lookup via this path
                logger.info(
                    f"MCP tool '{namespaced_name}' found in database. "
                    f"For runtime usage, use NativeMCPConfigLoader.create_for_agent() instead."
                )
                
                # Create wrapper for system MCP tool (will return None with warning)
                from AICrews.database.models.mcp import MCPServer
                server = self.db.query(MCPServer).filter(MCPServer.id == tool_config.server_id).first()
                
                if server:
                    return self._create_system_mcp_tool_wrapper(
                        server=server,
                        tool_config=tool_config,
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error looking up tool by namespaced name '{namespaced_name}': {e}")
            return None

    def _get_tool_by_legacy_name(self, legacy_name: str, user_id: Optional[int] = None) -> Optional[Callable]:
        """Get tool by its legacy name (backward compatibility)
        
        DEPRECATED: Legacy tool names are deprecated. The HTTP-based MCP client has been removed.
        MCP tools should be loaded via NativeMCPConfigLoader for CrewAI native integration.
        
        Args:
            legacy_name: Legacy tool name (e.g., stock_price, balance_sheet)
            user_id: Optional user ID for user-specific MCP tools
            
        Returns:
            Tool callable or None if not found
        """
        if not self.db:
            return None
            
        try:
            # Query by legacy_name field
            tool_config = (
                self.db.query(MCPTool)
                .filter(MCPTool.legacy_name == legacy_name, MCPTool.is_active == True)
                .first()
            )
            
            if not tool_config:
                # Fallback: query by tool_name if legacy_name not populated
                tool_config = (
                    self.db.query(MCPTool)
                    .filter(MCPTool.tool_name == legacy_name, MCPTool.is_active == True)
                    .first()
                )
            
            if tool_config:
                # Emit deprecation warning
                logger.warning(
                    f"Tool '{legacy_name}' uses legacy naming and HTTP MCP client (both deprecated). "
                    f"Please update to use NativeMCPConfigLoader with namespaced format: '{tool_config.namespaced_name}'"
                )
                
                # Create wrapper for system MCP tool (will return None with warning)
                from AICrews.database.models.mcp import MCPServer
                server = self.db.query(MCPServer).filter(MCPServer.id == tool_config.server_id).first()
                
                if server:
                    return self._create_system_mcp_tool_wrapper(
                        server=server,
                        tool_config=tool_config,
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error looking up tool by legacy name '{legacy_name}': {e}")
            return None

    def _create_system_mcp_tool_wrapper(
        self,
        server: "MCPServer",
        tool_config: MCPTool,
    ) -> Optional[Callable]:
        """Create wrapper for system MCP tool from database
        
        DEPRECATED: This method used the old HTTP-based MCP client which has been removed.
        Use NativeMCPConfigLoader for CrewAI native MCP integration instead.
        
        Args:
            server: MCP server configuration
            tool_config: Tool configuration from mcp_tools table
            
        Returns:
            None - always returns None as HTTP MCP client is deprecated
        """
        logger.warning(
            f"_create_system_mcp_tool_wrapper is deprecated. "
            f"Tool '{tool_config.namespaced_name}' cannot be loaded via HTTP MCP client. "
            f"Use NativeMCPConfigLoader for CrewAI native MCP integration instead. "
            f"See AICrews/config/mcp.py for usage."
        )
        return None

    # =========================================================================
    # 工具查询接口 (数据库查询)
    # =========================================================================

    def get_all_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已注册的工具（用于 runner summary）"""
        tools_dict = {}

        # Helper to extract metadata from callables
        def extract_meta(funcs, source, category):
            for f in funcs:
                name = getattr(f, "__name__", str(f))
                tools_dict[name] = {
                    "name": name,
                    "source": source,
                    "category": category,
                }

        # System tools removed as per user request
        # extract_meta(self._get_system_mcp_tools(), "builtin", "market_data")
        # extract_meta(self._get_quant_tools(), "builtin", "quant")
        # extract_meta(self._get_external_tools(), "builtin", "external")

        return tools_dict

    def get_tools_for_user(
        self,
        user_id: int,
        tiers: Optional[List[ToolTier]] = None,
        scopes: Optional[List[str]] = None,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """获取用户可用的工具列表 (数据库查询)

        Args:
            user_id: 用户 ID
            tiers: 工具层级筛选 (默认全部层级)
            scopes: 工具范围筛选
            category: 工具分类筛选
            active_only: 是否只返回激活的工具

        Returns:
            工具列表，包含所有层级和来源
        """
        tools = []

        # Tier 1: 内置工具
        if tiers is None or ToolTier.TIER_1_BUILTIN in tiers:
            builtin_tools = self._get_builtin_tools(category, active_only)
            tools.extend(builtin_tools)

        # Tier 2: MCP 工具
        if tiers is None or ToolTier.TIER_2_DATA in tiers:
            mcp_tools = self._get_mcp_tools_for_user(user_id, category, active_only)
            tools.extend(mcp_tools)

        # Tier 3: 知识源工具
        if tiers is None or ToolTier.TIER_3_KNOWLEDGE in tiers:
            knowledge_tools = self._get_knowledge_tools_for_user(
                user_id, category, active_only
            )
            tools.extend(knowledge_tools)

        # Tier 4: 缓存中的工具
        if tiers is None or ToolTier.TIER_4_AGENT in tiers:
            cached_tools = self._get_cached_tools(user_id, category, active_only)
            tools.extend(cached_tools)

        return tools

    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """根据工具名称获取工具

        Args:
            tool_name: 工具名称

        Returns:
            工具信息，如果不存在则返回 None
        """
        # 先检查缓存
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name].to_dict()

        # 检查数据库
        # Builtin Tools
        builtin = (
            self.db.query(BuiltinTool)
            .filter(BuiltinTool.tool_key == tool_name, BuiltinTool.is_active == True)
            .first()
        )

        if builtin:
            return self._builtin_to_dict(builtin)

        # MCP Tools
        mcp_tool = self.db.query(MCPTool).filter(MCPTool.tool_key == tool_name).first()

        if mcp_tool:
            return self._mcp_tool_to_dict(mcp_tool)

        return None

    # =========================================================================
    # Tier 1: 内置工具
    # =========================================================================

    def _get_builtin_tools(
        self, category: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取内置工具列表

        Args:
            category: 工具分类筛选
            active_only: 是否只返回激活的工具

        Returns:
            内置工具列表
        """
        query = self.db.query(BuiltinTool)

        if active_only:
            query = query.filter(BuiltinTool.is_active == True)

        if category:
            query = query.filter(BuiltinTool.category == category)

        builtin_tools = query.order_by(BuiltinTool.sort_order).all()

        return [self._builtin_to_dict(t) for t in builtin_tools]

    def _builtin_to_dict(self, tool: BuiltinTool) -> Dict[str, Any]:
        """将内置工具转换为字典

        Args:
            tool: 内置工具对象

        Returns:
            工具字典
        """
        return {
            "name": tool.tool_key,
            "description": tool.description,
            "source": ToolSource.BUILTIN.value,
            "tier": ToolTier.TIER_1_BUILTIN.value,
            "category": tool.category,
            "icon": tool.icon,
            "is_active": tool.is_active,
            "requires_api_key": tool.requires_api_key,
            "api_key_provider": tool.api_key_provider,
            "config_schema": tool.config_schema,
        }

    # =========================================================================
    # Tier 2: MCP 工具
    # =========================================================================

    def _get_mcp_tools_for_user(
        self, user_id: int, category: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户的 MCP 工具列表

        Args:
            user_id: 用户 ID
            category: 工具分类筛选
            active_only: 是否只返回激活的工具

        Returns:
            MCP 工具列表
        """
        # 获取用户订阅的 MCP 服务器
        user_servers = (
            self.db.query(UserMCPServer).filter(UserMCPServer.user_id == user_id).all()
        )

        tools = []

        for user_server in user_servers:
            if active_only and not user_server.is_enabled:
                continue

            mcp_server = user_server.server
            if not mcp_server or not mcp_server.is_active:
                continue

            # 获取该服务器的所有工具
            server_tools = (
                self.db.query(MCPTool).filter(MCPTool.server_id == mcp_server.id).all()
            )

            for tool in server_tools:
                if category and tool.category != category:
                    continue

                tools.append(self._mcp_tool_to_dict(tool, mcp_server))

        return tools

    def _mcp_tool_to_dict(
        self, tool: MCPTool, server: Optional[MCPServer] = None
    ) -> Dict[str, Any]:
        """将 MCP 工具转换为字典

        Args:
            tool: MCP 工具对象
            server: MCP 服务器对象

        Returns:
            工具字典
        """
        if server is None:
            server = tool.server

        return {
            "name": tool.tool_key,
            "display_name": tool.display_name,
            "description": tool.description,
            "source": ToolSource.MCP.value,
            "tier": ToolTier.TIER_2_DATA.value,
            "category": tool.category,
            "server_name": server.name if server else None,
            "server_key": server.server_key if server else None,
            "is_active": tool.is_active and server.is_active
            if server
            else tool.is_active,
            "config_schema": tool.config_schema,
        }

    # =========================================================================
    # Tier 3: 知识源工具
    # =========================================================================

    def _get_knowledge_tools_for_user(
        self, user_id: int, category: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户的知识源工具列表

        Args:
            user_id: 用户 ID
            category: 工具分类筛选
            active_only: 是否只返回激活的工具

        Returns:
            知识源工具列表
        """
        # 获取用户的知识源
        user_knowledge = (
            self.db.query(UserKnowledgeSource)
            .filter(UserKnowledgeSource.user_id == user_id)
            .all()
        )

        tools = []

        for uk in user_knowledge:
            if active_only and not uk.is_enabled:
                continue

            knowledge_source = uk.knowledge_source
            if not knowledge_source or not knowledge_source.is_active:
                continue

            tools.append(
                {
                    "name": f"knowledge_{knowledge_source.source_key}",
                    "display_name": knowledge_source.display_name,
                    "description": f"Access {knowledge_source.display_name} knowledge",
                    "source": ToolSource.OTHER.value,
                    "tier": ToolTier.TIER_3_KNOWLEDGE.value,
                    "category": category or "knowledge",
                    "knowledge_id": knowledge_source.id,
                    "knowledge_type": knowledge_source.source_type,
                    "is_active": uk.is_enabled,
                }
            )

        return tools

    # =========================================================================
    # Tier 4: 缓存中的工具
    # =========================================================================

    def _get_cached_tools(
        self, user_id: int, category: Optional[str] = None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """从缓存获取 Agent 特定工具

        Args:
            user_id: 用户 ID
            category: 工具分类筛选
            active_only: 是否只返回激活的工具

        Returns:
            缓存工具列表
        """
        tools = []

        for tool_name, tool in self._tool_cache.items():
            if active_only and not tool.is_active:
                continue

            if category and tool.category != category:
                continue

            # 检查工具是否属于该用户
            # 这里简化处理：假设缓存中的工具都可以使用
            # 实际应该检查工具的 user_id 或权限

            tools.append(tool.to_dict())

        return tools

    # =========================================================================
    # Agent 工具绑定
    # =========================================================================

    def get_tools_for_agent(
        self, agent_id: int, loadout_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取 Agent 的工具配置

        根据 4-Tier Loadout 配置返回工具列表。

        Args:
            agent_id: Agent ID
            loadout_config: 工具配置字典
                {
                    "tier_1": [...],  # Builtin tools
                    "tier_2": [...],  # MCP tools
                    "tier_3": [...],  # Knowledge sources
                    "tier_4": [...],  # Agent-specific tools
                }

        Returns:
            工具列表
        """
        agent = (
            self.db.query(AgentDefinition)
            .filter(AgentDefinition.id == agent_id)
            .first()
        )

        if not agent:
            return []

        # 使用 loadout_config 或从 agent.loadout_data 读取
        config = loadout_config or agent.loadout_data or {}

        tools = []
        user_id = agent.user_id

        # Tier 1: 内置工具
        tier_1_tools = config.get("tier_1", [])
        if tier_1_tools:
            for tool_name in tier_1_tools:
                tool = self.get_tool_by_name(tool_name)
                if tool:
                    tools.append(tool)

        # Tier 2: MCP 工具
        tier_2_tools = config.get("tier_2", [])
        if tier_2_tools:
            mcp_tools = self._get_mcp_tools_for_user(user_id)
            for tool in mcp_tools:
                if tool["name"] in tier_2_tools:
                    tools.append(tool)

        # Tier 3: 知识源
        tier_3_tools = config.get("tier_3", [])
        if tier_3_tools:
            knowledge_tools = self._get_knowledge_tools_for_user(user_id)
            for tool in knowledge_tools:
                if tool["name"] in tier_3_tools or tool["knowledge_id"] in tier_3_tools:
                    tools.append(tool)

        # Tier 4: Agent 特定工具
        tier_4_tools = config.get("tier_4", [])
        if tier_4_tools:
            cached_tools = self._get_cached_tools(user_id)
            for tool in cached_tools:
                if tool["name"] in tier_4_tools:
                    tools.append(tool)

        return tools

    # =========================================================================
    # 工具发现和管理方法
    # =========================================================================

    def get_tool_info(self, tool_key: str) -> Optional[Dict[str, Any]]:
        """获取工具详情

        Args:
            tool_key: 工具键

        Returns:
            工具详情字典
        """
        return self.get_tool_by_name(tool_key)

    def get_all_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有注册的工具信息

        Returns:
            工具信息字典
        """
        tools = {}

        # 缓存的工具
        for tool_name, tool in self._tool_cache.items():
            tools[tool_name] = tool.to_dict()

        # 数据库中的工具
        builtin_tools = self._get_builtin_tools()
        for tool in builtin_tools:
            tools[tool["name"]] = tool

        mcp_tools = self._get_mcp_tools_for_user(user_id=0)  # 系统工具
        for tool in mcp_tools:
            tools[tool["name"]] = tool

        return tools

    async def connect_user_mcp(self, user_id: int, server_url: str) -> Dict[str, Any]:
        """连接用户自定义 MCP 服务器并发现工具

        Args:
            user_id: 用户 ID
            server_url: MCP 服务器 URL

        Returns:
            连接结果和发现的工具列表
        """
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            discovered_tools = []

            async with sse_client(server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 发现可用工具
                    tools_result = await session.list_tools()

                    for tool in tools_result.tools:
                        discovered_tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.inputSchema
                                if hasattr(tool, "inputSchema")
                                else None,
                            }
                        )

            return {
                "success": True,
                "server_url": server_url,
                "tools_count": len(discovered_tools),
                "tools": discovered_tools,
            }

        except Exception as e:
            logger.error(f"Error connecting to MCP server {server_url}: {e}")
            return {"success": False, "server_url": server_url, "error": str(e)}


# =========================================================================
# 便捷函数
# =========================================================================


async def get_tools_for_agent(
    user_id: Optional[int] = None, db: Optional[Session] = None
) -> List[Callable]:
    """获取适用于 Agent 的工具列表

    这是给 CrewAI Agent 使用的便捷函数

    Args:
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        CrewAI 工具列表
    """
    registry = ToolRegistry(db=db) if db else ToolRegistry(db=None)
    return await registry.get_user_tools(user_id)


async def create_agent_with_tools(
    user_id: int, role: str, goal: str, backstory: str, llm, db: Session = None
):
    """创建配置了工具的 Agent

    Args:
        user_id: 用户 ID
        role: Agent 角色
        goal: Agent 目标
        backstory: Agent 背景故事
        llm: LLM 实例
        db: 数据库会话

    Returns:
        配置了个性化工具的 CrewAI Agent
    """
    from crewai import Agent

    registry = ToolRegistry(db=db)
    tools = await registry.get_user_tools(user_id)

    agent = Agent(
        role=role, goal=goal, backstory=backstory, tools=tools, llm=llm, verbose=True
    )

    return agent


__all__ = [
    "ToolRegistry",
    "get_tools_for_agent",
    "create_agent_with_tools",
]
