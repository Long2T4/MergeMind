import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// jsdom doesn't implement scrolling; AppLayout scrolls to the top on navigation.
window.scrollTo = vi.fn()
Element.prototype.scrollIntoView = vi.fn()
