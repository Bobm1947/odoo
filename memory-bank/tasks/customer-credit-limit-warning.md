---
slug: customer-credit-limit-warning
feature: customer-credit-limit-warning
status: CREATIVE_COMPLETE
---

# customer-credit-limit-warning: Customer Credit Limit Warning

**Complexity**: Level 3 (inherited from customer-credit-limit-warning)
**Status**: CREATIVE_COMPLETE
**Roadmap**: customer-credit-limit-warning
**Branch**: feature/customer-credit-limit-warning
**Worktree**: N/A

## Task Description

Add a customer credit limit warning to the Sale Order form. The warning is a
computed text message that appears as a banner when a customer is
approaching or exceeding their credit limit. Yellow at 80% of limit, red
over 100%. The message includes the credit limit, current outstanding
receivables, and how much this order would add. Empty (no banner) when the
customer has no credit limit set or is well within limit.

## Specification

**Feature Type**: End-User Feature
**Primary Persona**: Sales Rep (productBrief.md § Key Personas — "Uses CRM/Sales apps... issue quotations"; productBrief has no Banyan-specific persona detail beyond role name for this brownfield fork)
**Creative Exploration Needed**: Yes — see "Creative Exploration Needed" below. This task should route through `/bmb:creative` before build (consistent with its Level 3 classification).

> **CRITICAL FINDING — Odoo core already implements ~70% of this feature.** `addons/sale/models/sale_order.py` already has a computed `partner_credit_warning` field, rendered in a banner in the exact location this task wants, built from the exact three data points this task asks for. It is **binary** (no banner vs. a single over-limit banner) — it has **no 80% "approaching" yellow tier**. See the full writeup under "Creative Exploration Needed" — the central open question is whether to extend this shared core mechanism or build a parallel one, and that decision changes both scope and upstream-merge risk.

### Invocation Method
- **Location**: Sale Order form (`addons/sale/views/sale_order_views.xml`), the banner region immediately below `<header>` and above the order-lines notebook — the exact slot the existing `partner_credit_warning` alert already occupies (lines 301-305), sibling to the "archived products" and "duplicated order" alert divs that follow it (lines 306-314+).
- **Element**: An `<div class="alert alert-warning" role="alert" invisible="partner_credit_warning == ''">` wrapping `<field name="partner_credit_warning"/>` — this exact div already exists; the task is to extend or replace its underlying compute so it has two visually distinct severity states instead of one.
- **Visibility**: Conditional — banner is entirely absent from the DOM (not just visually hidden) when the underlying text is empty, via the existing `invisible="... == ''"` pattern. Today the field is non-empty only when the customer is already over limit; this task adds a second non-empty state at >=80%.
- **Navigation**: None required — the banner sits on the primary Sale Order form, always in view above the order lines, visible the moment the form renders or the relevant data changes. No clicks, tabs, or settings navigation needed to discover it.
- **Confidence**: HIGH on location/element (exact existing pattern found in the codebase, cited above) / LOW on implementation strategy (extend existing shared compute vs. build a parallel one — flagged for Creative Phase).

