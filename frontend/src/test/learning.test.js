import { describe, expect, it } from 'vitest'
import {
  activityGrid, categoryTrend, filterByRange, repeatedCategories, summarizeFindings,
} from '../lib/learning'

let nextIssueId = 1
const finding = (category, severity = 'low', extra = {}) => ({ id: nextIssueId++, category, severity, ...extra })
const saved = (id, createdAt, issues, status = 'completed') => ({
  id, created_at: createdAt, review_status: status, programming_language: 'python', issues,
})

describe('learning statistics', () => {
  it('counts findings per category and normalises category names', () => {
    const summary = summarizeFindings([
      saved(1, '2026-10-01T12:00:00', [finding('Input Validation', 'high'), finding('security')]),
      saved(2, '2026-10-02T12:00:00', [finding('input_validation'), finding('input_validation')]),
      saved(3, '2026-10-03T12:00:00', [], 'failed'),
    ])

    expect(summary).toMatchObject({ reviewCount: 3, completedCount: 2, issueCount: 4, highCount: 1 })
    expect(summary.categories).toEqual([
      { category: 'input_validation', count: 3, reviewCount: 2 },
      { category: 'security', count: 1, reviewCount: 1 },
    ])
  })

  it('only treats a category as repeated across different reviews', () => {
    const sameReview = repeatedCategories([
      saved(1, '2026-10-01T12:00:00', [finding('security'), finding('security')]),
    ])
    expect(sameReview).toEqual([])

    const repeated = repeatedCategories([
      saved(1, '2026-10-01T12:00:00', [finding('security', 'high', { suggested_fix: 'Old fix' })]),
      saved(2, '2026-10-05T12:00:00', [finding('security', 'low', { suggested_fix: null }), finding('logic')]),
    ])
    expect(repeated).toHaveLength(1)
    expect(repeated[0].category).toBe('security')
    expect(repeated[0].findingCount).toBe(2)
    expect(repeated[0].reviews.map((item) => item.id)).toEqual([2, 1])
    // Prefers the newest finding that has a suggested fix.
    expect(repeated[0].example.reviewId).toBe(1)
  })

  it('filters to the last 30 days', () => {
    const now = new Date('2026-10-27T12:00:00Z')
    const reviews = [saved(1, '2026-09-01T12:00:00', []), saved(2, '2026-10-20T12:00:00', [])]
    expect(filterByRange(reviews, '30d', now).map((item) => item.id)).toEqual([2])
    expect(filterByRange(reviews, 'all', now)).toHaveLength(2)
  })

  it('builds per-review category counts, oldest first, from completed reviews', () => {
    const trend = categoryTrend([
      saved(1, '2026-10-01T12:00:00', [finding('testing'), finding('testing')]),
      saved(2, '2026-10-02T12:00:00', [], 'failed'),
      saved(3, '2026-10-03T12:00:00', [finding('testing'), finding('logic')]),
    ], ['testing', 'logic'])

    expect(trend.reviews.map((item) => item.id)).toEqual([1, 3])
    expect(trend.series).toEqual([
      { category: 'testing', counts: [2, 1] },
      { category: 'logic', counts: [0, 1] },
    ])
  })

  it('counts reviews per day inside a 12-week grid', () => {
    const now = new Date(2026, 9, 27, 12)
    const grid = activityGrid([
      saved(1, '2026-10-27T12:00:00', []),
      saved(2, '2026-10-27T12:00:00', []),
      saved(3, '2026-10-20T12:00:00', []),
      saved(4, '2025-01-01T12:00:00', []),
    ], 12, now)

    expect(grid.columns).toHaveLength(12)
    expect(grid.columns.every((column) => column.length === 7)).toBe(true)
    expect(grid.total).toBe(3)
    expect(grid.max).toBe(2)
    expect(grid.columns.flat().some((cell) => cell.future)).toBe(true)
  })
})
