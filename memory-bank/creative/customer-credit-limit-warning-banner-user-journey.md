# User Journey Design: Customer Credit Limit Warning (Sale Order banner)

**Created**: 2026-09-18
**Status**: DECIDED
**Decision Type**: User Journey
**Task**: `customer-credit-limit-warning`

## Journey Overview

**Feature**: A two-tier (approaching / over-limit) informational banner on the Sale Order form that tells a Sales Rep, while they are still building a quotation, how much credit exposure this customer already carries and what this order would add.
**Primary Persona**: Sales Rep (productBrief.md § Key Personas — "Uses CRM/Sales apps... issue quotations")
**Journey Type**: **Synchronous, ambient** — there is no discrete "operation" to start or wait for. The journey is a continuously-recomputed peripheral signal that rides along the rep's existing quote-building journey.
**Orchestration Pattern**: **Inline Contextual Banner (passive, zero-interaction), evolved in place** — no wizard, no modal, no dismissal, no navigation.

### Success Statement

> A Sales Rep building a quotation sees, without clicking anything, a banner at the top of the form that says the customer is approaching (yellow) or has reached (red) their credit limit, states the limit, the existing outstanding receivables, and what this order adds — and the banner updates itself as the rep edits order lines, before the quote is ever saved.

### Governing Design Principle: Trigger Parity

This banner **already exists today** in binary form and is familiar to every existing user. The journey is therefore designed around one non-negotiable constraint:

> **Every order that shows a banner today must show the *over-limit* banner tomorrow, fired by the exact same condition, at the exact same moment, with the same opening sentence.** The only genuinely new experience is a *lower-severity banner that appears earlier*.

Concretely: core's trigger is `total_credit > credit_limit` (`_build_credit_warning_message`, `addons/account/models/account_move.py:1862` — `if not partner_id.credit_limit or total_credit <= partner_id.credit_limit: return ''`). That boundary is preserved byte-for-byte for the red tier. Nothing that is silent today becomes loud in a *new* way; the yellow tier is strictly additive earlier warning. This is what makes the change feel like an evolution rather than a redesign.

## Persona Context

### Primary User

- **Who**: Sales Rep
- **Goal**: Get an accurate quotation out the door quickly. Credit exposure is *not* their primary task — it is a constraint they need to be told about, not something they go looking for.
- **Context**: Odoo backend web client, desktop, inside the Sales app, on a `sale.order` form in `draft` or `sent` state. Often mid-flow: picking a customer, adding 3-10 order lines, adjusting quantities and discounts, then confirming or emailing.
- **Proficiency**: Fluent in Odoo forms; **not** an Accounting user. Critically, they typically do **not** hold `account.group_account_invoice` / `account.group_account_readonly`, so they cannot see `credit`, `credit_limit`, or `credit_to_invoice` anywhere else in the UI. This banner is, for this persona, the **only** window onto the customer's credit position.
- **Existing mental model**: "A yellow bar at the top of the quote means something is wrong with this quote." Established by three sibling alert divs occupying the same region (`sale_order_views.xml:301-314`: credit warning, archived products, duplicated order).

### Secondary Users

- **Who**: Accountant / Bookkeeper, Sales Manager
- **Different needs**: They *can* see the underlying partner fields directly (Accounting groups) and have the Partner form and Aged Receivable reports available. For them the banner is a convenience reminder, not the sole channel. No separate journey is designed for them — the same banner serves both, and the design deliberately does **not** add an Accounting-flavored drill-down that would be dead weight for the primary persona.

## Journey Map

### Entry Points

| Entry | Context | User Intent |
|-------|---------|-------------|
| Sales ▸ Orders ▸ Quotations ▸ *open a quotation* | Form renders in `draft`/`sent` | "Build / review this quote" — banner is seen incidentally |
| Sales ▸ New (blank quotation) ▸ select a Customer | `partner_id` onchange fires | "Start a quote for this customer" — banner appears at customer selection if exposure already exists |
| CRM ▸ Opportunity ▸ New Quotation | Same form, partner pre-filled | Same as above |
| Editing any order line qty / price / discount | `amount_total` recompute | "Adjust the quote" — banner appears / changes tier live |

There is **no dedicated entry point and none is wanted**. Discoverability is achieved by placement, not by navigation: the banner occupies the fixed region between `</header>` and `<sheet>`, above the fold on every Sale Order form.

**Journey boundary (important, see Findings):** core gates the compute on `order.state in ('draft', 'sent')` (`addons/sale/models/sale_order.py:774-775`). Once the rep confirms the order (`state == 'sale'`), the banner **disappears entirely**. This is correct and is preserved: the warning is shown exactly while the rep can still act on it, and vanishes once the decision is made. It also removes any ambiguity about the banner being a gate — it demonstrably is not.

### State Diagram

