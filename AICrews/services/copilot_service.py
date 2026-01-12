import asyncio
from AICrews.observability.logging import get_logger
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.database.models.user import User
from AICrews.database.models.llm import UserModelConfig
from AICrews.llm.unified_manager import get_unified_llm_manager
from AICrews.schemas.copilot import CopilotMessage

from AICrews.config.prompt_config import get_prompt_config_loader

logger = get_logger(__name__)

# 获取配置加载器
prompt_loader = get_prompt_config_loader()
copilot_config = prompt_loader.get_config("copilot")

MAX_HISTORY_LENGTH = copilot_config.get("max_history_length", 6)
COPILOT_SYSTEM_PROMPT = copilot_config.get(
    "system_prompt", "You are FinanceAI Copilot."
)


class ThinkTagParser:
    """解析 <think>...</think> 标签，支持跨 chunk 处理。

    用于处理思考模型（如 GLM-4.6、DeepSeek-R1）的输出，
    将 thinking 内容和正常回答内容分开。
    """

    def __init__(self):
        self.buffer = ""
        self.in_think = False

    def feed(self, text: str) -> List[Tuple[str, str]]:
        """
        输入文本，返回 [(type, content), ...] 列表。

        Args:
            text: 输入的文本 chunk

        Returns:
            List of (type, content) tuples where type is 'thinking' or 'content'

        处理逻辑：
        1. 遇到 <think> 开始标签 → 切换到 thinking 模式
        2. 遇到 </think> 结束标签 → 切换回 content 模式
        3. 标签不完整时缓冲等待下一个 chunk
        """
        self.buffer += text
        results = []

        while True:
            if self.in_think:
                # 在 thinking 模式，寻找 </think>
                end_idx = self.buffer.find("</think>")
                if end_idx != -1:
                    thinking_content = self.buffer[:end_idx]
                    if thinking_content:
                        results.append(("thinking", thinking_content))
                    self.buffer = self.buffer[end_idx + 8:]  # len("</think>") = 8
                    self.in_think = False
                else:
                    # 未找到结束标签，检查是否有部分标签需要保留
                    safe_len = self._find_safe_length(self.buffer, "</think>")
                    if safe_len > 0:
                        results.append(("thinking", self.buffer[:safe_len]))
                        self.buffer = self.buffer[safe_len:]
                    break
            else:
                # 在 content 模式，寻找 <think>
                start_idx = self.buffer.find("<think>")
                if start_idx != -1:
                    content_before = self.buffer[:start_idx]
                    if content_before:
                        results.append(("content", content_before))
                    self.buffer = self.buffer[start_idx + 7:]  # len("<think>") = 7
                    self.in_think = True
                else:
                    # 未找到开始标签，检查是否有部分标签需要保留
                    safe_len = self._find_safe_length(self.buffer, "<think>")
                    if safe_len > 0:
                        results.append(("content", self.buffer[:safe_len]))
                        self.buffer = self.buffer[safe_len:]
                    break

        return results

    def _find_safe_length(self, text: str, tag: str) -> int:
        """找到可以安全输出的长度（避免截断部分标签）。

        例如：如果 text 以 "<thi" 结尾，而 tag 是 "<think>"，
        则返回 len(text) - 4，保留 "<thi" 在缓冲区中。
        """
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return len(text) - i
        return len(text)

    def flush(self) -> List[Tuple[str, str]]:
        """流结束时，输出缓冲区剩余内容。"""
        results = []
        if self.buffer:
            chunk_type = "thinking" if self.in_think else "content"
            results.append((chunk_type, self.buffer))
            self.buffer = ""
        return results