### Success Criteria
- **User sees**: Banner text containing the partner's credit limit, current outstanding receivables (posted-but-unpaid `credit` + confirmed-but-not-yet-invoiced `credit_to_invoice`), and how much this order would add — styled as "approaching" (yellow) when the projected total is >=80% and <=100% of the credit limit, and "over limit" (red, or the project's chosen over-limit treatment — see Creative Exploration) when it exceeds 100%. No banner at all when the customer has no `credit_limit` set, the company-level credit-limit feature is disabled, or the projected total is comfortably under 80%.
- **Verifiable at**: The Sale Order form itself — the banner area between `<header>` and the order lines (same place the existing binary warning already renders today).
- **Data persisted**: None. `partner_credit_warning` is a non-stored compute (`fields.Text(compute='_compute_partner_credit_warning')`, no `store=True` — `addons/sale/models/sale_order.py:299-300`); it is recomputed on the fly from `res.partner.credit`, `credit_to_invoice`, `credit_limit`, and the in-progress order's own total. No new DB columns are required unless Creative Phase decides a new field/severity attribute is warranted.
- **Observable within**: Immediate — recomputes synchronously via the standard Odoo compute/onchange round-trip whenever `partner_id`, `order_line`, or pricing changes on the form; no save required (mirrors today's behavior, confirmed by the existing core test `test_credit_limit_multicurrency` in `addons/sale/tests/test_credit_limit.py:151-214`, which asserts the warning updates live as order lines are edited).

### Acceptance Criteria

#### AC-ENTRY-1: Sales user sees the credit-limit banner without any extra navigation
**Priority**: MUST
**Given** a user with the Sales app open on any Sale Order form (new quotation or existing order)
**When** the form renders
**Then** the credit-limit banner region is present at its established location — immediately below `<header>` in `addons/sale/views/sale_order_views.xml` (same position as today's `partner_credit_warning` div, lines 301-305) — requiring no extra clicks, tabs, or menu navigation to discover it

#### AC-HAPPY-1: Red/over-limit banner appears when this order would push the customer over their credit limit
**Priority**: MUST
**Given** a customer with `credit_limit` set on `res.partner` (Float, company-dependent, `addons/account/models/partner.py:524-527`) and the company setting `account_use_credit_limit` enabled (`addons/account/models/company.py:154-155`)
**When** the sum of `credit` (posted/unpaid invoices) + `credit_to_invoice` (confirmed-but-not-yet-invoiced orders) + this order's own total exceeds `credit_limit`
**Then** the banner renders in its over-limit state and its text states the partner's credit limit and the total amount due including this order — the same three data points already assembled by `account.move._build_credit_warning_message()` (`addons/account/models/account_move.py:1846-1888`), preserved or re-derived by whichever implementation approach Creative Phase selects

#### AC-HAPPY-2: Yellow "approaching limit" banner appears at the 80% threshold
**Priority**: MUST
**Given** the same preconditions as AC-HAPPY-1
**When** the projected total (`credit` + `credit_to_invoice` + this order) is >=80% and <=100% of `credit_limit` (not yet over)
**Then** the banner renders in a visually distinct "approaching limit" state, carrying the same three data points (credit limit, current outstanding receivables, this order's contribution) — exact wording and boundary rounding at 80.0% are pinned during Creative Phase

#### AC-HAPPY-3: Banner is fully absent when there is no credit exposure to warn about
**Priority**: MUST
**Given** a customer with no `credit_limit` value set (falsy, matching core's existing `if not partner_id.credit_limit` guard), OR the company setting `account_use_credit_limit` disabled, OR the projected total is comfortably under 80% of the limit
**When** the Sale Order form is viewed
**Then** no banner div renders at all (absent, not merely visually hidden) — matching the existing `invisible="partner_credit_warning == ''"` pattern

#### AC-ERROR-1: Banner remains visible to sales users without Accounting field-level access
**Priority**: MUST
**Given** a user in the Sales app who does NOT belong to `account.group_account_invoice` or `account.group_account_readonly` (the groups gating direct read access to `credit`, `credit_limit`, and `credit_to_invoice` — `addons/account/models/partner.py:518-527`)
**When** that user opens a Sale Order for a customer who is over or approaching their credit limit
**Then** the banner text is still visible to them — the compute must keep running with elevated access the way `order.sudo()` already does today (`addons/sale/models/sale_order.py:779`), even though the underlying partner fields stay inaccessible to that user directly; this mirrors the existing core test `test_credit_limit_access` (`addons/sale/tests/test_credit_limit.py:344-366`), which this feature must not regress

### Scope Boundaries
- **In scope**: Two-tier (yellow at >=80%, red/over-limit at >100%) banner logic on the Sale Order form only, sourced from `res.partner.credit`, `credit_to_invoice`, and `credit_limit`, gated by the existing `account_use_credit_limit` company setting. Message composition including all three required data points (credit limit, outstanding receivables, this order's addition). Correct empty/no-banner behavior for: no credit limit set, feature disabled, or comfortably under 80%.
- **Out of scope**: Extending the same tri-state treatment to Invoices (`account.move`) — even though `_build_credit_warning_message()` is shared with Invoicing today, this task only asks for the Sale Order form; touching Invoices is an explicit non-goal unless Creative Phase decides the extension path requires it. Blocking/preventing order confirmation — this stays a non-blocking, informational banner; no new validation/constraint. A configurable threshold setting UI — 80% is a fixed spec value per the task description, not user-configurable, unless Creative Phase says otherwise. Notifications, emails, or activities tied to credit exposure. Changing the default value of the `account_use_credit_limit` company setting.
- **Dependencies**: `res.company.account_use_credit_limit` must be enabled (Settings > Invoicing) for any banner to ever appear (existing precondition, unchanged). `res.partner.credit_limit` must be set (Accounting-group-gated field) on the customer. Existing `account`/`sale` credit machinery (`credit`, `credit_to_invoice`, `_build_credit_warning_message`) that this feature builds on top of.
- **NFR implications**: Security/field-access — `credit`, `credit_limit`, `credit_to_invoice` are gated to `account.group_account_invoice`/`account.group_account_readonly`; any new or extended compute must preserve the existing `.sudo()` elevation pattern so non-Accounting sales users keep seeing the banner text (see AC-ERROR-1). Multi-company/multi-currency — core's existing logic already handles company-currency conversion (`formatLang`, `record.company_id.currency_id`) and multi-company credit scoping (proven by `test_credit_limit_multi_company` and `test_credit_limit_multicurrency` in `addons/sale/tests/test_credit_limit.py`); any extension must not regress these paths. productBrief.md's NFR sections (Performance, Accessibility, etc.) are largely "To be determined" for this brownfield fork — no additional documented NFRs apply beyond the security/multi-company points above.

### Creative Exploration Needed

Yes. Route this task through `/bmb:creative` (architecture + UI/UX lanes) before build. Specific open questions:

1. **Extend vs. build new — the central design decision.** Odoo core (`addons/sale/models/sale_order.py:299-300,771-781` + `addons/account/models/account_move.py:1846-1888`) already implements a computed `partner_credit_warning` Text field on `sale.order`, gated by `account_use_credit_limit`, rendered in a `<div class="alert alert-warning">` immediately below `<header>` (`addons/sale/views/sale_order_views.xml:301-305`), assembling exactly the three data points this task asks for. What core lacks is the 80%/100% two-tier distinction — it is binary (nothing, or a single `alert-warning` message that only fires once the customer is already over limit). The message builder (`_build_credit_warning_message`) is **shared** between `sale.order` and `account.move` (Invoices) — modifying its signature/behavior has blast radius into the Invoicing UI, which this task does not mention. Options to weigh: (a) extend `_build_credit_warning_message` in place with a severity/threshold parameter — smaller diff, but touches shared Invoicing code and increases future upstream-merge risk; (b) add a parallel `sale.order`-only compute that reuses the same underlying partner data but composes its own two-tier message/severity independently of the invoice code path — larger diff, more cleanly scoped to this task, some logic duplication with core.
2. **Visual severity mapping.** Core's only existing tier already renders as `alert-warning` (Bootstrap yellow). If the over-limit case should now render as red, that changes the visible color for every customer/order already relying on the existing mechanism today — needs an explicit UI/UX call, e.g., approaching (80-100%) → `alert-warning` (yellow, matches core's current styling), over (>100%) → `alert-danger` (red, new).
3. **80% boundary semantics and copy.** Whether 80.0% is inclusive, how it's rounded, and the exact wording for the new "approaching" message — core's existing message templates in `_build_credit_warning_message` are phrased specifically for the over-limit case ("has reached its credit limit of...") and need a parallel "approaching" phrasing.
4. **Currency/multi-company parity and Invoicing scope creep.** Whether the multi-currency and multi-company edge cases already proven for the >100% path (`test_credit_limit_multicurrency`, `test_credit_limit_multi_company`) need equivalent coverage for the new 80% tier, and whether Invoices should eventually get the same tri-state treatment (explicitly out of scope for *this* task, but worth a documented decision since the shared method invites scope creep).

## Test Strategy

### Approach
- **Emphasis**: Integration — this project's testing convention (systemPatterns.md § Testing Patterns) favors real transactional-DB tests over the ORM (`TransactionCase`) rather than isolated unit tests with mocks. Follow the existing `addons/sale/tests/test_credit_limit.py` pattern (composes `SaleCommon`-style mixins).
- **Target test count**: ~12 across all phases (Level 3 guideline: 10-20).

### File Organization
- **New test files**: `<new-addon>/tests/__init__.py`, `<new-addon>/tests/test_credit_limit_warning.py` — the new two-tier severity logic, boundary cases, and access-rights parity. (`<new-addon>` name is finalized in the Architecture creative phase; provisionally `sale_credit_limit_warning`.)
- **Extend existing**: None — this is a new addon, so no existing test file is extended. Core's `addons/sale/tests/test_credit_limit.py` is read-only reference (do not modify a module this task doesn't own).

### What NOT to Test
- The existing binary over-limit compute and its multi-currency/multi-company correctness — already covered by core's `test_credit_limit.py` (`test_credit_limit_multicurrency`, `test_credit_limit_multi_company`); this task only needs to prove its own two-tier extension doesn't regress those paths, not re-prove them from scratch.
- Bootstrap/CSS rendering pixel-fidelity — covered by asserting the correct Bootstrap alert class (`alert-warning` / `alert-danger`) is present, not visual regression testing.

### Per-Phase Test Guidance
- Phase 1: ~6 tests — two-tier compute logic across the boundary matrix (no `credit_limit` set, feature disabled, <80%, exactly 80%, 80-100%, >100%), each asserting both the message content (credit limit, outstanding receivables, this order's contribution) and the severity value.
- Phase 2: ~3 tests — view renders the correct Bootstrap alert class per severity tier; banner is absent (not just hidden) in the no-warning case; access-rights parity for a Sales-only user without `account.group_account_invoice` (regression guard for AC-ERROR-1, mirrors core's `test_credit_limit_access`).
- Phase 3: ~3 tests — E2E: open a Sale Order, add order lines that cross first the 80% then the 100% threshold, assert the banner updates live (no save required) with correct text and severity at each step.

## Implementation Roadmap

### New Source Files (pin path + extension)
<!-- Guiding Principle (systemPatterns.md): "Inheritance over modification" — existing addon
     files (addons/sale/, addons/account/) are never edited directly; this feature is delivered
     as a new addon that extends sale.order/sale_order_views.xml via _inherit. Addon name/exact
     inheritance strategy is confirmed in the Architecture creative phase (Creative Q1); paths
     below use the provisional addon name `sale_credit_limit_warning`. -->
- [ ] `addons/sale_credit_limit_warning/__manifest__.py` — new addon manifest (depends: `sale`, `account`)
- [ ] `addons/sale_credit_limit_warning/__init__.py` — new
- [ ] `addons/sale_credit_limit_warning/models/__init__.py` — new
- [ ] `addons/sale_credit_limit_warning/models/sale_order.py` — new; `_inherit = 'sale.order'`, two-tier severity compute (extends or wraps `_compute_partner_credit_warning` per creative decision)
- [ ] `addons/sale_credit_limit_warning/views/sale_order_views.xml` — new; `_inherit` of `sale.order.view.form` (or the addons/sale form's external ID), xpath onto the existing `partner_credit_warning` banner div to add severity-conditional CSS class
- [ ] `addons/sale_credit_limit_warning/tests/__init__.py` — new
- [ ] `addons/sale_credit_limit_warning/tests/test_credit_limit_warning.py` — new (see Test Strategy)

### Phases
- [x] Phase 1: Two-tier compute logic — scaffold the new addon; extend `sale.order`'s credit-warning compute (or its severity classification) to distinguish "approaching" (>=80%, <=100%) from "over limit" (>100%) from "none"; unit/integration tests across the full boundary matrix (AC-HAPPY-1, AC-HAPPY-2, AC-HAPPY-3)
- [ ] Phase 2: Banner UI + access parity — extend the existing form-view banner div via `_inherit` to render the correct Bootstrap severity class per tier; verify the banner stays visible to Sales users without Accounting-group field access (AC-ENTRY-1, AC-ERROR-1)
- [ ] Phase 3: End-to-end flow + regression guard — E2E test walking the full entry-to-success flow (open Sale Order → add lines crossing 80% then 100% → banner updates live with correct text/severity at each step); confirm no regression in core's existing `test_credit_limit.py` suite

## Creative Phases

- [x] User Journey Design → `memory-bank/creative/customer-credit-limit-warning-banner-user-journey.md` — Decision: Option 1, Enriched Passive Two-Tier Banner (evolution in place, no new interaction). Normative threshold semantics (>=80% inclusive → yellow, >100% strict → red, exactly 100% stays yellow per trigger parity with core). `role="status"` (yellow) vs `role="alert"` (red) for a11y. Flagged core bug: discarded `with_company()` return at `sale_order.py:772`. New ACs: AC-LIVE-1, AC-NAV-1, AC-A11Y-1.
- [x] Architecture Design → `memory-bank/creative/customer-credit-limit-warning-two-tier-warning-architecture.md` — Decision: Option (c) refined — new addon `addons/sale_credit_limit_warning/`, `_inherit`-extends `sale.order` with two new non-stored fields (`credit_warning_level`, `credit_limit_detail`) computed from one shared figures dict; view re-targeted via `inherit_id`/`xpath` on the existing banner div. `addons/sale/` and `addons/account/` stay byte-identical to upstream. Core's `partner_credit_warning` field/tests untouched (avoids breaking `@tagged('post_install')` assertions in `test_credit_limit.py`). Resolves Creative Q1/Q4.
- [x] UI/UX Design → `memory-bank/creative/customer-credit-limit-warning-banner-uiux.md` — Decision: full two-tier Bootstrap color mapping (`alert-warning` approaching / `alert-danger` over), precedented by `addons/account_edi/views/account_move_views.xml:114-131`. Exact copy templates for both tiers, `float_compare`-based boundary math (not raw float comparison), icon + label redundant cues for color-independence. Resolves Creative Q2/Q3.

## Design Critique (advisory)

**CREATIVE CRITIQUE**: skipped — `unresolved:no-companion` (Codex companion glob empty on this machine; `creative-critique: codex` in projectConfig, `availability: auto` → silent fallback, no critique run this pass).

---

## Execution State

**Build Status**: RUNNING
**Current Build**: Phase 1: Two-tier compute logic (customer-credit-limit-warning)
**Build Started**: 2026-09-18
**Phase Number**: 1 of 3
**Is Multi-Phase**: YES
**Current Phase**: BUILD (Phase 1 complete, Phase 2 pending)
**Current Step**: Step 11 - Git completion
**Can Resume**: NO

**CREATIVE CRITIQUE**: skipped — unresolved:no-companion (glob=∅, no `.local/codex-cache.md`)

### Active Sub-Agents
- User Journey Design: COMPLETE
- Architecture Design: COMPLETE
- UI/UX Design: COMPLETE

### Completed Steps
- Step 6 - Finalize plan: COMPLETE
- User Journey Design: COMPLETE (2026-09-18) - Output: memory-bank/creative/customer-credit-limit-warning-banner-user-journey.md
- Architecture Design: COMPLETE (2026-09-18) - Output: memory-bank/creative/customer-credit-limit-warning-two-tier-warning-architecture.md
- UI/UX Design: COMPLETE (2026-09-18) - Output: memory-bank/creative/customer-credit-limit-warning-banner-uiux.md
- Phase 1 - Step 3 TDD Agent: COMPLETE (2026-09-18) - New addon `addons/sale_credit_limit_warning/` (model layer only): `_get_credit_warning_ratio`, `_get_credit_limit_figures`, `_build_credit_limit_detail`, `_compute_credit_limit_warning_tier` on `sale.order` (`_inherit`); 9 tests, RED confirmed then GREEN
- Phase 1 - Step 7 Integration Verification: COMPLETE (2026-09-18) - 9/9 addon tests, 221/221 core `sale` regression, flake8 clean (after orchestrator lint-formatting fixes: line length + lambda-to-def + `# noqa` on `__init__.py` imports, no logic changes), `git diff --stat -- addons/sale addons/account` empty
- Phase 1 - Step 8 Code Review: COMPLETE (2026-09-18) - APPROVED. 2 non-blocking recommendations deferred to Phase 2/3: (a) use `float_compare` instead of raw float comparison in the tier classification for robustness against non-round currency amounts; (b) add multi-currency/multi-company/`state=='sale'` test coverage for the 80% tier
- Phase 1 - Step 9 Documentation: COMPLETE (2026-09-18) - techContext.md updated with new addon reference; systemPatterns.md/productBrief.md unchanged (no new pattern, no user-facing change yet)

### Guard & Recovery Log
- Phase 1: Step 7 lint gate FAIL (28 flake8 violations: E501 line-too-long, E731 lambda-assign, F401 unused `__init__.py` imports) → orchestrator applied direct mechanical formatting fixes (no logic change) + `# noqa` per repo's own `addons/sale_margin/__init__.py` precedent → re-verified: flake8 clean, 9/9 + 221/221 tests still passing, upstream diff still empty → PASS