```
                    ┌──────────────────────────────────────────────┐
                    │  Sale Order form open (state = draft | sent)  │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────▼───────────────────────┐
                    │ Recompute trigger: partner_id | order_line    │
                    │ amount_total | company_id  (no save required) │
                    └──────────────────────┬───────────────────────┘
                                           │
                 ┌─────────────────────────┼─────────────────────────┐
                 │                         │                         │
        gate fails (any of):        80% ≤ total ≤ limit        total > limit
        • feature off                      │                         │
        • no credit_limit                  │                         │
        • total < 80% of limit             │                         │
        • state ∉ (draft, sent)            │                         │
                 │                         │                         │
                 ▼                         ▼                         ▼
        ┌────────────────┐        ┌─────────────────┐       ┌─────────────────┐
        │  S0: NO BANNER │◄──────►│ S1: APPROACHING │◄─────►│  S2: OVER LIMIT │
        │  (absent from  │        │  yellow         │       │  red            │
        │   the DOM)     │        │  role=status    │       │  role=alert     │
        └────────────────┘        └─────────────────┘       └─────────────────┘
                 ▲                         │                         │
                 │                         └───── confirm order ─────┘
                 │                                     │
                 └─────────────────────────────────────┘
                        (state → 'sale'; banner retires)

        All transitions are bidirectional and free — the rep can walk
        back across every boundary by deleting a line or lowering a qty.
```

### Step-by-Step Journey

#### Step 1: Form renders / customer selected — S0 (no banner)
- **System**: `sale.order` form view (web client) + `_compute_partner_credit_warning` on the server
- **User Sees**: A normal quotation form. **No banner element at all** — not a collapsed one, not an empty div. The header sits directly on top of the sheet.
- **User Actions**: Pick a customer, start adding order lines — ordinary quote building.
- **Feedback**: Absence *is* the feedback. Silence means "no credit concern here."
- **Transitions**: Any change to `partner_id`, `order_line`, or `amount_total` triggers a server round-trip that may promote to S1 or S2.
- **Data Flow**: `partner.credit` + `partner.credit_to_invoice` + `order.amount_total / currency_rate` read under `.sudo()`; compared against `partner.credit_limit`.

#### Step 2: Rep adds lines and crosses 80% — S1 (approaching, yellow)
- **System**: Server recompute on the onchange round-trip; client re-renders the form
- **User Sees**: A yellow (`alert alert-warning`) banner materialises between the header and the sheet, two lines:

  > **Deco Addict is approaching its credit limit of: $10,000.00**
  > Outstanding (unpaid invoices + confirmed orders): $6,200.00 · This order: $2,400.00 · Total: $8,600.00 — 86% of limit

- **User Actions**: Read it. Optionally lower a quantity, drop a line, or carry on. **No action is required or offered.**
- **Feedback**: Colour (yellow = advisory) + the explicit `% of limit` figure, which makes the otherwise-invisible 80% threshold self-explanatory — the rep never has to be told what triggered it.
- **Transitions**: Add more → S2. Remove value → back to S0. Change customer → recompute from scratch.
- **Data Flow**: All three required data points are on-screen simultaneously with no interaction: **limit** (line 1), **outstanding receivables** (line 2, first term), **this order's contribution** (line 2, second term), plus the derived total and percentage.

#### Step 3: Rep crosses 100% — S2 (over limit, red)
- **System**: Same recompute path; severity flips
- **User Sees**: The **same two-line banner in the same position, recoloured red** (`alert alert-danger`). Line 1 keeps core's exact existing sentence; line 2 keeps the same three-term breakdown:

  > **Deco Addict has reached its credit limit of: $10,000.00**
  > Outstanding (unpaid invoices + confirmed orders): $6,200.00 · This order: $4,900.00 · Total amount due: $11,100.00

- **User Actions**: Still none required. The rep may confirm the order anyway — **this banner never blocks confirmation.**
- **Feedback**: Colour escalation is the entire signal. Because both tiers are exactly two lines, the S1→S2 transition causes **zero layout reflow** — the banner recolours and rewords in place under the rep's eyes with no content jump.
- **Transitions**: Reduce the order → back to S1 → S0. Confirm → banner retires (state gate).

#### Step 4: Success
- **User Sees**: Either a confirmed order (banner gone by design) or a quote they consciously adjusted.
- **Value Delivered**: The rep made a credit-aware decision *before* committing, using information they have no other way to see, without leaving the form or losing a keystroke of work.
- **Next Actions**: Confirm, Send by Email, adjust lines, or escalate to a manager out-of-band. All pre-existing; the journey adds none.

## Async Handling

**Not applicable.** This journey is fully synchronous. There is no background job, no queue, no notification channel, and deliberately so — see "Options Explored / Option 4".

The only latency the rep experiences is the standard Odoo onchange round-trip that already occurs on every order-line edit. The credit compute adds two `res.partner` field reads to a round-trip that is already happening; it introduces **no new wait state, no spinner, and no new failure surface**.

## Live-Update Behaviour (threshold crossings)

This is the part of the journey the existing binary banner barely exercises and the new yellow tier will exercise constantly.

