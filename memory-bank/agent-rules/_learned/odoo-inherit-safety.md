---
name: Odoo Inherit Safety (this fork)
globs: ["addons/*/models/*.py", "addons/*/views/*.xml"]
topics: ["odoo", "upstream-merge-safety"]
priority: low
auto_generated: true
derived_from: [customer-credit-limit-warning]
evidence_count: 1
last_validated: 2026-09-19
---

- When extending a core Odoo compute or view that another module's
  `post_install`-tagged tests assert exact-string or `Form()`-field-presence
  contracts against, re-target via `xpath` onto the existing field node —
  never `position="replace"` on it, and never override the original compute
  method in place. This keeps upstream regression suites green with zero
  edits to files the task doesn't own.
- Evidence: `customer-credit-limit-warning` re-targeted core's
  `partner_credit_warning` banner div via `xpath` rather than replacing it,
  preserving core's `test_credit_limit_access` `Form()`-driven test contract
  while adding a new severity tier from a separate addon.
