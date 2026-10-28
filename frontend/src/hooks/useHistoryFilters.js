import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

// Stage 6 History filters live in the URL (?q=&language=&status=&page=), so
// they survive opening a review and coming back, a reload, or a shared link.
export function readHistoryFilters(params) {
  const page = Number.parseInt(params.get('page') || '1', 10)
  return {
    search: params.get('q') || '',
    language: params.get('language') || '',
    status: params.get('status') || '',
    page: Number.isFinite(page) && page > 1 ? page - 1 : 0,
  }
}

export function historySearchString(filters) {
  const params = new URLSearchParams()
  if (filters.search) params.set('q', filters.search)
  if (filters.language) params.set('language', filters.language)
  if (filters.status) params.set('status', filters.status)
  if (filters.page > 0) params.set('page', String(filters.page + 1))
  const text = params.toString()
  return text ? `?${text}` : ''
}

export function useHistoryFilters() {
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => readHistoryFilters(params), [params])

  const setFilters = useCallback((updater) => {
    setParams((previous) => {
      const current = readHistoryFilters(previous)
      const next = typeof updater === 'function' ? updater(current) : updater
      return new URLSearchParams(historySearchString(next))
    }, { replace: true })
  }, [setParams])

  return [filters, setFilters]
}
