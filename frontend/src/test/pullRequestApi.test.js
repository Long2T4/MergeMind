import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPullRequestReview } from '../services/api'

const URL = 'https://github.com/octo-org/sample-repo/pull/7'

afterEach(() => vi.unstubAllGlobals())

function reply(status, body) {
  return vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body })
}

describe('createPullRequestReview', () => {
  it('posts the pull request URL using the backend contract', async () => {
    const fetch = reply(202, { id: 42 })
    vi.stubGlobal('fetch', fetch)
    expect(await createPullRequestReview({ projectId: 1, prUrl: URL, sourceRoot: 'backend' })).toEqual({ id: 42 })
    const [address, options] = fetch.mock.calls[0]
    expect(address).toMatch(/\/pull-request-reviews\/$/)
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ project_id: 1, pr_url: URL, source_root: 'backend' })
  })

  it.each([
    [422, 'This pull request has 31 changed files.'],
    [404, 'Pull request not found or not public.'],
    [503, "GitHub's rate limit was reached. Try again in 60 seconds."],
    [409, 'This pull request is already being reviewed.'],
    [429, 'Too many pull request reviews are running (at most 3).'],
  ])('shows the server explanation for %i responses', async (status, detail) => {
    vi.stubGlobal('fetch', reply(status, { detail }))
    await expect(createPullRequestReview({ projectId: 1, prUrl: URL }))
      .rejects.toMatchObject({ message: detail, validation: true })
  })

  it('uses a generic message when the server gives no explanation', async () => {
    vi.stubGlobal('fetch', reply(500, null))
    await expect(createPullRequestReview({ projectId: 1, prUrl: URL }))
      .rejects.toMatchObject({ message: expect.stringMatching(/status 500/) })
  })
})
