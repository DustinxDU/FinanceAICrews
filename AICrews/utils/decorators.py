import time
import functools
import traceback
from typing import Optional, Callable, Any
from .logger import logger, get_module_logger, LogModule


def monitor(
    log_level: str = "INFO",
    log_args: bool = False,
    log_result: bool = False,
    performance_threshold_ms: Optional[float] = None,
    module: Optional[str] = None,
    custom_logger: Optional[Any] = None
):
    """
    增强版性能监控装饰器
    
    功能:
    1. 记录函数开始和结束
    2. 计算执行时间 (ms)
    3. 支持分级日志输出 (DEBUG/INFO/WARNING/ERROR)
    4. 性能阈值告警（超时自动升级为 WARNING）
    5. 可选择记录调用参数和返回结果
    6. 捕获并详细记录异常（包括堆栈跟踪）
    7. 支持按业务模块分类记录
    
    Args:
        log_level: 日志级别 ('DEBUG'/'INFO'/'WARNING'/'ERROR')
        log_args: 是否记录函数调用参数
        log_result: 是否记录函数返回结果
        performance_threshold_ms: 性能阈值(毫秒)，超过时告警
        module: 业务模块名称 (trading/risk/data等)
        custom_logger: 自定义logger实例
    
    Examples:
        >>> @monitor()
        >>> def simple_func():
        >>>     return "result"
        
        >>> @monitor(log_level="DEBUG", log_args=True, log_result=True)
        >>> def detailed_func(x, y):
        >>>     return x + y
        
        >>> @monitor(performance_threshold_ms=1000, module="trading")
        >>> def trading_execution():
        >>>     # 如果执行超过1秒，会自动记录WARNING
        >>>     pass
        
        >>> @monitor(log_level="ERROR", module="database")
        >>> def critical_db_operation():
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 确定使用的logger
            if custom_logger:
                log = custom_logger
            elif module:
                log = get_module_logger(module)
            else:
                log = logger
            
            start_time = time.time()
            func_name = func.__name__
            module_name = func.__module__
            
            # 记录函数调用开始
            if log_args:
                # 格式化参数信息（限制长度避免日志过长）
                args_str = str(args)[:200] if args else "()"
                kwargs_str = str(kwargs)[:200] if kwargs else "{}"
                log.debug(
                    f"🔹 [Call] {module_name}.{func_name} | "
                    f"args={args_str}, kwargs={kwargs_str}"
                )
            else:
                log.debug(f"🔹 [Call] {module_name}.{func_name}")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000  # 毫秒
                
                # 判断是否超过性能阈值
                is_slow = (
                    performance_threshold_ms is not None and 
                    execution_time > performance_threshold_ms
                )
                
                # 根据性能表现选择日志级别
                if is_slow:
                    log.warning(
                        f"⚠️ [Performance] {module_name}.{func_name} 执行耗时 {execution_time:.2f}ms "
                        f"(超过阈值 {performance_threshold_ms}ms)"
                    )
                else:
                    # 正常完成，按指定级别记录
                    log_func = getattr(log, log_level.lower(), log.info)
                    log_func(
                        f"✅ [Success] {module_name}.{func_name} 完成 | "
                        f"耗时: {execution_time:.2f}ms"
                    )
                
                # 记录返回结果
                if log_result:
                    result_str = str(result)[:500]  # 限制长度
                    log.debug(f"🔹 [Result] {module_name}.{func_name} | result={result_str}")
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # 记录异常详情
                error_msg = (
                    f"❌ [Error] {module_name}.{func_name} 失败 | "
                    f"耗时: {execution_time:.2f}ms | "
                    f"错误类型: {type(e).__name__} | "
                    f"错误信息: {str(e)}"
                )
                
                # 记录详细堆栈跟踪
                log.error(error_msg, exc_info=True)
                
                # 重新抛出异常，让上层处理
                raise
        
        return wrapper
    
    # 支持两种调用方式
    # @monitor 或 @monitor()
    if callable(log_level):
        func = log_level
        log_level = "INFO"
        return decorator(func)
    
    return decorator


def log_execution(
    module: str,
    level: str = "INFO",
    include_args: bool = False
):
    """
    简化版日志装饰器，专注于业务模块分类
    
    Args:
        module: 业务模块 (trading/risk/data等)
        level: 日志级别
        include_args: 是否记录参数
    
    Examples:
        >>> @log_execution(module="trading", level="INFO")
        >>> def execute_trade(symbol, quantity):
        >>>     pass
        
        >>> @log_execution(module="risk", level="WARNING")
        >>> def check_risk_limits():
        >>>     pass
    """
    return monitor(
        log_level=level,
        log_args=include_args,
        module=module
    )


def performance_critical(
    threshold_ms: float = 1000,
    module: str = LogModule.PERFORMANCE
):
    """
    标记性能关键函数，自动监控执行时间
    
    Args:
        threshold_ms: 性能阈值(毫秒)
        module: 业务模块
    
    Examples:
        >>> @performance_critical(threshold_ms=500)
        >>> def fast_calculation():
        >>>     pass
        
        >>> @performance_critical(threshold_ms=2000, module="database")
        >>> def complex_query():
        >>>     pass
    """
    return monitor(
        performance_threshold_ms=threshold_ms,
        module=module,
        log_level="DEBUG"
    )


def trace_debug(
    module: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = True
):
    """
    调试追踪装饰器，详细记录函数调用信息
    
    Args:
        module: 业务模块
        log_args: 记录调用参数
        log_result: 记录返回结果
    
    Examples:
        >>> @trace_debug()
        >>> def debug_function(x, y):
        >>>     return x + y
        
        >>> @trace_debug(module="data")
        >>> def process_data(data):
        >>>     return data
    """
    return monitor(
        log_level="DEBUG",
        log_args=log_args,
        log_result=log_result,
        module=module
    )


def error_handler(
    module: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    错误处理装饰器，捕获并记录异常

    Args:
        module: 业务模块
        reraise: 是否重新抛出异常
        default_return: 异常时的默认返回值

    Examples:
        >>> @error_handler(module="database")
        >>> def risky_db_operation():
        >>>     # 异常会被记录并重新抛出
        >>>     pass

        >>> @error_handler(reraise=False, default_return=[])
        >>> def safe_operation():
        >>>     # 异常时返回空列表，不抛出
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log = get_module_logger(module) if module else logger

            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_name = f"{func.__module__}.{func.__name__}"
                log.error(
                    f"❌ [Exception] {func_name} | "
                    f"错误: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )

                if reraise:
                    raise
                else:
                    log.warning(
                        f"⚠️ [Suppressed] {func_name} 异常已被抑制 | "
                        f"返回默认值: {default_return}"
                    )
                    return default_return

        return wrapper

    return decorator


def error_handler_async(
    module: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    异步版错误处理装饰器

    Args:
        module: 业务模块
        reraise: 是否重新抛出异常
        default_return: 异常时的默认返回值

    Examples:
        >>> @error_handler_async(module="database")
        >>> async def async_db_operation():
        >>>     # 异常会被记录并重新抛出
        >>>     pass

        >>> @error_handler_async(reraise=False, default_return=[])
        >>> async def safe_async_operation():
        >>>     # 异常时返回空列表，不抛出
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            log = get_module_logger(module) if module else logger

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                func_name = f"{func.__module__}.{func.__name__}"
                log.error(
                    f"❌ [Exception] {func_name} | "
                    f"错误: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )

                if reraise:
                    raise
                else:
                    log.warning(
                        f"⚠️ [Suppressed] {func_name} 异常已被抑制 | "
                        f"返回默认值: {default_return}"
                    )
                    return default_return

        return wrapper

    return decorator


__all__ = [
    'monitor',
    'log_execution',
    'performance_critical',
    'trace_debug',
    'error_handler',
    'error_handler_async',
]