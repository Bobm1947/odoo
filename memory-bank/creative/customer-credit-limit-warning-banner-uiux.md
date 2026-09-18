# UI/UX Decision: Two-Tier Customer Credit Limit Warning Banner

**Created**: 2026-09-18
**Status**: DECIDED
**Decision Type**: UI/UX

## User Context

### Target Users
- **Primary**: Sales Rep — uses the Sales app to create/edit quotations and sales orders; the productBrief lists no detailed goals/pain points beyond role name for this brownfield fork, so this design treats them as a task-focused user scanning the form top-to-bottom, not someone who drills into Accounting screens.
- **Secondary**: Sales Manager / Accountant reviewing an order — same visual surface, but may also have `account.group_account_invoice`/`account.group_account_readonly` access and could cross-reference the partner's Accounting record if curious. The banner must not assume this access, per AC-ERROR-1.

### User Goals
1. Notice, without hunting, that a customer is financially at-risk for this order (discoverability, zero extra navigation).
2. Understand at a glance *how* at-risk (approaching vs. already over) without reading dense text.
3. See the three concrete numbers (credit limit, current outstanding receivables, this order's contribution) needed to make a judgment call (proceed, call the customer, escalate) — without needing Accounting-group access to look anything up themselves.

### Use Cases
| Use Case | User | Goal | Frequency |
|----------|------|------|-----------|
| UC1 | Sales Rep drafting a quotation for a returning customer | Confirm the customer is in good standing before adding more lines | Every quotation for an existing customer with a credit limit set |
| UC2 | Sales Rep editing order lines on an existing draft | See the warning update live as the order total changes and crosses a threshold | Whenever lines/pricing change on a draft/sent order |
| UC3 | Sales Manager reviewing a rep's order before confirmation | Quickly distinguish "worth a heads-up" from "needs my decision before confirming" | Ad hoc, order review |

### Constraints
- **Devices**: Standard Odoo 18 backend web client — desktop-first responsive form view; no separate mobile-specific requirement documented in productBrief.md (NFRs largely "To be determined" for this fork). Design must not break at narrower backend widths (the existing sibling alert divs already wrap responsively; new markup follows the same pattern).
- **Accessibility**: No explicit WCAG level documented in productBrief.md. Absent a stated target, this design defaults to not relying on color alone to convey severity (WCAG 1.4.1 baseline) since that costs nothing extra and directly serves AC-ERROR-1's non-Accounting-user audience and general color-vision-deficient users.
- **Existing Patterns**: Must reuse Odoo's Bootstrap `alert-*` + `role="alert"` convention already used throughout the backend (see Options Explored — a same-app precedent for exactly this two-tier pattern exists in `addons/account_edi/views/account_move_views.xml`). Must preserve the "absent from DOM, not just hidden" pattern via `invisible="..."` (Guiding Principle: consistency with existing `partner_credit_warning == ''` idiom).

## User Flow

### Flow Diagram
```
[Sales Rep opens/edits Sale Order] → [Form renders / recomputes on change]
                                              ↓
                      [credit_warning_severity computed: none / warning / danger]
                                              ↓
                    none ──────────────→ [No banner div in DOM]
                    warning ───────────→ [Yellow "approaching" banner, 3 data points]
                    danger ────────────→ [Red "over limit" banner, 3 data points]
                                              ↓
                              [Rep reads banner, continues editing or confirms order]
                                    (banner never blocks Confirm button)
```

### Flow Description
1. **Entry**: Rep opens a new quotation or an existing draft/sent Sale Order for a customer with `credit_limit` set and `account_use_credit_limit` enabled. No navigation needed — banner region sits directly below the header buttons.
2. **Step 1 (compute)**: As `partner_id`, `order_line`, or pricing changes, the severity compute re-runs (existing live-recompute behavior, no save required — confirmed by core's `test_credit_limit_multicurrency`).
3. **Step 2 (render)**: View re-evaluates the two `invisible` conditions; at most one of the two severity divs is shown at a time (never both).
4. **Decision Point**: Rep reads the banner text and decides whether to proceed, adjust the order, or contact the customer/manager. This is purely informational — no gate.
5. **Exit**: Rep continues normal order flow (add lines, send, confirm). Confirming an over-limit order is still allowed — this task explicitly keeps the feature non-blocking (Scope Boundaries: "Blocking/preventing order confirmation" is out of scope).

### Error States
| Error | Cause | User Recovery |
|-------|-------|----------------|
| Banner text shows credit fields but rep can't verify them independently | Rep lacks `account.group_account_invoice`/`account.group_account_readonly` | None needed — this is by design (AC-ERROR-1); banner text itself is sufficient, no drill-in required. Rep escalates to Accounting/Sales Manager if they want to inspect the underlying partner record. |
| Banner doesn't appear even though rep expects one | `account_use_credit_limit` company setting disabled, or `credit_limit` unset on partner, or projected total is comfortably under 80% | No action required from the rep — this is correct "nothing to warn about" behavior (AC-HAPPY-3), not a bug. If a rep genuinely expects a warning, that's a data/config question for Accounting, not a UI gap. |

## Options Explored

### Option 1: Full two-tier Bootstrap color mapping (approaching = yellow, over = red)
- **Approach**: `credit_warning_severity in {'warning','danger'}` maps directly to Bootstrap's own severity vocabulary: approaching → `alert-warning` (yellow, matches today's only-existing color), over limit → `alert-danger` (red, new). This is the standard Bootstrap semantic mapping (`warning` = caution, `danger` = urgent/blocking-attention) that Odoo core itself already uses for exactly this two-tier shape elsewhere in the same Accounting/Invoicing app family: `addons/account_edi/views/account_move_views.xml:114-131` renders two sibling `<div>`s — `alert-danger` gated on `edi_blocking_level == 'error'`, `alert-warning` gated on `edi_blocking_level == 'warning'` — off a single severity field, on the same `account.move` form. This is a **direct structural precedent**, not an invented pattern.
- **Wireframe/Layout**:
  ```
  ┌─────────────────────────────────────────────┐
  │  <header> buttons/statusbar                  │
  ├─────────────────────────────────────────────┤
  │ ⚠ [alert-warning] Acme Corp is approaching   │  ← only when severity == warning
  │   its credit limit of $50,000.00...          │
  ├─────────────────────────────────────────────┤
  │ ⛔ [alert-danger] Acme Corp has exceeded its  │  ← only when severity == danger
  │   credit limit of $50,000.00...              │
  ├─────────────────────────────────────────────┤
  │  (other existing alert divs: archived        │
  │   products, duplicated order...)              │
  ├─────────────────────────────────────────────┤
  │  Order lines notebook                         │
  └─────────────────────────────────────────────┘
  ```
- **User Flow**: Rep sees yellow → mental model "worth noting, keep going"; sees red → mental model "stop and think, this is serious" — reuses the universal traffic-light convention the rep already applies to every other red/yellow signal in the app (and in daily life).
- **Pros**:
  - Instantly scannable at a glance — no reading required to register severity, critical for a rep who may have the form open for minutes while adding lines.
  - Directly precedented inside this very codebase (`account_edi`), so it's reinforcing an existing Odoo convention rather than inventing one — lower risk of looking "off-brand" for the product.
  - Cleanest possible two-tier signal; satisfies AC-HAPPY-1/2's "visually distinct" requirement with zero ambiguity.
- **Cons**:
  - Changes the color of the over-limit case for every existing deployment currently relying on the shipped-in-core `alert-warning` binary banner — reps and managers with muscle memory for "yellow = over limit" see red for the first time after upgrade.
  - Bootstrap red carries a "blocking/error" connotation in many UIs; must be visually/behaviorally reinforced (via copy and non-modal placement) that this is still informational, not a hard stop, to avoid violating the "must never feel blocking" acceptance requirement.
- **Usability**: High
- **Accessibility**: Medium (color alone is a signal — mitigated in the Decision section by pairing each tier with a distinct icon and label word, not color alone)
- **Implementation Complexity**: Low — two sibling divs each gated by an `invisible` condition on one severity field, directly mirroring the `account_edi` precedent's structure.

### Option 2: Preserve existing over-limit yellow; differentiate tiers by icon/weight instead of color
- **Approach**: Keep `alert-warning` (yellow) for *both* tiers — avoids any visible color change for existing over-limit users — and differentiate "approaching" from "over limit" using a secondary cue: a leading icon (e.g. `fa-info-circle` for approaching vs. `fa-exclamation-triangle` for over) plus bold/emphasized lead-in text ("Approaching..." vs. "**Over limit:**...").
- **Wireframe/Layout**:
  ```
  ┌─────────────────────────────────────────────┐
  │ ℹ [alert-warning] Approaching credit limit:  │  ← severity == warning
  │   Acme Corp, limit $50,000.00...              │
  ├─────────────────────────────────────────────┤
  │ ⚠ [alert-warning] Over credit limit: Acme    │  ← severity == danger, bold lead
  │   Corp, limit $50,000.00...                   │
  └─────────────────────────────────────────────┘
  ```
- **User Flow**: Rep must read the first few words (or notice the icon) to register severity — no color shortcut.
- **Pros**:
  - Zero visible regression for anyone currently relying on the existing yellow over-limit banner in production — the most conservative option.
  - Still not color-alone-dependent (already meets the accessibility mitigation Option 1 needs to add).
- **Cons**:
  - Both tiers share the same background color, so a rep skimming the form (not reading text) cannot distinguish "worth a note" from "seriously over" without stopping to read — directly weakens AC-HAPPY-1/AC-HAPPY-2's "visually distinct" requirement, which is a MUST-priority acceptance criterion.
  - Breaks from the account_edi precedent in the same codebase for no functional gain — introduces a *new*, less scannable convention instead of reusing an existing one.
  - Underuses Bootstrap's built-in severity vocabulary that the rest of the backend already trains users to read instantly.
- **Usability**: Medium — functional but requires reading, not glancing.
- **Accessibility**: High (best color-independence of all options, but at the cost of at-a-glance usability for sighted users)
- **Implementation Complexity**: Low-Medium — same two-div structure as Option 1, but needs a bit more copy/icon craftsmanship to make the non-color distinction unambiguous, plus a review of icon meaning (avoid `fa-info-circle`, which normally signals `alert-info`/neutral, being paired with a yellow background — mixed signal).

### Option 3: Three-tier Bootstrap ladder (info / warning / danger) mirroring account_edi's severity vocabulary
- **Approach**: A hybrid that still changes the over-limit color (like Option 1) but softens the "approaching" tier down one notch from today's yellow to `alert-info` (blue/neutral), reserving `alert-warning` (yellow) as a true "getting serious" middle state introduced later if ever needed. For this task's two required states, "approaching" → `alert-info`, "over" → `alert-danger`.
- **Wireframe/Layout**: Same two-div structure as Option 1, with `alert-info` swapped in for the approaching tier.
- **Pros**: Very clearly distinct from the danger tier (blue vs. red is a strong contrast); frees up yellow as a future middle rung if the business ever wants a 3-tier ladder.
- **Cons**: `alert-info` conventionally signals *neutral information*, not *caution* — misrepresents the semantic intent of "approaching your credit limit" (this is a caution, not FYI trivia) and would be the first departure from core's own choice to treat this exact state as `alert-warning` today. Also discards the one piece of visual continuity (yellow) that existing over-limit-yellow users could otherwise carry forward to the *new* approaching tier.
- **Usability**: Medium — visually distinct, but semantically mismatched cue (blue reads as "informational," undercutting urgency for a real caution state).
- **Accessibility**: Medium — same color-alone caveat as Option 1.
- **Implementation Complexity**: Low — identical structure to Option 1, one class swap.

## Evaluation Matrix

| Criteria | Option 1 (warning/danger) | Option 2 (color-preserving) | Option 3 (info/danger) |
|----------|----------|----------|----------|
| Usability | High | Medium | Medium |
| Accessibility (after icon+label mitigation) | High | High | Medium-High |
| Consistency (with account_edi precedent) | High | Low | Medium |
| Responsiveness | High (reuses existing responsive alert markup) | High | High |
| Performance | High (no runtime cost difference) | High | High |
| Implementation Effort | Low | Low-Medium | Low |

## Decision

**Chosen**: Option 1 — Full two-tier Bootstrap color mapping (`alert-warning` for approaching, `alert-danger` for over limit), reinforced with a non-color icon+label cue for accessibility.

### Rationale
- **AC-HAPPY-1/AC-HAPPY-2 (MUST, "visually distinct")** is best satisfied by a genuine color-family change, not a same-color icon/weight tweak (Option 2) or a semantically mismatched neutral-info treatment (Option 3). A Sales Rep skimming a form full of other content needs to register severity in a glance, not a read.
- **This is not an invented pattern.** `addons/account_edi/views/account_move_views.xml:114-131` already renders this exact structure — two sibling `alert-danger`/`alert-warning` divs gated by a single severity field — on `account.move`, a model in the same app family this task touches (`account`/`sale`). Reusing it means the change *increases* consistency with core Odoo conventions rather than deviating from them, directly serving the systemPatterns.md Guiding Principle of following established directory/extension patterns and Odoo's own extensibility conventions.
- **The "behavior change" concern is real but manageable, not disqualifying.** Today's shipped-in-core over-limit banner being yellow is arguably a *latent inconsistency* with Odoo's own severity vocabulary (yellow=caution, red=serious/blocking-attention) rather than an established design the product is intentionally preserving — `account_edi` on the very same platform already reserves red for its more serious tier. Framing the change as "this order is now colored consistently with every other `danger`-level alert in the backend, including elsewhere in Accounting" is a defensible, low-risk position, and this task ships as a **new, non-core addon** (`sale_credit_limit_warning`) rather than a stealth core patch, so the behavior change is visible and attributable to an explicit, documented feature addition — not a silent modification of stock Odoo.
- **Non-blocking requirement is protected by placement and copy, not color.** Bootstrap `alert-danger` commonly appears in *validation-error* contexts, which risks reading as "you must fix this before continuing." This design mitigates that by (a) keeping the exact same non-modal, inline placement as today's banner (never a dialog/toast), (b) never disabling or hiding the Confirm button, and (c) using informational, non-imperative copy ("has exceeded its credit limit of..." not "cannot be confirmed until..."). This exact mitigation pattern (red alert, still non-blocking) is also how `account_edi`'s own `alert-danger` div behaves — it reports an EDI error state without preventing further edits.
- **Accessibility mitigation is added on top, at negligible cost.** Rather than choosing Option 2 purely to avoid relying on color, Option 1 adopts Option 2's best idea as an *addition*: each tier gets a distinct icon (`fa-exclamation-triangle` for approaching, `fa-ban` or `fa-exclamation-circle` for over) and a distinct leading label word ("Approaching..." vs. "Exceeded..."), so color-vision-deficient users and screen-reader users (via the label text, since icons are decorative/`aria-hidden`) get the same two-way distinction sighted users get from color — this satisfies WCAG 1.4.1's "not color alone" principle without giving up Option 1's scannability advantage.

### Trade-offs Accepted
- **Visible color change for existing over-limit users.** Accepted because: (a) this feature ships as an explicit new addon, not a silent core patch, so the change is documented and attributable; (b) it brings the Sale Order form's severity vocabulary in line with `account_edi`'s existing convention in the same app suite, which is a consistency *improvement*; (c) the underlying business event (customer is over their credit limit) is unchanged — only its visual weight increases, which is directionally correct (more attention-worthy, not less).
- **Bootstrap `alert-danger` risks a "blocking" connotation.** Mitigated via placement (inline, not modal), never disabling Confirm, and non-imperative copy — but acknowledged as a residual UX risk worth calling out to UAT reviewers explicitly walking the "confirm an over-limit order" journey.

## Design Specifications

### Layout
- **Desktop**: Two sibling `<div class="alert ...">` blocks in the exact same DOM slot as today's single banner — immediately below `<header>`, above the "archived products" and "duplicated order" alert divs, above the order-lines notebook. At most one is visible at a time (severity is mutually exclusive: none/warning/danger).
- **Tablet**: Same markup; Bootstrap alert blocks already reflow/wrap text at narrower widths (no new responsive behavior required — matches the existing sibling alerts' behavior).
- **Mobile**: Same markup; Odoo backend form views are not optimized for narrow mobile widths as a rule (no documented mobile NFR in productBrief.md) — this banner does not introduce any new mobile-specific requirement beyond what the existing sibling alerts already provide.

### Key Components
| Component | Purpose | Behavior |
|-----------|---------|----------|
| Approaching-limit `<div class="alert alert-warning" role="alert">` | Caution-tier banner | Rendered only when `credit_warning_severity == 'warning'`; absent from DOM otherwise |
| Over-limit `<div class="alert alert-danger" role="alert">` | Urgent-tier banner | Rendered only when `credit_warning_severity == 'danger'`; absent from DOM otherwise |
| Leading icon (`<i class="fa fa-exclamation-triangle" aria-hidden="true"/>` / `<i class="fa fa-exclamation-circle" aria-hidden="true"/>`) | Non-color severity cue | Decorative only (`aria-hidden="true"`); the label word in the text itself carries the accessible meaning |
| `<field name="partner_credit_warning_message"/>` (or equivalent computed text field, name TBD by Architecture) | Message body | Plain text/pre-wrapped multi-line message containing all three required data points |

### Interactions
| Trigger | Action | Feedback |
|---------|--------|----------|
| Rep changes `partner_id` | Severity + message recompute | Banner appears/disappears/switches tier live, no save required (matches existing `_compute_partner_credit_warning` live-recompute behavior) |
| Rep adds/edits/removes an order line, or pricing changes | Severity + message recompute | Same as above — banner updates in place as the projected total crosses 80%/100% thresholds |
| Rep clicks "Confirm" while banner is showing (either tier) | Order confirms normally | No interception, no confirmation dialog, no field lock — banner is purely informational per Scope Boundaries |

### Responsive Behavior
| Breakpoint | Changes |
|------------|---------|
| < 640px | None beyond Bootstrap's default alert text wrapping (already the behavior of the existing sibling alert divs; no new CSS needed) |
| 640-1024px | None beyond default alert reflow |
| > 1024px | Standard full-width alert bar as shown in the wireframe above |

### Accessibility Requirements
- [x] Keyboard navigation support — banner is a static text region, not an interactive control; no new tab stops or focus traps introduced
- [x] Screen reader compatibility — `role="alert"` on both divs (already the existing pattern) ensures assistive tech announces the region; icons are `aria-hidden="true"` decorative so screen readers rely on the label word + message text, not the icon
- [x] Color contrast compliance (WCAG AA) — reuses Bootstrap's stock `alert-warning`/`alert-danger` palette, already used throughout the Odoo backend and presumed to meet the theme's existing contrast bar (no custom colors introduced)
- [ ] Focus indicators visible — N/A, banner is not focusable/interactive
- [x] Error messages accessible — N/A (this is not a form-validation error banner); message text is plain, readable, and includes the severity label word so meaning does not depend on icon or background color alone

## Implementation Guidance (for Architecture/Build handoff)

**Scope note**: Architecture owns final addon/file structure and the exact compute strategy (Creative Q1: extend `_build_credit_warning_message` vs. new `sale.order`-only compute). This section pins only the UI-facing surface — exact classes, xpath target, and copy — needed to implement Option 1 once Architecture confirms the underlying field(s).

### View change (exact xpath/inherit strategy note)
Extend `sale.order`'s form view (the view referenced by `addons/sale/views/sale_order_views.xml`, e.g. `sale.view_order_form`) via a new `<record>` with `_inherit`, xpath-targeting the **existing** banner div at `addons/sale/views/sale_order_views.xml:301-305`:

```xml
<xpath expr="//div[hasclass('alert-warning')][field[@name='partner_credit_warning']]" position="replace">
    <div class="alert alert-warning" role="alert"
         invisible="credit_warning_severity != 'warning'">
        <i class="fa fa-exclamation-triangle me-1" aria-hidden="true"/>
        <field name="partner_credit_warning_message"/>
    </div>
    <div class="alert alert-danger" role="alert"
         invisible="credit_warning_severity != 'danger'">
        <i class="fa fa-exclamation-circle me-1" aria-hidden="true"/>
        <field name="partner_credit_warning_message"/>
    </div>
</xpath>
```

This is a direct structural mirror of the `account_edi` precedent (`edi_blocking_level == 'error'` / `'warning'` pattern) applied to a new `credit_warning_severity` selection field (`'none' | 'warning' | 'danger'`, exact name/field finalized by Architecture) instead of replacing the field-emptiness check. When severity is `'none'`, both divs are absent — satisfying AC-HAPPY-3's "absent, not hidden" requirement the same way the existing `invisible="... == ''"` pattern does today.

### Exact CSS/Bootstrap classes per tier
| Severity | Div class | Icon class | 
|---|---|---|
| `warning` (approaching, >=80% and <=100%) | `alert alert-warning` | `fa fa-exclamation-triangle` |
| `danger` (over limit, >100%) | `alert alert-danger` | `fa fa-exclamation-circle` |
| `none` | (div absent) | — |

No custom SCSS required — both classes are stock Bootstrap/Odoo backend theme classes already in use elsewhere in this same view file and in `account_edi`.

### 80% boundary and rounding semantics
- Compute `ratio = total_credit / credit_limit` where `total_credit = credit + credit_to_invoice + current_amount` (identical inputs to today's `_build_credit_warning_message`, just evaluated at an earlier threshold too).
- **Inclusive lower bound**: `ratio >= 0.8` → at least "approaching" (matches AC-HAPPY-2's ">=80%" wording exactly).
- **Inclusive upper bound of "approaching"**: `ratio <= 1.0` → still "approaching," not yet "over" (matches AC-HAPPY-2's "<=100%" wording).
- **Exclusive over-limit floor**: `ratio > 1.0` → "over limit" (mirrors core's existing strict `total_credit <= partner_id.credit_limit` guard being the "no warning" condition — i.e., `total_credit > credit_limit` is core's existing over-limit trigger; this task's "danger" tier is exactly that condition, unchanged from core).
- **Floating-point tolerance**: use `odoo.tools.float_compare` / `float_is_zero` (Odoo's standard monetary-safe comparison utility, already used throughout `account`/`sale`) against the partner's currency rounding, not a raw `>=`/`<=` on floats, to avoid a ratio of `0.7999999999` or `1.0000000001` falsely landing in the wrong tier at the exact boundary. Compare `total_credit` directly against `credit_limit * 0.8` and `credit_limit` (not the derived `ratio` float) to keep the comparison in the same currency-rounded domain core already uses for its own `total_credit <= partner_id.credit_limit` check.
- Boundary test matrix already scoped in the task's Test Strategy (Phase 1: "no credit_limit set, feature disabled, <80%, exactly 80%, 80-100%, >100%") — this spec's exact-80% case must resolve to `warning`, not `none`.

### Exact message copy templates
Parallel in structure and tone to core's existing `_build_credit_warning_message` (`addons/account/models/account_move.py:1866-1876`), but restructured so all three required data points are explicitly labeled rather than folded only into a single total — directly serving AC-HAPPY-1/AC-HAPPY-2's "shows all 3 required data points" requirement.

**Approaching tier (`warning`, new)**:
```
%(partner_name)s is approaching its credit limit of %(credit_limit)s.
Outstanding receivables: %(outstanding_receivables)s. This order adds %(order_amount)s, for a projected total of %(total_credit)s.
```

**Over-limit tier (`danger`, revised from core's existing single-total wording to add the same explicit breakdown)**:
```
%(partner_name)s has exceeded its credit limit of %(credit_limit)s.
Outstanding receivables: %(outstanding_receivables)s. This order adds %(order_amount)s, for a total of %(total_credit)s.
```

Where:
- `partner_name` = `partner_id.commercial_partner_id.name` (unchanged from core)
- `credit_limit` = `formatLang(env, partner_id.credit_limit, currency_obj=...)` (unchanged from core)
- `outstanding_receivables` = `formatLang(env, credit + credit_to_invoice - exclude_amount, currency_obj=...)` — the "current outstanding receivables" data point the task requires, newly broken out as its own labeled figure (today's core message never surfaces this sub-total on its own, only folded into the final total)
- `order_amount` = `formatLang(env, current_amount, currency_obj=...)` — "this order's contribution," also newly broken out
- `total_credit` = `formatLang(env, credit + credit_to_invoice - exclude_amount + current_amount, currency_obj=...)` (unchanged formula from core, `total_credit` in `_build_credit_warning_message`)

Both templates keep the same `%(name)s ... %(value)s` `_()`-translatable format-string convention core already uses, and both are two-sentence, single-paragraph, non-imperative (no "you must..." / "cannot be confirmed..." phrasing) to protect the non-blocking requirement regardless of tier color.

### Component Structure
```
addons/sale_credit_limit_warning/
├── models/
│   ├── __init__.py
│   └── sale_order.py              ← adds credit_warning_severity (fields.Selection) +
│                                      partner_credit_warning_message (fields.Text, compute)
├── views/
│   └── sale_order_views.xml       ← _inherit xpath replacing the banner div (see above)
├── tests/
│   ├── __init__.py
│   └── test_credit_limit_warning.py
├── __init__.py
└── __manifest__.py
```
> Field names (`credit_warning_severity`, `partner_credit_warning_message`) are this UI/UX design's working names for the two data points the view binds to; Architecture confirms final field names/compute strategy (Creative Q1) and this view spec adapts to whatever names Architecture finalizes without changing the class/xpath/copy design above.

### Recommended Libraries/Patterns
- Stock Bootstrap `alert-warning`/`alert-danger` classes + Odoo's `fa` icon font (both already dependencies of `sale`/`account` — no new frontend library needed).
- `odoo.tools.float_compare` for the 80%/100% boundary comparisons (already used throughout `account`/`sale` for monetary comparisons — avoids introducing a new comparison utility).
- Reuse `formatLang` (already imported in `account_move.py`) for all currency-formatted values in the new message builder, for multi-currency/multi-company parity with core (Creative Q4).

## Validation Checklist

- [x] Meets all user goals — discoverability (AC-ENTRY-1), visual distinction (AC-HAPPY-1/2), correct absence (AC-HAPPY-3), non-Accounting-user readability (AC-ERROR-1)
- [x] Accessible per requirements — `role="alert"`, non-color-alone cues (icon + label word), stock contrast-compliant Bootstrap classes
- [x] Consistent with existing patterns — direct structural reuse of `account_edi`'s two-sibling-div severity pattern; preserves the "absent, not hidden" `invisible` idiom
- [x] Respects Guiding Principles and component architecture in systemPatterns.md — delivered via a new addon extending `sale.order`/`sale_order_views.xml` through `_inherit`/xpath, never editing core `addons/sale` or `addons/account` files directly
- [x] Responsive across devices — reuses existing responsive alert markup, no new breakpoint-specific behavior
- [x] Performance acceptable — no client-side JS added; pure server-computed fields + declarative view conditions, same cost profile as today's single banner
- [x] Implementation feasible — Low complexity per the Evaluation Matrix; two sibling divs + one severity field + one message-builder method

## Next Steps

1. Architecture Design creative phase resolves Creative Q1 (extend vs. new compute) and finalizes the exact field names this UI/UX spec's `credit_warning_severity`/`partner_credit_warning_message` placeholders bind to.
2. Phase 2 build (per the task's Implementation Roadmap) implements the xpath/view change and message-builder copy exactly as specified above, plus the boundary-comparison logic using `float_compare`.
3. UAT should explicitly walk the "confirm an order while the red over-limit banner is showing" journey to verify the non-blocking requirement holds in practice, not just in copy — this is the residual risk flagged under Trade-offs Accepted.