class CopilotService:
    """Copilot服务 - 处理对话和LLM调用"""

    def __init__(self, db: Session, user_id: int, llm_config_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.llm_config_id = llm_config_id
        self._skip_thinking_models = False  # 允许使用思考模型
        self.redis = get_redis_manager()
        self.history_key = f"copilot:history:{user_id}"

    async def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取用户对话历史 (从 Redis)"""
        history = await self.redis.get_json(self.history_key)
        return history or []

    async def add_message(self, role: str, content: str):
        """添加消息到历史 (存入 Redis)"""
        history = await self.get_conversation_history()
        history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # 保持历史长度限制
        if len(history) > MAX_HISTORY_LENGTH * 2:
            history = history[-MAX_HISTORY_LENGTH * 2 :]

        # 存回 Redis (设置 24小时 TTL)
        await self.redis.set(self.history_key, history, ttl=86400)

    async def clear_history(self):
        """清除对话历史"""
        await self.redis.delete(self.history_key)

    def _normalize_llm_output(self, output: Any) -> str:
        if output is None:
            return ""
        if isinstance(output, str):
            return output
        if hasattr(output, "content"):
            return str(getattr(output, "content"))
        if isinstance(output, dict) and "content" in output:
            return str(output["content"])
        return str(output)

    def _iter_text_chunks(self, text: str, chunk_size: int = 48):
        if not text:
            return
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]

    async def _call_llm_instance(self, llm: Any, prompt: str) -> str:
        if hasattr(llm, "acall") and callable(getattr(llm, "acall")):
            result = await llm.acall(prompt)
            return self._normalize_llm_output(result)
        if hasattr(llm, "call") and callable(getattr(llm, "call")):
            result = await asyncio.to_thread(llm.call, prompt)
            return self._normalize_llm_output(result)
        # Try direct invocation
        try:
            result = await asyncio.to_thread(llm.invoke, prompt)
            return self._normalize_llm_output(result)
        except AttributeError:
            # Fallback for different LLM object interfaces
            result = await asyncio.to_thread(llm, prompt)
            return self._normalize_llm_output(result)

    async def search_web(self, query: str) -> List[Dict[str, Any]]:
        """通过MCP进行联网搜索 (已禁用以提升速度)"""
        return []

    async def get_market_context(self, ticker: str) -> Dict[str, Any]:
        """获取资产的市场上下文 (已禁用以提升速度)"""
        return {}

    async def generate_response(
        self,
        message: str,
        context: Optional[str] = None,
        enable_web_search: bool = False,
    ) -> Tuple[str, List[str], bool]:
        """生成Copilot响应 (非流式)"""

        (
            full_prompt,
            sources,
            search_performed,
            additional_context,
        ) = await self._prepare_context(message, context, enable_web_search)

        # 调用LLM生成响应
        response = await self._call_llm(full_prompt, message, additional_context)

        # 保存对话历史
        await self.add_message("user", message)
        await self.add_message("assistant", response)

        return response, sources, search_performed

    async def generate_streaming_response(
        self,
        message: str,
        context: Optional[str] = None,
        enable_web_search: bool = False,
    ):
        """生成Copilot流式响应

        直接使用 litellm 的流式 API，无需依赖 CrewAI 事件总线。
        Copilot 是简单的对话场景，不需要 Agent/Crew 机制。

        Thinking Mode:
        - enable_thinking=False: 过滤掉 <think>...</think> 标签内容
        - enable_thinking=True: 区分 thinking 和 content，前端可展示可折叠的 thinking 区域
        """
        import litellm

        (
            full_prompt,
            sources,
            search_performed,
            additional_context,
        ) = await self._prepare_context(message, context, enable_web_search)

        # 保存用户消息
        await self.add_message("user", message)

        # 获取 LLM 配置参数
        try:
            llm_config = await self._get_llm_config()
        except Exception as e:
            logger.error(f"Failed to get LLM config: {e}", exc_info=True)
            yield f"data: {json.dumps({'content': f'[Error: {str(e)}]'})}\n\n"
            return

        # 应用配置参数
        llm_params = copilot_config.get("llm_params", {})
        temperature = llm_params.get("temperature", 0.7)
        max_tokens = llm_params.get("max_tokens", 4096)

        # 构建消息格式
        messages = [{"role": "user", "content": full_prompt}]

        full_response = ""
        full_thinking = ""
        enable_thinking = llm_config.get("enable_thinking", False)
        parser = ThinkTagParser()

        # 直接使用 litellm 流式调用
        try:
            logger.info(f"[STREAM] Starting litellm streaming: model={llm_config['model']}, enable_thinking={enable_thinking}")

            # 构建额外参数（用于支持 MiniMax reasoning_split 等）
            extra_kwargs = {}
            if enable_thinking:
                # MiniMax M2.1 需要 reasoning_split=true 来分离 thinking 内容
                extra_kwargs["extra_body"] = {"reasoning_split": True}

            # 使用 litellm.acompletion 进行异步流式调用
            response = await litellm.acompletion(
                model=llm_config["model"],
                messages=messages,
                api_key=llm_config.get("api_key"),
                api_base=llm_config.get("api_base"),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **extra_kwargs,
            )

            # 迭代流式响应
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # 处理 reasoning_content（MiniMax/DeepSeek 思考模型的 thinking 内容）
                    reasoning_content = getattr(delta, "reasoning_content", None)
                    if reasoning_content and enable_thinking:
                        full_thinking += reasoning_content
                        yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning_content})}\n\n"

                    # 处理正常 content（可能包含 <think> 标签）
                    content = getattr(delta, "content", None)
                    if content:
                        # 使用 ThinkTagParser 解析 <think> 标签
                        for chunk_type, chunk_content in parser.feed(content):
                            if not enable_thinking:
                                # 模式1: 过滤 <think> 标签，只输出 content 类型
                                if chunk_type == "content":
                                    full_response += chunk_content
                                    yield f"data: {json.dumps({'content': chunk_content})}\n\n"
                            else:
                                # 模式2: 区分 thinking 和 content（实时流式）
                                if chunk_type == "thinking":
                                    full_thinking += chunk_content
                                    logger.debug(f"[STREAM] Sending thinking chunk: {chunk_content[:50]}...")
                                else:
                                    full_response += chunk_content
                                yield f"data: {json.dumps({'type': chunk_type, 'content': chunk_content})}\n\n"

            # 流结束时，输出缓冲区剩余内容
            for chunk_type, chunk_content in parser.flush():
                if not enable_thinking:
                    if chunk_type == "content":
                        full_response += chunk_content
                        yield f"data: {json.dumps({'content': chunk_content})}\n\n"
                else:
                    if chunk_type == "thinking":
                        full_thinking += chunk_content
                    else:
                        full_response += chunk_content
                    yield f"data: {json.dumps({'type': chunk_type, 'content': chunk_content})}\n\n"

            # 保存助手回复（只保存正常回答内容，不保存 thinking）
            await self.add_message("assistant", full_response)
            logger.info(f"[STREAM] Completed. Response length: {len(full_response)}, Thinking length: {len(full_thinking)}")

        except Exception as e:
            logger.error(f"Streaming LLM call failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'content': f'[Error: {str(e)}]'})}\n\n"

    async def _get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置参数（用于直接调用 litellm）"""
        from AICrews.llm.policy_router import LLMPolicyRouter
        from AICrews.llm.core.config_store import get_config_store
        from AICrews.schemas.llm_policy import LLMScope

        # 检查是否有环境变量配置
        if LLMPolicyRouter.is_env_configured(LLMScope.COPILOT):
            from AICrews.llm.system_config import get_system_llm_config_store

            store = get_system_llm_config_store()
            config = store.get_config(LLMScope.COPILOT)

            provider = config.provider
            model = config.model

            # 从 providers.yaml 获取 provider 配置
            config_store = get_config_store()
            provider_config = config_store.get_provider(provider)

            if provider_config:
                # 使用配置中的 llm_model_prefix
                prefix = provider_config.llm_model_prefix or ""
                litellm_model = f"{prefix}{model}"
                api_base = config.base_url or provider_config.endpoints.api_base
            else:
                # 回退：直接使用模型名
                litellm_model = model
                api_base = config.base_url

            logger.info(f"Using env-based LLM config: provider={provider}, model={model}, litellm_model={litellm_model}")

            return {
                "model": litellm_model,
                "api_key": config.api_key,
                "api_base": api_base,
                "enable_thinking": config.enable_thinking,
            }

        # 回退到 proxy 模式（暂不支持流式）
        raise ValueError("Streaming requires env-based LLM configuration. Set FAIC_LLM_COPILOT_* env vars.")

    async def _get_llm_instance(self) -> Any:
        """
        获取 LLM 实例 (优先使用环境变量配置，支持热更新)

        Routing flow:
        1. Check if env-based config exists for COPILOT scope
        2. If yes: Use direct LLM creation (bypasses proxy, supports hot updates)
        3. If no: Fall back to LLM Policy Router with proxy

        The env-based approach is preferred because:
        - Supports hot updates via POST /api/v1/llm-policy/system-config/reload
        - Simpler configuration (just set env vars)
        - No proxy dependency for system scopes
        """
        import os
        import uuid
        from AICrews.llm.policy_router import LLMPolicyRouter
        from AICrews.schemas.llm_policy import LLMScope

        # Try env-based direct LLM first (preferred for system scopes)
        if LLMPolicyRouter.is_env_configured(LLMScope.COPILOT):
            return await self._get_llm_from_env()

        # Fall back to proxy-based routing
        return await self._get_llm_from_proxy()

    async def _get_llm_from_env(self) -> Any:
        """
        Get LLM instance from environment-based configuration.

        Uses SystemLLMConfigStore for hot-reloadable config.
        """
        from AICrews.llm.policy_router import LLMPolicyRouter
        from AICrews.llm.unified_manager import get_unified_llm_manager
        from AICrews.schemas.llm_policy import LLMScope

        # Create a temporary router instance just to resolve the config
        # (We don't need proxy_base_url or encryption_key for direct resolution)
        router = LLMPolicyRouter(
            proxy_base_url="",  # Not used for direct resolution
            encryption_key=b"",  # Not used for direct resolution
        )

        # Resolve to DirectLLMCall
        direct_call = router.resolve_system_direct(
            scope=LLMScope.COPILOT,
            custom_tags=["product:copilot", "feature:chat"],
        )

        logger.info(
            f"Using env-based LLM for copilot: provider={direct_call.provider}, "
            f"model={direct_call.model}, run_id={direct_call.metadata.get('run_id')}"
        )

        # Create LLM instance via UnifiedLLMManager
        manager = get_unified_llm_manager()
        llm = manager.create_default_llm(**direct_call.to_llm_params())

        return llm

    async def _get_llm_from_proxy(self) -> Any:
        """
        Get LLM instance via LLM Policy Router (proxy-based).

        Legacy approach - used when env-based config is not available.
        """
        import os
        import uuid
        from sqlalchemy import select
        from AICrews.llm.policy_router import LLMPolicyRouter
        from AICrews.llm.proxy_provider import ProxyProvider
        from AICrews.schemas.llm_policy import UserContext, LLMScope
        from AICrews.database.models.user import User

        # Get user from DB
        user_stmt = select(User).where(User.id == self.user_id)
        user = self.db.execute(user_stmt).scalar_one_or_none()

        if not user:
            raise ValueError(f"User {self.user_id} not found")

        # Build UserContext for router
        user_context = UserContext(
            user_id=user.id,
            email=user.email,
            subscription_level=getattr(user, "subscription_level", "free"),
            is_active=getattr(user, "is_active", True),
        )

        # Get LiteLLM proxy configuration
        proxy_base_url = os.getenv("LITELLM_PROXY_BASE_URL", "http://litellm:4000/v1")

        # Get encryption key (for decrypting API keys)
        encryption_key_str = os.getenv("ENCRYPTION_KEY")
        if not encryption_key_str:
            logger.warning("ENCRYPTION_KEY not set; using default dev key (NOT for production)")
        from AICrews.utils.encryption import get_encryption_key_bytes

        encryption_key = get_encryption_key_bytes()

        # Resolve LLM call via Policy Router
        router = LLMPolicyRouter(
            proxy_base_url=proxy_base_url,
            encryption_key=encryption_key
        )

        # Generate run_id for tracing
        run_id = str(uuid.uuid4())

        # Custom tags for copilot context
        custom_tags = ["product:copilot", "feature:chat"]

        resolved_call = router.resolve(
            scope=LLMScope.COPILOT,
            user_context=user_context,
            db=self.db,
            custom_tags=custom_tags,
        )

        logger.info(
            f"Resolved LLM call for copilot: model={resolved_call.model}, "
            f"run_id={run_id}, user_id={user.id}"
        )

        # Create LLM instance via ProxyProvider
        proxy_provider = ProxyProvider()
        llm = proxy_provider.create_llm(resolved_call)
        return llm

    async def _call_llm(
        self, full_prompt: str, user_message: str, context_str: str
    ) -> str:
        """调用 LLM 生成回答 (非流式)"""
        llm = await self._get_llm_instance()

        # 应用配置参数
        llm_params = copilot_config.get("llm_params", {})
        if "temperature" in llm_params:
            llm.temperature = llm_params["temperature"]
        if "max_tokens" in llm_params:
            llm.max_tokens = llm_params["max_tokens"]

        try:
            response = await llm.ainvoke(full_prompt)
            return self._normalize_llm_output(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    async def _prepare_context(
        self,
        message: str,
        context: Optional[str] = None,
        enable_web_search: bool = False,
    ) -> Tuple[str, List[str], bool, str]:
        """准备对话上下文和Prompt (简化版，提升速度)"""
        sources = []
        search_performed = False
        additional_context = ""

        # 跳过 MCP 搜索和市场数据获取以提升速度
        if False and enable_web_search:  # 已禁用
            pass

        # 简化的对话历史 (仅最近2轮)
        history = await self.get_conversation_history()
        history_text = ""
        for msg in history[-4:]:  # 最近2轮对话
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

        # 构建简洁的prompt
        full_prompt = f"""{COPILOT_SYSTEM_PROMPT}

**Context:**
{context if context else "No additional context provided."}

**Conversation History:**
{history_text}

**User Question:**
{message}

**Answer:**"""

        return full_prompt, sources, search_performed, additional_context
