# Frontend UI Redesign — Approved Plan

Approved at Gate 1 on 2026-10-27. Visual reference: `MergeMind Redesign.pdf`
(Home, New Review, Review Results, Review History, Learning).
Branch: `feature/ui-redesign` from `main` @ `9f9f162`.

## Decisions

- Dependencies: `react-router-dom`, `highlight.js` (core + the 5 supported
  languages); dev: Vitest + Testing Library.
- Backend: add `medium_severity_count` / `low_severity_count` to the History
  summary only, with tests. No schema or Supabase changes.
- Learning page: real data only. Label category statistics accurately: a
  repeated category isn't proof of an identical mistake or of improvement.
  Show coverage so partial data isn't presented as all-time.
- No fake features: unsupported PDF elements are omitted or marked
  "Coming soon".

## task_list

1. Design tokens and base styles (dark surfaces, lime accent, typography).
2. App shell: router, sidebar, mobile menu, API status.
3. Shared UI: score ring, stat card, badges, severity bar, code block,
   code editor, empty state, "Coming soon".
4. History page, keeping every Stage 6 behaviour; backend severity split.
5. Review Results page with Stage 7 confidence and Stage 8 merge risk.
6. New Review page with the same request payload as before; file upload
   stays in the browser.
7. Home dashboard from real stats and recent reviews.
8. Learning page from saved reviews, with honest labels.
9. Vitest suites: History, results/scores, navigation, learning, pages.
10. Docs: PROJECT_PLAN (Stage 7/8 as built, roadmap conflicts flagged),
    review summary.
