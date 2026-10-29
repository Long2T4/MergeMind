# Project-aware context collector

Scope: the context-collection part of Akhil's originally assigned Stage 9
(Project-Aware Review). The existing roadmap uses conflicting stage names;
this task does not implement developer feedback or renumber the roadmap.

1. Add a provider-independent backend service accepting a reviewed path,
   submitted code and a mapping of supplied project paths to text.
2. Resolve direct Python imports (including relative imports and a configured
   source root) and local static JavaScript/TypeScript imports, exports and
   CommonJS requires. Exclude the reviewed file and unrelated files.
3. Enforce repository-relative paths and configurable file/character budgets.
   Report unresolved local imports and files omitted by the budget without
   reading the filesystem, executing source code or fetching remote content.
4. Add meaningful tests for import resolution, bounds, invalid inputs and
   incomplete source code. Run the existing backend regression suite.
5. Document a runnable example, supported syntax and remaining integration
   work; review the diff and record verified test results before committing.

AI/API/UI wiring and GitHub repository retrieval are subsequent work. This
collector is callable and tested independently; the application does not yet
send its output to the AI provider.
