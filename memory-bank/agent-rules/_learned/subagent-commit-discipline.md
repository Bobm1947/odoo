---
name: Sub-Agent Commit Discipline
globs: ["**/*"]
topics: ["build-orchestrator", "documentation-agent", "git"]
priority: low
auto_generated: true
derived_from: [customer-credit-limit-warning]
evidence_count: 1
last_validated: 2026-09-19
---

- When the build orchestrator's protocol is a single end-of-phase commit,
  sub-agents (especially the Documentation Agent) should stage their
  changes for that commit rather than creating their own separate mid-phase
  commit — and should complete every requested task-file Execution State
  update before handing back, not leave partial updates for the orchestrator
  to finish.
- Evidence: on `customer-credit-limit-warning`, the Documentation Agent
  committed `techContext.md` changes separately in all 3 phases
  (`0876738d`, `c674ad3f`, `5aa4e8f6`) instead of leaving them for the
  phase commit, and skipped a requested task-file Execution State update in
  Phase 1 that the orchestrator had to complete itself. Low severity (git
  history stayed legible), but a repeated pattern across all 3 phases.