| Transition | Trigger | What the rep perceives | Design treatment |
|---|---|---|---|
| S0 → S1 | Order grows past 80% | Banner **inserts**; sheet shifts down ~2 text rows | Accepted. Identical to today's S0→over-limit insertion and to the sibling archived-product/duplicate alerts. Odoo re-renders the form on every onchange anyway, so the rep is already acclimatised. |
| S1 → S2 | Order grows past 100% | Banner **recolours and rewords in place** | **Zero reflow by construction** — both tiers are pinned to exactly two lines. This is the single most important micro-detail of the design: the most alarming transition is also the calmest visually. |
| S2 → S1 | Rep reduces the order | Recolours back to yellow | Symmetric, free, no penalty for exploring. Reinforces "this is information, not a gate." |
| S1 → S0 | Order drops below 80% | Banner **removes**; sheet shifts up | Accepted, same rationale as S0→S1. |
| any → S0 | Customer cleared or swapped | Banner recomputed from scratch | Falls out of `@api.depends('partner_id', ...)`. |
| any → gone | `action_confirm` | Banner retires with the draft state | Intentional; see "Journey boundary". |

**No animation.** No slide, no fade. Odoo has no such convention in this region, and an animated insert would draw more attention to the layout shift, not less. Instant is calmer.

**No debounce/throttle.** The recompute is server-side on an onchange the rep already triggers; adding client-side suppression would create a window where the banner disagrees with the form.

### Accessibility of live updates (a new requirement the second tier creates)

Today's single banner uses `role="alert"` — an **assertive** live region. With one tier that fires rarely and only past the limit, that is tolerable. With a yellow tier that will fire on a large fraction of quotations **and recompute on every quantity keystroke round-trip**, an assertive region would interrupt a screen-reader user's speech on essentially every line edit. That is a real regression risk the two-tier design itself introduces.

**Design decision:**

| Tier | ARIA role | Rationale |
|---|---|---|
| S1 approaching (yellow) | `role="status"` (polite) | Queues behind what the user is doing; announced at a natural pause. Advisory content deserves a polite region. |
| S2 over limit (red) | `role="alert"` (assertive) | Preserves today's behaviour exactly at the tier where today's banner lives. Genuinely warrants interruption. |

This also means the escalation to red is audibly distinct for non-sighted users, not just visually — the severity signal survives the loss of colour, which is required regardless (colour must never be the only channel; the differing verbs "is approaching" vs. "has reached" carry the tier in the text itself).

## Distributed System Flow

Single-process; the "distribution" is only the client/server form round-trip.

```
  [Web client: sale.order form]
            │  onchange(partner_id | order_line | amount_total)
            ▼
  [Odoo server: _compute_partner_credit_warning]
            │  order.sudo().with_company(order.company_id)
            ▼
  [res.partner: credit, credit_to_invoice, credit_limit]  (company-dependent)
            │
            ▼
  [message + severity]  ──►  back in the onchange response  ──►  re-render banner
```

### Responsibility Matrix

| Step | Owner | State Storage | Failure Handling |
|------|-------|---------------|------------------|
| Trigger recompute | Web client (onchange) | Client form state (unsaved) | Standard Odoo onchange error surface; no bespoke handling |
| Compute severity + message | `sale.order` compute (new addon, `_inherit`) | **None — non-stored** `fields.Text` + severity | Empty string ⇒ banner absent; the null case is the safe default |
| Read partner credit fields | `res.partner` via `.sudo()` | PostgreSQL | `.sudo()` elevation is mandatory (AC-ERROR-1); without it a Sales-only user gets an AccessError on form open |
| Render tier | Form view XML (`_inherit` + xpath) | DOM only | `invisible="... == ''"` removes the node entirely |

## Error Handling

### Error States

| Error Type | When | User Sees | Recovery |
|------------|------|-----------|----------|
| No customer selected | Blank quotation | No banner (`credit_limit` falsy on empty partner) | N/A — correct silent state |
| Customer has no credit limit | `credit_limit == 0` | No banner | N/A — correct silent state |
| Company feature disabled | `account_use_credit_limit` off | No banner, ever | Admin enables it in Settings ▸ Invoicing (outside this journey) |
| Rep lacks Accounting groups | Always, for this persona | **Banner still fully visible** via `.sudo()` | N/A — this is the AC-ERROR-1 guarantee; a failure here would look to the rep like an AccessError traceback on form open, which is why it is a MUST |
| Order currency ≠ company currency | Multi-currency quote | Amounts shown in **company** currency (`formatLang(..., currency_obj=record.company_id.currency_id)`), order total converted via `currency_rate` | Pre-existing behaviour, deliberately unchanged. Documented as a known rough edge, not fixed here. |
| Multi-company: active company ≠ order company | Multi-company DB | Potentially the wrong company's `credit_limit` — see Findings | The new compute must apply `.with_company()` correctly (core's call is a discarded no-op) |
| Stale banner vs. unsaved edits | Between keystroke and round-trip | Momentarily previous tier | Self-healing on the next onchange; sub-second, no user-visible inconsistency worth designing for |

### Partial Failure

There is no partial state to fail into. The compute is all-or-nothing and non-stored: it either produces a message (banner renders) or an empty string (banner absent). There is nothing to roll back, resume, or reconcile — a deliberate property of keeping this a pure compute rather than a stored field with its own lifecycle.

