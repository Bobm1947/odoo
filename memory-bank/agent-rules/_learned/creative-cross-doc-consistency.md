---
name: Creative Cross-Document Consistency
globs: ["memory-bank/creative/*.md"]
topics: ["creative-phase", "consistency"]
priority: low
auto_generated: true
derived_from: [customer-credit-limit-warning]
evidence_count: 1
last_validated: 2026-09-19
---

- Before marking a Level 3-4 creative phase DECIDED, check sibling creative
  documents for the same task for conflicting pinned values on shared
  attributes (ARIA roles, CSS classes, field names, thresholds) — reconcile or
  explicitly flag the discrepancy in your own doc rather than silently
  asserting your own value.
- Evidence: on `customer-credit-limit-warning`, the UI/UX doc specified
  `role="alert"` on both severity tiers of a banner while the User Journey
  doc's explicitly-reasoned AC-A11Y-1 called for `role="status"` on one tier
  (to avoid interrupting screen-reader speech on every edit). Neither doc
  showed awareness of the other's conflicting claim.
