# Frontend UI Redesign — Review Summary

**What was implemented**: The React frontend was rebuilt to match
`MergeMind Redesign.pdf`: a dark theme, lime accent, a persistent sidebar and
five routed pages (Home, New Review, Review Results, History, Learning), plus
a read-only Projects page. Plan: [ui-redesign-plan](../plans/ui-redesign-plan.md).

- **Added**: `react-router-dom` and `highlight.js` (5 grammars); Vitest and
  Testing Library as dev-only dependencies.
- **Only backend change**: `medium_severity_count` / `low_severity_count`
  added to the History summary. No schema change.
- **Preserved**: everything from Stages 3–8, including the submission
  payload, every Stage 6 behaviour (filters now persist in the URL), and the
  Stage 7 confidence and Stage 8 risk text.
- **Not implemented** (omitted or marked "Coming soon"): GitHub,
  Semgrep/Bandit/ESLint, review depth/focus, feedback actions, fix rates,
  XP/levels, streaks and lessons.

**Tests run**:

- `pytest backend/tests`: 21 passed (one new severity-split test).
- `npm test` (Vitest): 48 passed across 6 files. They cover History,
  results, scores, navigation, learning maths and pages.
- `vite build` succeeds: 89.8 KB JS gzipped, up from 51 KB.
- Browser QA against a throwaway SQLite backend (never Supabase), at 1440,
  1024 and 390 px:
  - all five pages compared with the PDF;
  - real submit → failed state → retry flow;
  - the History filter, open and back flow;
  - no horizontal overflow and no console errors.

**Review findings**:

- **`security-reviewer`**: no CRITICAL, HIGH or MEDIUM. Its one LOW was
  fixed: the back link now only follows in-app router-state paths. Both
  `dangerouslySetInnerHTML` sinks (highlight.js output) were confirmed
  escaped.
- **`react-reviewer`**: no CRITICAL or HIGH. All seven MEDIUMs were fixed,
  with regression tests:
  - the search box drifted from the URL on external changes;
  - hash links dropped the back target;
  - a retry prefill carried over into a fresh New Review;
  - navigation could fire after the user left mid-submit;
  - inactive tabs had dangling `aria-controls`;
  - focus wasn't moved on route change;
  - a missing `issues` array could crash the page.
- Several LOWs were also fixed: the hidden file input, a NaN risk score,
  Escape to close the menu, a skipped heading level and editor input lag.

**Unresolved issues**:

- No authentication (app-wide; pre-existing).
- Learning stats come from the unpaginated `GET /code-reviews/`, which won't
  scale indefinitely. The page shows coverage when it loads fewer reviews
  than exist.
- The History table scrolls sideways inside its card at tablet widths.
- The roadmap conflicts are flagged in `docs/PROJECT_PLAN.md`.

**Lessons for future work**: CSS import order and `.sr-only` overflow; see
[growth-log 2026-10-27](../growth-log/2026-10-27.md).