## Options Explored

### Option 1: Enriched Passive Two-Tier Banner (evolution in place) — **CHOSEN**

- **Orchestration**: Inline contextual banner, zero interaction
- **Flow Summary**: Same div, same slot, same trigger point for red. Severity drives the Bootstrap class, the ARIA role, and one verb in line 1. Line 2 becomes a structured three-term breakdown that surfaces all required data points with no interaction at all.
- **Wireframe**:
  ```
  ┌──────────────────────────────────────────────────────────────┐
  │ New  Send by Email  Confirm  Preview  Cancel      [Quotation]│  ← header
  ├──────────────────────────────────────────────────────────────┤
  │ ░░ Deco Addict is approaching its credit limit of: $10,000.00│  ← yellow
  │ ░░ Outstanding (unpaid invoices + confirmed orders):         │    2 lines
  │ ░░ $6,200.00 · This order: $2,400.00 · Total: $8,600.00      │    role=status
  │ ░░ — 86% of limit                                            │
  ├──────────────────────────────────────────────────────────────┤
  │  Customer  [Deco Addict            ]   Expiration [       ]  │  ← sheet
  │  ┌ Order Lines ┬ Optional Products ┬ Other Info ┐            │
  │  │ Product      Qty   Unit Price   Taxes  Subtotal           │
  ```
  and at >100%, **identical geometry**, recoloured:
  ```
  │ ▓▓ Deco Addict has reached its credit limit of: $10,000.00   │  ← red
  │ ▓▓ Outstanding (unpaid invoices + confirmed orders):         │    2 lines
  │ ▓▓ $6,200.00 · This order: $4,900.00 · Total amount due:     │    role=alert
  │ ▓▓ $11,100.00                                                │
  ```
- **Pros**:
  - Zero added friction — the rep's hands never leave the order lines
  - All three mandated data points visible simultaneously, no click, no hover, no expand
  - Both tiers same height ⇒ the escalation transition is reflow-free
  - Line 1 of the red tier is **verbatim core copy**, preserving ~228 locales' existing translations and the exact sentence existing users already know
  - The `% of limit` figure makes the 80% threshold self-documenting, removing the need for a configurable-threshold setting
  - Nothing to maintain: no dismissal state, no session storage, no new endpoint
- **Cons**:
  - Line 2 is dense; at narrow viewports it wraps to 2-3 visual rows (mitigated: middot-separated terms wrap gracefully; still one logical line)
  - Can't be silenced — a rep who knowingly works an over-limit account sees it on every quote
  - Today's over-limit yellow becomes red, a visible change for existing users (see Trade-offs)

### Option 2: Banner + Progressive Disclosure ("Show breakdown")

- **Orchestration**: One-line banner headline + a collapsible caret revealing the credit-limit / outstanding / this-order breakdown
- **Flow Summary**: Banner shows only "Deco Addict is approaching its credit limit"; the rep clicks a chevron to expand the numbers.
- **Wireframe**:
  ```
  │ ░░ Deco Addict is approaching its credit limit   [ Details ▾ ]│
  ```
  expanded:
  ```
  │ ░░ Deco Addict is approaching its credit limit   [ Details ▴ ]│
  │ ░░   Credit limit ................... $10,000.00              │
  │ ░░   Outstanding receivables ........  $6,200.00              │
  │ ░░   This order .....................  $2,400.00              │
  │ ░░   ─────────────────────────────────────────                │
  │ ░░   Total ..........................  $8,600.00  (86%)       │
  ```
- **Pros**: Calmest collapsed state; a genuinely scannable aligned breakdown when expanded; scales if more terms are ever added
- **Cons**:
  - **Costs a click to reach data the acceptance criteria say the user must see** — AC-HAPPY-1/2 require the three data points; hiding them behind an affordance arguably fails them, or at minimum makes them conditionally satisfied
  - Expand/collapse is client state that Odoo form views don't naturally persist across the onchange re-renders this banner experiences constantly — the panel would collapse itself every time the rep edits a line, which is worse than never having opened it
  - Requires a new OWL component + template + assets bundle for a banner that is currently one line of declarative XML — large blast radius for a two-tier change
  - Introduces two different heights, so S1→S2 transitions can reflow
- **Best For**: Dashboards and settings pages, not a form the user is actively typing into

### Option 3: Banner + "View Customer Receivables" action affordance

- **Orchestration**: Passive banner (as Option 1) plus a secondary link/button opening the partner's outstanding invoices
- **Pros**: Answers the natural follow-up "which invoices?"; useful to Accountants and Sales Managers
- **Cons**:
  - **Navigates away from an unsaved quotation** — the single worst thing you can do to a rep mid-quote. Odoo would either discard the draft or force a save/dirty-state dialog. Context loss is severe and the rep's primary task is interrupted by an affordance they didn't ask for.
  - The primary persona **cannot open that view anyway** — they lack `account.group_account_invoice`, so the link would be hidden or error for the exact user the banner exists to serve, leaving a control that only helps the secondary persona
  - Adds an action, a window action XML, and access-group conditioning to a purely informational element
