import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// jsdom doesn't implement scrolling; AppLayout scrolls to the top on navigation.
window.scrollTo = vi.fn()
Element.prototype.scrollIntoView = vi.fn()

// Stage 12: API calls go through the Supabase-authenticated client. Tests stub
// `fetch` themselves, so stand in a signed-in client that passes requests
// straight through. Tests of auth.js itself use vi.importActual.
// /account calls resolve to empty data shaped like the backend's responses.
// Plain functions, not vi.fn(), so tests' vi.resetAllMocks() doesn't clear them.
vi.mock('../stage12/auth', () => {
  const emptyLearning = {
    total_reviews: 0, total_issues: 0, fixed_issues: 0, false_positives: 0, pull_request_reviews: 0,
    statuses: { open: 0, fixed: 0, dismissed: 0, false_positive: 0 },
    categories: {}, repeated_categories: [], monthly_categories: [], trend_note: '',
  }
  return {
    supabase: null,
    API_BASE: 'http://localhost:8000',
    authFetch: (url, options) => fetch(url, options),
    accountRequest: async (path) => (path === '/learning' ? emptyLearning : []),
  }
})
