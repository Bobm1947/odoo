# Archive: Customer Credit Limit Warning

## Metadata
- Task: customer-credit-limit-warning
- Complexity: Level 3
- Started: 2026-09-18
- Completed: 2026-09-19
- Roadmap Link: customer-credit-limit-warning

## Summary

Added a second ("approaching", >=80% of credit limit) severity tier to the Sale
Order form's customer credit-limit warning banner, alongside the existing
("over limit", >100%) tier that Odoo core already ships. The banner shows the
customer's credit limit, current outstanding receivables, and how much the
in-progress order would add — styled yellow when approaching, red when over,
and fully absent when there is no credit exposure to warn about.

The Spec Writer's discovery that Odoo core (`addons/sale/models/sale_order.py`,
shared with `addons/account`'s Invoicing UI via `_build_credit_warning_message()`)
already implements ~70% of this feature in strictly binary form reframed the task
from "build a banner" to "extend a shared core mechanism safely" — the decisive
input to the eventual architecture.

## Requirements

### Original Requirements
- Computed banner on the Sale Order form: yellow at >=80% of credit limit, red
  over 100%
- Message includes credit limit, current outstanding receivables, and this
  order's contribution
- No banner when the customer has no credit limit set or is well within limit

### Success Criteria
- [✓] AC-ENTRY-1 — banner discoverable with zero extra navigation
- [✓] AC-HAPPY-1 — red/over-limit banner with all 3 data points
- [✓] AC-HAPPY-2 — yellow/approaching banner at the 80% threshold
- [✓] AC-HAPPY-3 — banner fully absent (not just hidden) when nothing to warn about
- [✓] AC-ERROR-1 — banner stays visible to Sales users without Accounting-group access
- [✓] AC-LIVE-1 — live threshold walk (none→approaching→over→none), no save required
- [✓] AC-NAV-1 — never blocks order confirmation; banner retires after confirm
- [✓] AC-A11Y-1 — tiers distinguishable by text/role, not color alone

## Implementation

### Approach

Delivered as a new, self-contained addon (`addons/sale_credit_limit_warning/`)
that `_inherit`-extends `sale.order` and its form view — Odoo's own
extensibility mechanism (systemPatterns.md's "Inheritance over modification"
Guiding Principle) — rather than editing `addons/sale/` or `addons/account/`
directly, or modifying the shared `_build_credit_warning_message()` method that
Invoicing also depends on. The upstream-merge-safety invariant
(`git diff --stat -- addons/sale addons/account` empty) held across all 3
phases.

### Key Components

1. **Model layer** (`addons/sale_credit_limit_warning/models/sale_order.py`)
   - Purpose: two non-stored computed fields (`credit_warning_level`,
     `credit_limit_detail`) driven by one shared figures resolver, so severity
     and message text can never disagree
   - Chain: `_get_credit_warning_ratio()` → `_get_credit_limit_figures()` →
     `_build_credit_limit_detail()` → `_compute_credit_limit_warning_tier()`
   - Threshold externalized via `ir.config_parameter` (fail-soft, default 0.8)
   - Fixes two real core bugs (discarded `.with_company()` return; missing
     `'state'` in `@api.depends`) scoped entirely inside this addon's own
     resolver

2. **View layer** (`addons/sale_credit_limit_warning/views/sale_order_views.xml`)
   - Purpose: `ir.ui.view` inheriting `sale.view_order_form`; re-targets core's
     existing `partner_credit_warning` banner div (via `xpath`, never
     `position="replace"`) to the "over" tier restyled `alert-danger`, and
     inserts a sibling `alert-warning` div for "approaching"
   - `role="status"` (polite) on the approaching tier vs `role="alert"`
     (assertive) on the over tier — per the User Journey design's AC-A11Y-1,
     confirmed after a build-phase human review corrected an intermediate
     regression (see Lessons Learned)

3. **Tests** (`addons/sale_credit_limit_warning/tests/`)
   - `test_two_tier_credit_limit.py` — 9 tests, tier-boundary matrix + parity
     tripwire against core's own message string
   - `test_view_and_access.py` — 3 tests, alert classes per tier + AC-ERROR-1
     access-parity regression guard
   - `test_e2e_live_flow.py` — 3 tests, full live threshold walk (AC-LIVE-1),
     confirm-never-blocked (AC-NAV-1), and a11y legibility (AC-A11Y-1)