- **Best For**: The Accounting-side (`account.move`) rendering of the same warning — explicitly out of scope for this task
- **Verdict**: Rejected for this journey; **documented as a deferred enhancement** should the Invoicing tri-state ever be taken up.

### Option 4: Dismissible / session-suppressible banner

- **Orchestration**: Passive banner with an × that suppresses it for the session or for that customer
- **Pros**: Removes repetition fatigue for reps who deliberately work over-limit accounts
- **Cons**:
  - **Requires new persisted state** for a feature whose entire architectural virtue is being a non-stored compute — a dismissal table/flag, a scope decision (per user? per order? per partner? per session?), and an expiry policy
  - A dismissed over-limit warning is a **risk-transfer hazard**: the organisation's reason for the feature is that someone sees it
  - The banner already self-dismisses at exactly the right moment — on order confirmation (state gate) and whenever the rep reduces the order below threshold. The genuine dismissal need is already met by the data.
- **Verdict**: Rejected.

## Evaluation Matrix

| Criterion | Option 1 (chosen) | Option 2 | Option 3 | Option 4 |
|-----------|---|---|---|---|
| Discoverability | H | H | H | H |
| Learnability | H | M | M | M |
| Efficiency (repeat use) | H | L | M | M |
| Error Prevention | H | M | H | L |
| Error Recovery | H | H | M | M |
| Feedback clarity | H | M | H | M |
| Consistency with existing UI | H | L | M | L |
| Accessibility | H | M | M | M |
| Implementation blast radius | H (small) | L (large) | M | L (large) |
| Delight / calmness | H | M | M | M |

## Decision

**Chosen**: Option 1 — Enriched Passive Two-Tier Banner, evolved in place.

### Rationale

1. **The primary persona's task is not credit review.** A Sales Rep is building a quote against the clock. The correct journey for a peripheral constraint is one that costs them **zero actions** — read it or ignore it, in under two seconds, without moving the mouse. Options 2 and 3 both charge the rep an interaction for information the acceptance criteria say must simply be *seen*.
2. **It satisfies the acceptance criteria without interpretation.** AC-HAPPY-1 and AC-HAPPY-2 require the credit limit, outstanding receivables, and this order's contribution to be present. Option 1 puts all three on screen unconditionally. Option 2 hides two of them behind a control that, given Odoo's onchange re-render behaviour, would auto-collapse every time the rep edits a line.
3. **It is the smallest possible change that delivers the whole feature.** The element, the slot, the visibility mechanism, and the recompute triggers all already exist. The delta is: a severity value, a Bootstrap class, an ARIA role, one changed verb, and a richer second line. Everything else the rep already knows stays put.
4. **Trigger parity protects existing users.** Nobody's existing workflow gains or loses a warning at a different moment. The red tier fires under the identical condition as today's banner.
5. **Zero-reflow escalation is the feature's best micro-detail.** Pinning both tiers to two lines means the moment that matters most — crossing 100% while typing — is a colour change under a steady cursor, not a jump. This falls out of the copy design, costs nothing, and is impossible in Options 2 and 3.
6. **No new persisted state, no new endpoint, no new failure mode.** The journey inherits a compute that is already non-stored, already sudo-elevated, already multi-currency-aware, and already live-updating.

### Resolution of the open questions posed to this phase

| Question | Answer |
|---|---|
| Does the journey need interaction beyond passive viewing? | **No.** Dismissal (Option 4) and drill-down (Option 3) are both rejected with reasons; progressive disclosure (Option 2) is rejected because Odoo's re-render cadence defeats it. |
| Exact copy for the two tiers | Specified below — parallel sentence structure, core sentence preserved for the over tier. |
| Behaviour across live threshold boundaries | Fully specified in "Live-Update Behaviour", including the zero-reflow constraint and the ARIA politeness split. |
| Is 80% worth making configurable? | **No.** The banner prints `— 86% of limit`, which makes the threshold self-evident at the point of use. A settings toggle would add a configuration surface to explain something the copy already explains. Keep it fixed, as the task specifies. |

### Trade-offs Accepted

- **Today's over-limit banner turns from yellow to red.** Accepted deliberately. Keeping over-limit yellow would force the new "approaching" tier into some third colour (blue/info), making the two tiers nearly indistinguishable at a glance and defeating the feature's whole purpose. The mitigation is that the *sentence* is unchanged, so the recognition cue existing users actually rely on ("Deco Addict has reached its credit limit of…") survives intact; only the colour sharpens.
- **Line 2 is information-dense.** Accepted: the alternative (Option 2) costs a click and fights the re-render cycle. Mitigated by middot separation, which wraps readably, and by keeping the terms in causal order (existing → this order → total).
- **Sales Reps working chronically over-limit accounts see the banner on every quote.** Accepted — that is the feature working. See Option 4 rejection.
- **Amounts render in company currency on foreign-currency quotes.** Pre-existing core behaviour, explicitly not changed here to avoid scope creep into the shared message builder. Logged as a known rough edge.
- **No signal on list/kanban views.** A rep scanning the quotation list gets no credit cue. Out of scope; noted as a possible future enhancement (a decoration on the list view would be the natural home).

