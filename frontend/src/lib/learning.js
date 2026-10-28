// Learning-profile statistics derived from saved reviews (GET /code-reviews/).
// Everything here is a count of what the AI review reported. Nothing tracks
// whether a finding was fixed (that arrives with Stage 9 feedback).
import { normalizeCategory } from '../constants/categories'
import { parseApiDate } from './format'

const DAY_MS = 24 * 60 * 60 * 1000

function timeOf(review) {
  return parseApiDate(review.created_at)?.getTime() ?? 0
}

function newestFirst(a, b) {
  return timeOf(b) - timeOf(a) || b.id - a.id
}

export function filterByRange(reviews, range, now = new Date()) {
  if (range !== '30d') return reviews
  const cutoff = now.getTime() - 30 * DAY_MS
  return reviews.filter((review) => timeOf(review) >= cutoff)
}

export function summarizeFindings(reviews) {
  const categories = new Map()
  let issueCount = 0
  let highCount = 0
  let completedCount = 0

  for (const review of reviews) {
    if (review.review_status === 'completed') completedCount += 1
    for (const issue of review.issues || []) {
      issueCount += 1
      if (String(issue.severity).toLowerCase() === 'high') highCount += 1
      const key = normalizeCategory(issue.category)
      const entry = categories.get(key) || { category: key, count: 0, reviewIds: new Set() }
      entry.count += 1
      entry.reviewIds.add(review.id)
      categories.set(key, entry)
    }
  }

  const list = [...categories.values()]
    .map(({ category, count, reviewIds }) => ({ category, count, reviewCount: reviewIds.size }))
    .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category))

  return { reviewCount: reviews.length, completedCount, issueCount, highCount, categories: list }
}

// Categories that were flagged in at least `minReviews` different reviews.
// This shows a recurring *category*, not that the findings are the same mistake.
export function repeatedCategories(reviews, minReviews = 2) {
  const byCategory = new Map()

  for (const review of [...reviews].sort(newestFirst)) {
    for (const issue of review.issues || []) {
      const key = normalizeCategory(issue.category)
      const entry = byCategory.get(key) || {
        category: key, findingCount: 0, reviews: [], example: null, exampleWithFix: null,
      }
      entry.findingCount += 1
      if (!entry.reviews.some((item) => item.id === review.id)) {
        entry.reviews.push({ id: review.id, created_at: review.created_at })
      }
      // Reviews are visited newest first, so the first match is the most recent.
      if (!entry.example) entry.example = { issue, reviewId: review.id }
      if (!entry.exampleWithFix && issue.suggested_fix) entry.exampleWithFix = { issue, reviewId: review.id }
      byCategory.set(key, entry)
    }
  }

  return [...byCategory.values()]
    .filter((entry) => entry.reviews.length >= minReviews)
    .map(({ exampleWithFix, example, ...entry }) => ({ ...entry, example: exampleWithFix || example }))
    .sort((a, b) => b.reviews.length - a.reviews.length || b.findingCount - a.findingCount)
}

// Findings per category in the most recent completed reviews, oldest first.
export function categoryTrend(reviews, categories, limit = 6) {
  const recent = reviews
    .filter((review) => review.review_status === 'completed')
    .sort(newestFirst)
    .slice(0, limit)
    .reverse()

  const series = categories.map((category) => ({
    category,
    counts: recent.map((review) =>
      (review.issues || []).filter((issue) => normalizeCategory(issue.category) === category).length,
    ),
  }))

  return { reviews: recent.map(({ id, created_at }) => ({ id, created_at })), series }
}

function dateKey(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

// Reviews submitted per local calendar day, as `weeks` columns of Mon..Sun.
export function activityGrid(reviews, weeks = 12, now = new Date()) {
  const counts = new Map()
  for (const review of reviews) {
    const date = parseApiDate(review.created_at)
    if (!date) continue
    const key = dateKey(date)
    counts.set(key, (counts.get(key) || 0) + 1)
  }

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const mondayOffset = (today.getDay() + 6) % 7
  const start = new Date(today)
  start.setDate(today.getDate() - mondayOffset - (weeks - 1) * 7)

  const columns = []
  let total = 0
  let max = 0
  for (let week = 0; week < weeks; week += 1) {
    const column = []
    for (let day = 0; day < 7; day += 1) {
      const date = new Date(start)
      date.setDate(start.getDate() + week * 7 + day)
      const future = date > today
      const count = future ? 0 : counts.get(dateKey(date)) || 0
      total += count
      max = Math.max(max, count)
      column.push({ key: dateKey(date), date, count, future })
    }
    columns.push(column)
  }

  return { columns, total, max }
}
