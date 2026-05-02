import { useEffect, useState, useCallback, useRef } from 'react';

export interface PollingOptions {
  /** 轮询 URL（传入时使用 fetch 模式） */
  url?: string;
  /** 轮询间隔（ms），默认 5000 */
  interval?: number;
  /** 是否启用，默认 true */
  enabled?: boolean;
}

export interface UsePollingResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  start: () => void;
  stop: () => void;
}

/**
 * 通用轮询 Hook — 支持两种调用模式
 *
 * 模式 A（fetch 模式）：
 *   const { data } = usePolling({ url: '/api/xxx', interval: 3000 });
 *
 * 模式 B（自定义 callback 模式 — 用于 store action）：
 *   usePolling(() => { fetchData(); }, 5000);
 *   // 返回 { data: null, loading: false, error: null, start, stop }
 *
 * P4-4: 修复 positions board 使用模式 B 时类型不匹配的问题
 */
export function usePolling<T = unknown>(
  optionsOrCallback: PollingOptions | (() => void),
  intervalOrOptions?: number | PollingOptions,
): UsePollingResult<T> {
  // 检测调用模式
  const isCallbackMode = typeof optionsOrCallback === 'function';

  const callback = isCallbackMode ? (optionsOrCallback as () => void) : undefined;
  const options: PollingOptions = isCallbackMode
    ? (typeof intervalOrOptions === 'number' ? { interval: intervalOrOptions } : {})
    : (optionsOrCallback as PollingOptions);

  const { url, interval = 5000, enabled = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // fetch 模式下使用 fetchData；callback 模式下直接调用 callback
  const tick = useCallback(async () => {
    if (url) {
      // fetch 模式
      setLoading(true);
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const json: T = await res.json();
        if (mountedRef.current) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (mountedRef.current) {
          setError(e instanceof Error ? e : new Error(String(e)));
        }
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    } else if (callback) {
      // callback 模式（用于 store action）
      callback();
    }
  }, [url, callback]);

  const start = useCallback(() => {
    if (timerRef.current) return;
    tick(); // 立即执行一次
    timerRef.current = setInterval(tick, interval);
  }, [tick, interval]);

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      start();
    }
    return () => {
      mountedRef.current = false;
      stop();
    };
  }, [enabled, start, stop]);

  return { data, loading, error, start, stop };
}
