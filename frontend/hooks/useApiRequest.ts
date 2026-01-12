import { useCallback, useRef } from 'react';

/**
 * API 请求 Hook，支持请求取消
 * 用于防止组件卸载时的内存泄漏
 */
export function useApiRequest() {
  const abortControllers = useRef<Map<string, AbortController>>(new Map());

  /**
   * 取消指定 key 的请求
   */
  const abort = useCallback((key: string) => {
    const controller = abortControllers.current.get(key);
    if (controller) {
      controller.abort();
      abortControllers.current.delete(key);
    }
  }, []);

  /**
   * 执行请求，支持自动取消之前的同名请求
   * @param key 请求的唯一标识，用于取消之前的请求
   * @param fetchFn 实际的请求函数
   * @returns 请求结果
   */
  const request = useCallback(async <T>(
    key: string,
    fetchFn: (signal: AbortSignal) => Promise<T>
  ): Promise<T> => {
    // 取消之前的同名请求
    abort(key);
    
    const controller = new AbortController();
    abortControllers.current.set(key, controller);

    try {
      const result = await fetchFn(controller.signal);
      abortControllers.current.delete(key);
      return result;
    } catch (error) {
      abortControllers.current.delete(key);
      
      // 如果是取消操作，不抛出错误
      if (error instanceof Error && error.name === 'AbortError') {
        return undefined as T;
      }
      
      throw error;
    }
  }, [abort]);

  /**
   * 取消所有请求
   */
  const abortAll = useCallback(() => {
    abortControllers.current.forEach(controller => {
      controller.abort();
    });
    abortControllers.current.clear();
  }, []);

  return { request, abort, abortAll };
}