### Design Decisions

Architecture, UI/UX, and User Journey creative phases ran in parallel.
Architecture evaluated 5 options (extend shared method / sale-only compute /
new addon wrapping the compute / override the compute / new addon with
additive fields) and chose the additive-fields-in-a-new-addon option. UI/UX
chose full two-tier Bootstrap color mapping (`alert-warning`/`alert-danger`),
precedented by `addons/account_edi/views/account_move_views.xml`. User Journey
chose a passive, zero-new-interaction banner evolution, and derived the
`role="status"`/`role="alert"` a11y split from first principles.

Reference: `memory-bank/creative/customer-credit-limit-warning-two-tier-warning-architecture.md`,
`memory-bank/creative/customer-credit-limit-warning-banner-uiux.md`,
`memory-bank/creative/customer-credit-limit-warning-banner-user-journey.md`

## Testing
- New tests: 15 (9 model, 3 view/access, 3 E2E)
- Core regression: 221/221 (`sale` suite, Phases 1-2), 7/7
  (`TestSaleOrderCreditLimit`, Phase 3) — zero regressions
- flake8: clean (all phases)
- All tests passing: ✅

## Files Changed
- `addons/sale_credit_limit_warning/__init__.py` — addon init
- `addons/sale_credit_limit_warning/__manifest__.py` — manifest (depends: `sale`)
- `addons/sale_credit_limit_warning/data/ir_config_parameter.xml` — threshold default
- `addons/sale_credit_limit_warning/models/__init__.py`, `models/sale_order.py` — two-tier compute logic
- `addons/sale_credit_limit_warning/views/sale_order_views.xml` — banner view inheritance
- `addons/sale_credit_limit_warning/tests/__init__.py`, `test_two_tier_credit_limit.py`, `test_view_and_access.py`, `test_e2e_live_flow.py` — test suite
- `memory-bank/techContext.md` — new addon reference (Phase 1-3)

## Lessons Learned

Three independently-authored creative documents each made a defensible call on
a detail the others didn't fully own: the UI/UX doc specified `role="alert"`
on both severity tiers, while the User Journey doc's explicitly-reasoned
AC-A11Y-1 called for `role="status"` on the approaching tier (to avoid
interrupting screen-reader speech on every order-line edit). The build
orchestrator's Phase 2 Step 8 code review found the deviation and "fixed" the
code toward the UI/UX doc's version — silently regressing a correct,
well-reasoned accessibility decision. It was caught only because a human
reviewing the build-phase gate noticed the discrepancy and asked; the fix
(commit `d35a7329`) restored `role="status"` per the User Journey doc's
rationale and was re-verified before merging into the phase's work.

This is documented in the reflection as a **process** gap, not a one-off bug:
a code-review finding that traces to a contradiction between two creative
documents should be escalated as a decision for the human gate, not silently
auto-resolved toward whichever document the reviewer happens to check first.

Reference: `memory-bank/reflection/customer-credit-limit-warning-reflection.md`

## References
- Reflection: `memory-bank/reflection/customer-credit-limit-warning-reflection.md`
- Creative: `memory-bank/creative/customer-credit-limit-warning-two-tier-warning-architecture.md`,
  `memory-bank/creative/customer-credit-limit-warning-banner-uiux.md`,
  `memory-bank/creative/customer-credit-limit-warning-banner-user-journey.md`

## Follow-up
- Two real core bugs remain unfixed upstream in `addons/sale/models/sale_order.py`
  (discarded `.with_company()` return at lines 772-773; missing `'state'` in
  `@api.depends` at line 770) — out of scope for this fork's addon but worth a
  tracked upstream issue/PR against Odoo.
- Invoicing (`account.move`) never received the equivalent two-tier treatment —
  explicitly out of scope; a sibling addon or promoted mixin is sketched in the
  Architecture doc if picked up later.
- Ecosystem-improvement suggestions from the reflection (cross-doc consistency
  check after creative fan-out; Step 8 escalate-don't-resolve on doc-conflict
  findings) are process fixes for `bmb:creative`/build-orchestrator methodology,
  not memory-bank content — flagged for whoever maintains those files.
