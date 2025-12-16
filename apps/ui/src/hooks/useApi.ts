import { useState, useEffect } from 'react'
import { apiClient } from '@/services/api-client'

export function useApi<T>(endpoint: string, skip: boolean = false) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (skip) return

    const fetchData = async () => {
      try {
        setLoading(true)
        const result = await apiClient.get<T>(endpoint)
        setData(result)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'))
        setData(null)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [endpoint, skip])

  return { data, loading, error }
}
