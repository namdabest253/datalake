/**
 * Tiny "useAsync" hook. Avoids pulling react-query in for five fetches.
 *
 * Returns `{ data, loading, error }`. The fetcher closure is invoked once on
 * mount and re-invoked whenever any value in `deps` changes (same semantics
 * as React's stock `useEffect` dependency list).
 *
 * Pass `opts.cacheKey` to share results across mounts (e.g. between page
 * navigations). On remount we seed `data` from the module-level cache
 * immediately so the UI renders prior values without a loading flash, then
 * the fetcher runs in the background to revalidate.
 */

import { useEffect, useState } from "react";

export type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const cache = new Map<string, unknown>();

export function clearApiCache(key?: string): void {
  if (key === undefined) cache.clear();
  else cache.delete(key);
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  opts: { cacheKey?: string } = {},
): AsyncState<T> {
  const { cacheKey } = opts;
  const [state, setState] = useState<AsyncState<T>>(() => {
    const cached = cacheKey !== undefined ? (cache.get(cacheKey) as T | undefined) : undefined;
    return {
      data: cached ?? null,
      loading: cached === undefined,
      error: null,
    };
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => (s.data === null ? { ...s, loading: true, error: null } : s));
    fetcher()
      .then((data) => {
        if (cacheKey !== undefined) cache.set(cacheKey, data);
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err);
          setState((s) => ({ data: s.data, loading: false, error: msg }));
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