## Copy Specification (normative)

Both tiers render **exactly two lines**. The `This order` term is omitted when the order's contribution is zero (empty or zero-value quotation), yielding two variants per tier rather than core's four.

**S1 — Approaching (`alert alert-warning`, `role="status"`)**
```
{partner_name} is approaching its credit limit of: {credit_limit}
Outstanding (unpaid invoices + confirmed orders): {outstanding} · This order: {current} · Total: {total} — {pct}% of limit
```

**S2 — Over limit (`alert alert-danger`, `role="alert"`)**
```
{partner_name} has reached its credit limit of: {credit_limit}
Outstanding (unpaid invoices + confirmed orders): {outstanding} · This order: {current} · Total amount due: {total}
```

Notes:
- Line 1 of S2 is **verbatim** core's existing `_('%(partner_name)s has reached its credit limit of: %(credit_limit)s')`. Do not re-word it; existing translations must continue to resolve.
- Line 1 of S1 is deliberately the same sentence with one verb swapped, so translators immediately recognise the sibling string.
- `{outstanding}` = `partner.credit + partner.credit_to_invoice` — i.e. posted-unpaid invoices **plus** other already-confirmed sale orders. The parenthetical label exists precisely because `credit_to_invoice` is non-obvious.
- `{current}` = this order's contribution in company currency (`amount_total / currency_rate`).
- `{total}` = `outstanding + current`.
- All money values via `formatLang(..., currency_obj=order.company_id.currency_id)`, matching core.
- `{pct}` = `round(total / credit_limit * 100)`, integer, **approaching tier only**. It is deliberately absent from the over tier: a rounded percentage could display "100%" at 100.4%, contradicting the red styling. On the approaching tier the value is bounded to 80–100 and is the primary explanation of *why* the banner appeared.

## Threshold Semantics (normative)

Evaluate in this order; the first match wins.

