import { useEffect, useState } from "react";
import { apiClient } from "@/services/api-client";

// GET
export function useGetApi<T>(url: string, skip = false) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (skip) return;

    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.get<T>(url);
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [url, skip]);

  const refetch = async () => {
    const res = await apiClient.get<T>(url);
    setData(res);
    return res;
  };

  return { data, loading, error, refetch, setData };
}
// POST
export function usePostApi<TResponse, TBody = unknown>(url: string) {
  const [data, setData] = useState<TResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const post = async (body: TBody) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<TResponse>(url, body);
      setData(res);
      return res;
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setData(null);
    setError(null);
  };

  return { data, loading, error, post, reset };
}