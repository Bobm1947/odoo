---
name: Build Review Escalation on Cross-Doc Conflicts
globs: ["**/*"]
topics: ["build-orchestrator", "code-review", "creative-phase"]
priority: low
auto_generated: true
derived_from: [customer-credit-limit-warning]
evidence_count: 1
last_validated: 2026-09-19
---

- When a Step 8 code-review finding traces to a contradiction between two
  creative documents (not a single implementation drift from one document),
  escalate it as a decision for the human gate instead of silently picking one
  document's version to "fix" the code toward. Neither creative lane is
  strictly senior to the other on a shared micro-decision (e.g., UI/UX owns
  Bootstrap classes/copy, User Journey owns end-to-end interaction/a11y flow),
  so silent auto-resolution is structurally unsound regardless of which side
  gets picked.
- Evidence: on `customer-credit-limit-warning` Phase 2, the orchestrator
  silently reverted a correct, explicitly-reasoned accessibility decision
  (`role="status"`) back to a conflicting creative doc's value
  (`role="alert"`), undoing the User Journey doc's AC-A11Y-1. Caught only by
  human review at the phase gate, not by the orchestrator's own process.