| Order | Condition | Tier |
|---|---|---|
| 1 | `state not in ('draft','sent')` OR `not company_id.account_use_credit_limit` OR `not partner.credit_limit` | S0 — empty string |
| 2 | `total_credit > credit_limit` (currency-rounded comparison, **identical to core's existing `total_credit <= credit_limit → ''` boundary, inverted**) | S2 — over |
| 3 | `total_credit >= 0.8 * credit_limit` (currency-rounded, **inclusive** at exactly 80%) | S1 — approaching |
| 4 | otherwise | S0 — empty string |

- **Exactly 100%** (`total_credit == credit_limit`) falls to rule 3 ⇒ **approaching/yellow**, not red. This is required by trigger parity: core returns `''` at exactly the limit today, so red must not fire there either.
- **Exactly 80%** is **inclusive** ⇒ yellow.
- Comparisons use the company currency's rounding (Odoo `currency.compare_amounts` / `float_compare`), never raw float `>`/`>=`, so that sub-cent noise cannot flicker the banner between tiers across round-trips.

## Implementation Guidelines

### Frontend / View Requirements

1. New addon's `views/sale_order_views.xml` `_inherit`s `sale.view_order_form` and xpaths the existing credit-warning div (`sale_order_views.xml:301-305`).
2. The div's `class` and `role` must be **severity-driven**, not static. Two candidate mechanics for the Architecture phase to pin: (a) a computed `partner_credit_warning_severity` Selection field driving `class="alert alert-{severity}"` via an attribute expression, or (b) two sibling divs each with its own `invisible=` on the severity value. Option (b) is more Odoo-idiomatic in declarative XML and avoids dynamic-class limitations; it must keep both variants at equal height to preserve the zero-reflow property.
3. Keep the banner in its existing slot — first of the three sibling alerts, immediately after `</header>`. Do not move it.
4. Preserve `invisible="partner_credit_warning == ''"` semantics so S0 removes the node from the DOM rather than hiding it (AC-HAPPY-3).

### Backend Requirements

1. New addon, `_inherit = 'sale.order'` (never edit `addons/sale` directly — systemPatterns.md § "Inheritance over modification").
2. A severity value must be exposed to the view alongside the message (non-stored, same `@api.depends` set as the message).
3. `@api.depends('company_id', 'partner_id', 'amount_total')` must be preserved so the live-update journey works without a save.
4. `.sudo()` elevation is **mandatory** (AC-ERROR-1) — without it the primary persona gets an AccessError on form open, which is a hard journey failure, not a degraded one.
5. **Fix the `with_company` no-op** — see Findings.

### Integration Points

| System | Interface | Data Exchanged |
|--------|-----------|----------------|
| `res.partner` | ORM read under `.sudo()`, company-dependent | `credit`, `credit_to_invoice`, `credit_limit` |
| `res.company` | ORM read | `account_use_credit_limit`, `currency_id` |
| `account.move._build_credit_warning_message` | Shared core method rendered in **both** `sale_order_views.xml:303` and `account_move_views.xml:840` | Architecture phase must ensure the Invoicing banner's behaviour is unchanged (out of scope) |
| Web client onchange | JSON-RPC | Recomputed message + severity per round-trip |

## Acceptance Criteria

### AC-ENTRY-1: Sales Rep sees the banner region with zero extra navigation
**Priority**: MUST

**Given** a Sales Rep with a `sale.order` in `draft` or `sent` state open in the Sales app
**When** the form renders
**Then** if a warning applies, the banner is present between `</header>` and `<sheet>` — the same slot as the existing `partner_credit_warning` div — with no click, tab, scroll, or menu navigation required to reach it

**Verification**:
- [ ] E2E: banner node is a direct sibling immediately following `header` in the rendered form
- [ ] E2E: banner is above the fold at a standard 1280×800 viewport with no scrolling
- [ ] E2E: no menu/tab/settings interaction precedes its appearance

### AC-HAPPY-1: Over-limit (red) journey renders all required data
**Priority**: MUST

**Given** `account_use_credit_limit` enabled, a partner with `credit_limit` set, and `credit + credit_to_invoice + this order > credit_limit`
**When** the Sale Order form renders in `draft`/`sent`
**Then**:
- Banner carries `alert-danger` and `role="alert"`
- Line 1 is core's exact sentence including the formatted credit limit
- Line 2 contains outstanding receivables, this order's contribution, and the total, all in company currency
- The banner occupies exactly two lines of copy

**Verification**:
- [ ] Integration: message string contains limit, outstanding, current, and total values
- [ ] E2E: rendered element carries `alert-danger` and `role="alert"`
- [ ] Integration: red fires under the *identical* boundary as core today (trigger parity regression guard)

### AC-HAPPY-2: Approaching (yellow) journey renders at ≥80%
**Priority**: MUST

**Given** the same preconditions, with `0.8 × credit_limit ≤ total_credit ≤ credit_limit`
**When** the form renders
**Then**:
- Banner carries `alert-warning` and `role="status"`
- Line 1 uses the "is approaching" verb form and states the limit
- Line 2 contains outstanding, this order, total, and `{pct}% of limit`
- The banner occupies exactly two lines of copy (same height as the over tier)

**Verification**:
- [ ] Integration: exactly 80% of limit ⇒ yellow (inclusive boundary)
- [ ] Integration: exactly 100% of limit ⇒ yellow, **not** red (trigger parity)
- [ ] E2E: rendered element carries `alert-warning` and `role="status"`

### AC-HAPPY-3: Banner fully absent when there is nothing to warn about
**Priority**: MUST

**Given** any of: no `credit_limit` set, `account_use_credit_limit` disabled, total below 80% of limit, or `state not in ('draft','sent')`
**When** the form renders
**Then** no banner node exists in the DOM at all (absent, not visually hidden), and the sheet sits directly beneath the header

**Verification**:
- [ ] Integration: message is `''` for each of the four suppression conditions
- [ ] E2E: no matching alert element is queryable in the DOM (not merely `display:none`)

### AC-ERROR-1: Banner survives the primary persona's access level
**Priority**: MUST

**Given** a user in `sales_team.group_sale_salesman` who holds **neither** `account.group_account_invoice` nor `account.group_account_readonly`
**When** they open a Sale Order for an approaching-limit customer **and** for an over-limit customer
**Then** both banners render in full with all values, and the form opens without an AccessError, because the compute runs under `.sudo()`

**Verification**:
- [ ] Integration: both tiers produce full messages for a Sales-only user (mirrors core's `test_credit_limit_access`, `addons/sale/tests/test_credit_limit.py:344-366`)
- [ ] Integration: core's own `test_credit_limit_access` still passes unmodified

### AC-LIVE-1: Banner tracks the order live, with no save
**Priority**: MUST

**Given** an unsaved quotation for a customer with a credit limit
**When** the rep adds/edits order lines so the projected total crosses 80%, then 100%, then falls back below 80%
**Then** at each round-trip:
- The banner appears / recolours / disappears to match the new tier
- Values in line 2 reflect the current order total
- **No save or confirmation is required at any point**
- The S1→S2 transition changes colour and wording without changing the banner's height

**Verification**:
- [ ] E2E: walk none → yellow → red → yellow → none by editing line quantities only
- [ ] E2E: assert correct class, role, and values at each step
- [ ] E2E: assert banner element height is unchanged across the yellow→red transition

### AC-NAV-1: Banner retires on confirmation
**Priority**: SHOULD

**Given** an over-limit quotation showing the red banner
**When** the rep clicks Confirm (which the banner must **not** block)
**Then** the order confirms successfully and the banner is absent from the confirmed (`state == 'sale'`) form

**Verification**:
- [ ] E2E: `action_confirm` succeeds with an over-limit banner present (non-blocking guarantee)
- [ ] E2E: banner absent post-confirmation

### AC-A11Y-1: Severity is conveyed without colour
**Priority**: SHOULD

**Given** a user who cannot perceive the alert colours
**When** either tier renders
**Then** the tier is unambiguous from the text alone ("is approaching" vs. "has reached") and from the ARIA role (`status` vs. `alert`)

**Verification**:
- [ ] E2E: assert the distinguishing verb phrase per tier
- [ ] E2E: assert `role` attribute per tier
- [ ] axe-core: no new critical/serious violations introduced on the Sale Order form

---

## Test Scenarios (Derived from Acceptance Criteria)

### Happy Path Tests
1. AC-ENTRY-1 — banner in the correct slot, above the fold, no navigation
2. AC-HAPPY-1 — red tier: class, role, all data points, trigger parity with core
3. AC-HAPPY-2 — yellow tier: class, role, all data points, `% of limit`, 80% and 100% boundaries

### Error Scenario Tests
1. AC-HAPPY-3 — all four suppression conditions produce an absent node
2. AC-ERROR-1 — Sales-only user sees both tiers; core's access test unregressed

### Edge Case Tests
1. AC-LIVE-1 — full live threshold walk with no save; zero-reflow on yellow→red
2. AC-NAV-1 — confirmation is never blocked; banner retires with the draft state
3. AC-A11Y-1 — tier legible without colour

## Accessibility Checklist

- [ ] Severity conveyed by text and ARIA role, never by colour alone
- [ ] Approaching tier uses `role="status"` (polite) so live recomputes don't interrupt screen-reader users on every line edit
- [ ] Over-limit tier retains `role="alert"` (assertive), matching today's behaviour
- [ ] Banner is plain text — no focusable controls, so it never enters or disturbs the keyboard tab order through the order-line editor
- [ ] Banner insertion/removal does not steal focus from the field being edited
- [ ] Alert colour contrast meets Bootstrap/Odoo's existing `alert-warning` / `alert-danger` tokens (inherited, not newly defined)
- [ ] No time limits, no auto-dismiss

## Analytics & Observability

Odoo ships no product-analytics layer and this fork's productBrief lists no metrics targets, so no instrumentation is added. Observability for this journey is behavioural and is asserted by tests rather than telemetry:

| Signal | Purpose | Where observed |
|--------|---------|----------------|
| Tier boundary correctness | The whole feature | Integration tests across the boundary matrix |
| Trigger parity with core | No regression for existing users | Core's `test_credit_limit.py` suite must pass unmodified |
| Live-update latency | Journey feels instant | Inherited from the existing onchange round-trip; no new I/O beyond two partner field reads |

## Validation Checklist

- [x] Journey delivers the stated value (rep makes a credit-aware decision before confirming)
- [x] Primary persona can complete it **without** Accounting access (AC-ERROR-1)
- [x] Every state is reachable and reversible; no dead ends
- [x] Live/async behaviour fully specified, including reflow and screen-reader politeness
- [x] Consistent with the three sibling alert divs already in the same region
- [x] Accessible: severity redundantly encoded; live-region politeness matched to severity
- [x] Every state has a concrete test scenario

## Findings for the Architecture Phase

Three grounded observations this journey design surfaced that the Architecture lane should absorb:

1. **`with_company` is a discarded no-op in core.** `addons/sale/models/sale_order.py:772` reads `order.with_company(order.company_id)` on its own statement — the returned recordset is never assigned or used. Since `credit_limit` is company-dependent (`addons/account/models/partner.py:524-527`), a multi-company user whose active company differs from `order.company_id` can have the wrong company's limit evaluated. The new compute should apply it properly, e.g. `order.sudo().with_company(order.company_id)`, and carry a test for it.

2. **The state gate is narrower than AC-ENTRY-1 as written.** Core gates on `state in ('draft','sent')`, so the banner is absent on confirmed and locked orders. The journey **preserves and endorses** this (warn while the rep can still act; retire once committed), but AC-ENTRY-1's phrase "new quotation or existing order" should be read as scoped to draft/sent. AC-NAV-1 above encodes the confirmed-state behaviour explicitly.

3. **The field is rendered in two views, not one.** `partner_credit_warning` also renders at `addons/account/views/account_move_views.xml:840-841`. Any approach that changes the **value** of that shared field (rather than adding a `sale.order`-scoped severity + message) will change the Invoicing banner's text too — the explicit scope boundary this task set. This is a strong argument for the sale-order-scoped compute path over modifying `_build_credit_warning_message` in place, and it is the Architecture lane's call to make.

## Next Steps

1. **Architecture lane** resolves the extend-vs-parallel question (Creative Q1) with the three Findings above as input, and pins the severity-exposure mechanic (computed Selection + dynamic class vs. two equal-height sibling divs).
2. **Phase 1 build** implements the threshold semantics table and the copy specification as a non-stored compute on an `_inherit`ed `sale.order`, with the boundary-matrix tests.
3. **Phase 2 build** implements the view `_inherit`, holding the equal-height / zero-reflow and ARIA-role split constraints, plus the AC-ERROR-1 access-parity guard.
4. **Phase 3 build / UAT** walks AC-LIVE-1 — the none → yellow → red → yellow → none live traversal with no save — as the journey's headline end-to-end proof.
