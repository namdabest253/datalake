/**
 * Tiny "useAsync" hook. Avoids pulling react-query in for five fetches.
 *
 * Returns `{ data, loading, error }`. The fetcher closure is invoked once on
 * mount and re-invoked whenever any value in `deps` changes (same semantics
 * as React's stock `useEffect` dependency list).
 */

import { useEffect, useState } from "react";

export type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err);
          setState({ data: null, loading: false, error: msg });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
