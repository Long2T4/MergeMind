import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY

// Do not put the service_role or database password in Vite variables.
export const supabase = url && key ? createClient(url, key) : null
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function authFetch(url, options = {}) {
  if (!supabase) throw new Error('Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY')
  const { data: { session }, error } = await supabase.auth.getSession()
  if (error || !session?.access_token) throw new Error('Please sign in first')
  const headers = new Headers(options.headers || {})
  headers.set('Authorization', `Bearer ${session.access_token}`)
  return fetch(url, { ...options, headers })
}

export async function accountRequest(path, options = {}) {
  const response = await authFetch(`${API_BASE}/account${path}`, options)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { message = (await response.json()).detail || message } catch { /* not JSON */ }
    const error = new Error(typeof message === 'string' ? message : JSON.stringify(message))
    error.status = response.status
    throw error
  }
  return response.json()
}
