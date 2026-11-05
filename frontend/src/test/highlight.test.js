import { describe, expect, it } from 'vitest'
import { highlightCode, resolveLanguage } from '../lib/highlight'

describe('syntax highlighting', () => {
  it('highlights TypeScript, including type annotations', () => {
    const html = highlightCode('interface User { name: string }\nconst count: number = 1', 'typescript')
    expect(html).toContain('hljs-keyword')
    expect(html).toContain('interface')
  })

  it('maps TypeScript fence hints to the TypeScript grammar', () => {
    expect(resolveLanguage('ts')).toBe('typescript')
    expect(resolveLanguage('tsx')).toBe('typescript')
    expect(resolveLanguage('TypeScript')).toBe('typescript')
  })

  it('still escapes unsupported languages instead of highlighting them', () => {
    expect(resolveLanguage('other')).toBeNull()
    expect(highlightCode('<b>x</b>', 'other')).toBe('&lt;b&gt;x&lt;/b&gt;')
  })
})
