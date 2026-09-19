---
version: next
status: completed
priority: medium
complexity: 3
linked_tasks: [customer-credit-limit-warning]
created: 2026-09-18
---

# Customer Credit Limit Warning

Add a customer credit limit warning to the Sale Order form. The warning is a
computed text message that appears as a banner when a customer is
approaching or exceeding their credit limit. Yellow at 80% of limit, red
over 100%. The message includes the credit limit, current outstanding
receivables, and how much this order would add. Empty (no banner) when the
customer has no credit limit set or is well within limit.

**Complexity rationale**: Requires a design decision on the banner's
threshold/color/message composition (UI/UX) and touches multiple
components — `sale.order` (new computed field + form view banner) and
`res.partner` (existing `credit` / `credit_limit` fields). Not system-wide,
so Level 3 rather than Level 4.
