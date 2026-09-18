# Architecture Decision: Two-Tier Customer Credit Limit Warning (Sale Order)

**Created**: 2026-09-18
**Status**: DECIDED
**Decision Type**: Architecture
**Task**: `customer-credit-limit-warning`
**Feature**: `customer-credit-limit-warning`
**Complexity**: Level 3

---

## Context

### System Requirements

- **R1** — The Sale Order form displays a computed text banner about the customer's credit standing.
- **R2** — Two visual tiers: **yellow** when the customer is at/above 80% of the credit limit ("approaching"), **red** when above 100% ("over").
- **R3** — The banner content includes: the **credit limit**, the **current outstanding receivables**, and **this order's contribution**.
- **R4** — The banner is **empty/hidden** when no credit limit is set, when the company-level feature gate is off, or when the customer is comfortably within the limit (< 80%).
- **R5** (AC-ERROR-1, non-negotiable) — The banner MUST remain visible to Sales users who do **not** hold `account.group_account_invoice` / `account.group_account_readonly`. The `.sudo()` elevation pattern core already relies on (`addons/sale/models/sale_order.py:779`) must be preserved or equivalently replaced.
- **R6** — Multi-currency correctness: the order's own amount must be normalised to company currency before comparison, exactly as core does (`amount_total / currency_rate`).
- **R7** — Multi-company correctness: `res.partner.credit_limit` is `company_dependent`; figures must be read in the order's company context.
- **R8** — Out of scope: the Invoicing (`account.move`) banner must retain its existing binary behaviour.

### Technical Constraints

- **C1 — Odoo core already implements ~70% of this feature.** Verified in this checkout:

  | Concern | Location |
  |---|---|
  | Field | `addons/sale/models/sale_order.py:299-300` — `partner_credit_warning = fields.Text(compute='_compute_partner_credit_warning')`, **non-stored** |
  | Compute | `addons/sale/models/sale_order.py:770-781` — gated on `state in ('draft','sent')` **and** `company_id.account_use_credit_limit`; calls `order.sudo()` at line 779 |
  | Message builder (**SHARED**) | `addons/account/models/account_move.py:1846-1888` — `_build_credit_warning_message(record, current_amount, exclude_current, exclude_amount)` |
  | Invoicing consumer | `addons/account/models/account_move.py:704-705, 1825-1839`; view `addons/account/views/account_move_views.xml:839-842` |
  | Sale view banner | `addons/sale/views/sale_order_views.xml:301-305` — `<div class="alert alert-warning" role="alert" invisible="partner_credit_warning == ''">` immediately below `</header>` |
  | Company gate | `addons/account/models/company.py:154-155` — `account_use_credit_limit` (Boolean, default off) |
  | Partner data | `addons/account/models/partner.py:517-534` — `credit`, `credit_to_invoice`, `credit_limit` (`company_dependent=True`), all `groups='account.group_account_invoice,account.group_account_readonly'` |
  | Existing tests | `addons/sale/tests/test_credit_limit.py` — `@tagged('post_install', '-at_install')` |

  Core is strictly **binary**: `_build_credit_warning_message` returns `''` unless `total_credit > credit_limit` (line 1863), and the single banner is always `alert-warning`. **There is no 80% tier and no colour differentiation today.**

- **C2 — `_build_credit_warning_message` is shared.** `sale.order._compute_partner_credit_warning` and `account.move._compute_partner_credit_warning` both call it. Any change to it is, by construction, a change to the Invoicing UI.

- **C3 — Guiding Principle: "Inheritance over modification"** (`systemPatterns.md` § Guiding Principles): *"Existing models/views are extended via `_inherit` (never edit another module's file directly)."* Reinforced by `productBrief.md` § Risks: *"Keep Banyan-specific changes in separate addons rather than modifying core; track upstream release notes."* This repo is a fork of upstream Odoo 18.0 **one commit ahead of stock** — every line touched inside `addons/sale/` or `addons/account/` is a future merge conflict.

- **C4 — Core's post-install tests will run against our code.** `test_credit_limit.py` is `@tagged('post_install', ...)`, meaning it executes *after all modules in the database are installed*. If our addon is installed in the same database and it changes the **string value** of `sale.order.partner_credit_warning`, these existing core assertions break:
  - `test_credit_limit_multicurrency` (lines 184-189) — exact-string `assertEqual` on `order.partner_credit_warning`
  - `test_credit_limit_access` (lines 341-367) — builds a `Form(sale.order)` and reads `order_form.partner_credit_warning`; **the field must remain present in the form arch** or the `Form` helper raises.
  - `test_credit_limit_multi_company` — multi-company `credit_to_invoice` behaviour.

  This is a hard architectural constraint, not a nice-to-have. It rules out silently rewriting `partner_credit_warning`'s content.

- **C5 — Odoo form views cannot compute `class` dynamically.** Only `invisible` / `readonly` / `required` / `column_invisible` accept Python expressions. Two colours therefore require **two `<div>` elements with static classes**, each gated by an `invisible` expression on a severity field — not one div with a computed class.

- **C6 — No JS/OWL budget.** This is a server-rendered form-view banner. Introducing an OWL component would pull in `static/src/` assets, an asset-bundle entry, and JS tests for what is fundamentally a computed string plus a CSS class.

- **C7 — No OpenTelemetry anywhere in this codebase.** `requirements.txt` contains no `opentelemetry-*` package; Odoo uses stdlib `logging` (`addons/sale/models/sale_order.py:4,32` — `_logger = logging.getLogger(__name__)`). See § Observability Architecture for the documented deviation.

### Non-Functional Requirements

- **NFR-PERF-1** — The compute runs on **every** onchange round-trip of the Sale Order form (it depends on `amount_total`). It must add **zero new SQL queries** beyond what core already issues; it must reuse the same `partner.credit` / `credit_to_invoice` reads core already performs (which the ORM cache serves once per transaction).
- **NFR-PERF-2** — No new stored column ⇒ no migration, no `_compute` mass-recompute at install on existing Sale Orders. Install must be a pure metadata/view operation.
- **NFR-SEC-1** — Elevation via `.sudo()` must be **narrowly scoped** to reading partner credit figures. It must not leak an elevated recordset into message formatting, writes, or anything a Sales user could pivot from. Credit figures shown are the customer's own AR position on the customer's own order — the disclosure core already makes deliberately (`# ensure access to 'credit' & 'credit_limit' fields`), not a new one.
- **NFR-SEC-2** — No new model ⇒ no new `ir.model.access.csv` rows required (per `systemPatterns.md`, ACLs are mandatory only *per addon touching data*; extending an existing model's fields inherits that model's ACLs and record rules).
- **NFR-MAINT-1 (dominant)** — Upstream-merge safety. `addons/sale/` and `addons/account/` must end the task **byte-identical to upstream**. `git diff upstream/18.0 -- addons/` must be empty for this task.
- **NFR-I18N-1** — All user-facing strings go through `_()` and all monetary values through `formatLang(..., currency_obj=...)`, matching core (`account_move.py:1866-1871`).
- **NFR-CONFIG-1 (12-factor)** — The 80% threshold must be changeable without a code edit.

---

## Component Analysis

### Core Components

| Component | Purpose | Responsibilities |
|-----------|---------|------------------|
| **Threshold config** (`ir.config_parameter`) | Externalise the "approaching" ratio | Supply `0.8` default; allow per-database override without a code change or module upgrade |
| **Credit figures resolver** (`sale.order._get_credit_limit_figures()`) | Single source of truth for the numbers | Apply the company gate + state gate; `.sudo()` + `.with_company()`; resolve `commercial_partner_id`; normalise order amount to company currency; return `credit_limit`, `receivables`, `current_amount`, `total_credit`, `ratio`, `level` |
| **Severity classifier** (inside the resolver) | Map ratio → `none` / `approaching` / `over` | Single `if/elif` on the *one* set of figures — guarantees tiers can never disagree |
| **Detail message composer** (`sale.order._build_credit_limit_detail()`) | Render the tier-appropriate human text | `_()`-wrapped, `formatLang`-formatted breakdown: limit, outstanding receivables, this order's contribution, total |
| **Severity field** (`sale.order.credit_warning_level`, Selection, non-stored) | Thread severity into the view | The only thing the XML `invisible` expressions key off |
| **Detail field** (`sale.order.credit_limit_detail`, Text, non-stored) | Thread the breakdown text into the view | Rendered by both banner divs |
| **View extension** (`ir.ui.view` inheriting `sale.view_order_form`) | Two-tier presentation | Re-target core's div to the `over` tier + restyle to `alert-danger`; insert a sibling `alert-warning` div for the `approaching` tier |
| **Core message** (`partner_credit_warning`) — *untouched* | Headline for the `over` tier | Left byte-identical; keeps core's post-install tests green and keeps the `Form()` contract intact |

### Component Interactions

```
                     ir.config_parameter
                'sale_credit_limit_warning.approaching_ratio' (default 0.8)
                                 |
                                 v
  sale.order (draft/sent) --> _get_credit_limit_figures()
        |                          |  .sudo().with_company(company_id)
        |                          |  -> res.partner (commercial_partner_id)
        |                          |       credit, credit_to_invoice, credit_limit
        |                          |  -> amount_total / currency_rate  (company currency)
        |                          v
        |                    {limit, receivables, current_amount, total, ratio, level}
        |                          |
        |            +-------------+--------------+
        |            v                            v
        |   credit_warning_level          _build_credit_limit_detail()
        |   ('none'|'approaching'|'over')          |
        |            |                             v
        |            |                     credit_limit_detail (Text)
        |            |                             |
        +--> partner_credit_warning  <-- CORE, UNMODIFIED (headline, over tier only)
                     |                             |
                     v                             v
        =================== sale.view_order_form (inherited) ===================
          div.alert.alert-danger   invisible="credit_warning_level != 'over'"
              <field partner_credit_warning/>   <field credit_limit_detail/>
          div.alert.alert-warning  invisible="credit_warning_level != 'approaching'"
              <field credit_limit_detail/>
        ========================================================================

  account.move  -- NOT IN THE GRAPH. No _inherit, no field, no view extension. --
```

**Key interaction property**: `credit_warning_level` and `credit_limit_detail` are produced by **one** compute method reading **one** figures dict. They cannot drift apart. `partner_credit_warning` remains produced entirely by core.

---

## Options Explored

### Option 1: Extend `_build_credit_warning_message()` in place (spec option **a**)

- **Description**: Add a `severity` / `threshold_ratio` parameter to `addons/account/models/account_move.py:1846`, changing the early-return at line 1863 from `total_credit <= credit_limit` to a ratio test, and returning a severity alongside the message. Edit `addons/sale/models/sale_order.py` and `addons/sale/views/sale_order_views.xml` to consume it.
- **Architecture Diagram**:
  ```
  [EDIT] addons/account/models/account_move.py::_build_credit_warning_message(+severity)
              |                                    |
              v                                    v
  [EDIT] sale.order._compute_...          account.move._compute_...  <-- INVOICING
              |                                    |
              v                                    v
  [EDIT] sale_order_views.xml            account_move_views.xml  <-- INVOICING UI
  ```
- **Pros**:
  - Smallest line count; no new module to install, name, or document.
  - Zero duplication of the currency/company normalisation logic.
  - Both Sales and Invoicing would get the two-tier behaviour "for free" *if that were wanted*.
- **Cons**:
  - **Directly violates the repo's stated Guiding Principle** ("never edit another module's file directly") and `productBrief.md`'s stated upstream-merge risk mitigation.
  - **Blast radius into Invoicing is unavoidable.** The method is the shared one (C2); changing its return contract changes `account.move.partner_credit_warning` for every invoice in the system. R8 is violated by construction — the only containment is a caller-supplied default, which is an opt-out rather than an isolation boundary.
  - Creates a permanent merge conflict in two of the most actively-changed files in Odoo (`account_move.py` is ~1900+ lines of hot upstream code).
  - Breaks core's own post-install assertions (C4) with no clean remedy other than editing core's test file too — compounding the divergence.
  - The change is invisible to `Settings > Apps`: an operator cannot see, disable, or uninstall it.
- **Technical Fit**: **Low** — contradicts the primary architectural principle of the codebase.
- **Complexity**: **Low** (to write) / **High** (to live with).
- **Scalability**: **Low** — every future upstream bump re-litigates the conflict.

### Option 2: Parallel `sale.order`-only compute, written into `addons/sale/` (spec option **b**)

- **Description**: Leave `_build_credit_warning_message()` alone. Add a second compute + severity field **inside `addons/sale/models/sale_order.py`**, and a second banner div inside `addons/sale/views/sale_order_views.xml`.
- **Pros**:
  - Invoicing is genuinely untouched — `account.move` never sees the new logic (fixes Option 1's worst flaw).
  - Independent message composition; free to include the receivables/contribution breakdown.
- **Cons**:
  - **Still edits another module's files** — the Guiding Principle violation and the upstream-merge conflict persist, merely relocated from `account/` to `sale/`.
  - Still not visible/installable/uninstallable as a unit in `Settings > Apps`.
  - Still breaks core's post-install assertions if it touches `partner_credit_warning`'s value (C4), because the test file lives in the same module and is maintained upstream.
  - Duplicates the currency/company normalisation inside a file that also contains the original — two copies, same file, guaranteed to diverge on the next upstream refactor with no module boundary to signal the coupling.
- **Technical Fit**: **Low-Medium** — right scoping instinct, wrong deployment unit.
- **Complexity**: **Medium**.
- **Scalability**: **Low-Medium**.

### Option 3 (RECOMMENDED): New addon `sale_credit_limit_warning`, additive fields, view re-target (spec option **c**, refined)

- **Description**: A new self-contained module under `addons/sale_credit_limit_warning/` that `_inherit = 'sale.order'` to **add** two non-stored fields (`credit_warning_level`, `credit_limit_detail`) and one `ir.ui.view` inheriting `sale.view_order_form`. **It does not override `_compute_partner_credit_warning` and does not change the value of any core field.** `addons/sale/` and `addons/account/` end byte-identical to upstream.
- **Architecture Diagram**:
  ```
  addons/sale_credit_limit_warning/          (NEW — the only files this task writes)
    __init__.py
    __manifest__.py                  depends: ['sale']   (account arrives transitively)
    data/ir_config_parameter.xml     approaching_ratio = 0.8
    models/__init__.py
    models/sale_order.py             _inherit = 'sale.order'
                                       + credit_warning_level   (Selection, compute, non-stored)
                                       + credit_limit_detail    (Text,      compute, non-stored)
                                       + _get_credit_limit_figures()
                                       + _build_credit_limit_detail()
                                       + _get_credit_warning_ratio()
    views/sale_order_views.xml       inherit_id="sale.view_order_form"
    tests/__init__.py
    tests/test_two_tier_credit_limit.py

  addons/sale/     ........ UNCHANGED (0 lines)
  addons/account/  ........ UNCHANGED (0 lines)
  ```
- **Pros**:
  - **Satisfies the Guiding Principle exactly** — `_inherit` on the model, `inherit_id` + `xpath` on the view, no core file edited.
  - **Invoicing isolation is structural, not conventional.** The module declares no `_inherit = 'account.move'` and no view inheriting `account.view_move_form`. Two-tier behaviour *cannot* reach Invoicing; there is no code path. This is enforced by a guardrail test (see § Implementation Guidelines #9).
  - **Core's post-install tests stay green without modification** — `partner_credit_warning` keeps its exact upstream value and stays present in the form arch, so `test_credit_limit_multicurrency`, `test_credit_limit_multi_company` and `test_credit_limit_access` all pass unmodified.
  - Upstream bumps merge cleanly; the module is independently versionable and appears in `Settings > Apps` as an installable/uninstallable unit.
  - Aligns with the 621-addon precedent in this repo — `addons/sale_margin/` is the canonical shape (separate addon, `_inherit = "sale.order"`, `inherit_id ref="sale.view_order_form"`, `xpath expr="//field[@name='...']"`).
  - Reuses core's *data* (`partner.credit`, `credit_to_invoice`, `credit_limit`, `amount_total / currency_rate`) so multi-currency/multi-company semantics are inherited, not re-derived.
- **Cons**:
  - Largest file count (≈8 small files vs. a handful of edited lines).
  - The `over`-tier headline sentence remains core's wording ("*X has reached its credit limit of: …*") because rewriting it would break core's exact-string assertions. The two tiers therefore have slightly different phrasing registers. **Accepted and documented**; escape hatch in § Trade-offs.
  - `credit_limit_detail` is rendered by two `<field>` nodes in one form arch (unavoidable given C5). Legal in Odoo and used elsewhere in core views, but a mild smell.
  - A thin amount of arithmetic (ratio, receivables sum) exists in both `_get_credit_limit_figures()` and `_build_credit_warning_message()`. Mitigated by reusing core's *inputs* verbatim and by a parity test (§ Implementation Guidelines #8).
- **Technical Fit**: **High**.
- **Complexity**: **Medium** (mostly boilerplate; the logic is ~60 lines).
- **Scalability**: **High**.

### Option 4: New addon, but overriding `_compute_partner_credit_warning` (considered, rejected)

- **Description**: Same module shell as Option 3, but `super()`-then-rewrite `partner_credit_warning` so the *whole* message (both tiers) is ours and both banners render a single field.
- **Pros**: One field instead of two; fully-controlled wording on both tiers; no duplicate `<field>` node.
- **Cons**:
  - **Breaks C4.** `test_credit_limit_multicurrency` (`addons/sale/tests/test_credit_limit.py:184-189`) does an exact-string `assertEqual`. Because it is `post_install`, installing our module in any database that also runs core's test suite turns a green suite red — in a *core* module we do not own. Fixing that means editing `addons/sale/tests/`, re-introducing the Option 1/2 divergence through the back door.
  - Re-declaring `@api.depends` on the override silently takes ownership of core's dependency list; a future upstream change to that list would be silently dropped.
- **Technical Fit**: **Medium**. **Complexity**: Medium. **Scalability**: **Low-Medium** (breaks on upstream test churn).
- **Verdict**: Rejected. The single-field elegance is not worth owning a core test file.

### Option 5: OWL client-side severity component (considered, rejected early)

- **Description**: Keep one server field; compute the tier in JS and swap the Bootstrap class client-side.
- **Cons**: Duplicates threshold logic into JS (two sources of truth for a *financial* threshold); needs an asset bundle entry + JS tests; the figures are already server-side and `sudo()`-gated, so shipping them to the client to re-classify adds a disclosure surface for no benefit; violates C6.
- **Verdict**: Rejected.

---

## Evaluation Matrix

Scale: 5 = best.

| Criteria | Opt 1 (edit shared) | Opt 2 (edit `sale/`) | **Opt 3 (new addon, additive)** | Opt 4 (new addon, override) | Opt 5 (OWL) |
|----------|:---:|:---:|:---:|:---:|:---:|
| Guiding-principle compliance (`_inherit` over modification) | 1 | 1 | **5** | 5 | 4 |
| Upstream-merge safety (NFR-MAINT-1) | 1 | 2 | **5** | 5 | 4 |
| Invoicing blast-radius containment (R8) | 1 | 4 | **5** | 5 | 4 |
| Core test suite stays green unmodified (C4) | 1 | 2 | **5** | 1 | 4 |
| Scalability / future extensibility | 2 | 2 | **5** | 4 | 3 |
| Maintainability | 2 | 2 | **4** | 4 | 2 |
| Performance (NFR-PERF-1/2) | 5 | 5 | **5** | 5 | 4 |
| Security (`sudo` scoping, NFR-SEC-1) | 4 | 4 | **5** | 5 | 2 |
| Observability / debuggability | 3 | 3 | **4** | 3 | 2 |
| Implementation cost (5 = cheapest) | 5 | 4 | **3** | 4 | 1 |
| Message-wording freedom | 5 | 5 | **3** | 5 | 5 |
| **Weighted verdict** | **Reject** | **Reject** | **SELECT** | Runner-up | Reject |

---

## Observability Architecture

### Documented deviation from `observability-requirements.md`

`observability-requirements.md` mandates OpenTelemetry traces/metrics/logs with W3C Trace Context propagation. **This feature crosses no service boundary and this codebase has no OTEL installation.** Specifically:

- `requirements.txt` contains **no** `opentelemetry-*` package (C7). Introducing the OTEL SDK as a dependency of a computed-banner addon would violate *"Modules are the unit of deployment"* and *"Explicit dependency graph"*, and would place a cross-cutting telemetry concern inside a single business addon — the wrong layer by any reading.
- The feature adds **no HTTP client call, no queue publish, no cron job, no controller route**. It is an ORM compute executed inside an existing JSON-RPC `onchange`/`read` request that Odoo's own `odoo/http.py` dispatcher already owns end to end. There is no new boundary at which to inject or extract `traceparent`.

**Therefore**: this architecture complies with the *intent* of the standard (diagnosable behaviour, configurable verbosity, no secrets in logs) using the codebase's existing mechanism, and explicitly defers OTEL adoption to a platform-level task that instruments `odoo/http.py` / `odoo/service/server.py` once for all 621 addons. That is the correct seam; this task is not it.

### Logging

- **Library**: stdlib `logging`, per Odoo convention — `_logger = logging.getLogger(__name__)` at module top (mirrors `addons/sale/models/sale_order.py:4,32`).
- **Format / output / level**: governed by Odoo's own server configuration (`docker/odoo.conf`; CLI `--log-level`, `--log-handler`, `--logfile`) — i.e. **configuration over code**, already satisfied at the platform layer. No log level or destination is hardcoded in this module.
- **Emissions** (deliberately minimal — this compute runs on every onchange; anything above `debug` would be a log-flood):

  | Level | Event | Fields |
  |---|---|---|
  | `debug` | Tier classified as non-`none` | `order.id`, `company.id`, `level`, `ratio` (rounded), `threshold` |
  | `warning` | `ir.config_parameter` ratio is unparseable or outside `(0, 1]` → falling back to `0.8` | raw parameter value, fallback used |

- **Never logged** (NFR-SEC / § 3.3 of the standard): `credit_limit`, `credit`, `credit_to_invoice`, `amount_total`, partner name or ID. These are **customer financial PII**; the tier and the ratio are sufficient to debug a classification bug without emitting the customer's AR position into the server log. This is a deliberate strengthening of the standard's PII clause for this feature.

### Distributed Tracing

- **Applicable boundaries**: none introduced by this feature. Correlation, when needed, is via Odoo's existing per-request logging context.

  | From | To | Protocol | Propagation |
  |---|---|---|---|
  | Web client (OWL form view) | Odoo server | JSON-RPC over HTTP | Handled by `odoo/http.py`; **unchanged by this feature** |
  | `sale.order` compute | PostgreSQL | psycopg2 | In-process, same transaction; no new queries beyond core's cached partner read |

- **Deferred**: repo-wide OTEL instrumentation at `odoo/http.py` (server span per request) and `odoo/sql_db.py` (DB spans). Tracked as a separate platform concern, not a blocker for this task.

### Metrics

- **Standard HTTP metrics** (`http_requests_total`, `http_request_duration_seconds`): not emitted by this addon; they belong to the platform-level instrumentation deferred above.
- **Custom business metrics**: **none in v1.** A meaningful `sale_credit_limit_warnings_total{level}` counter requires a metrics registry that does not exist in this codebase. Naming is pre-agreed for when one does:
  - `sale_credit_limit_warnings_total{level="approaching|over"}` — Counter. Labels are a bounded 2-value enum, satisfying § 6.3 cardinality limits. **Never** labelled by `partner_id`, `order_id` or `company_id`.
- **Interim observability substitute**: the tier is derivable at any time from data via an `ir.actions.act_window` domain / `_read_group` over `sale.order` — no counter needed to answer "how many orders are in each tier right now".

### Configuration Variables

Odoo is **config-file driven**, not env-var driven (`techContext.md`: *"the only env var used directly is `PYTHONDONTWRITEBYTECODE=1`"*). The mapping to the standard's variables is therefore:

| Standard variable | This system's equivalent | Default |
|---|---|---|
| `LOG_LEVEL` | `log_level` in `docker/odoo.conf` / `--log-level` | `info` |
| `LOG_FORMAT` | Odoo server log formatter (fixed) | text |
| `LOG_OUTPUT` / `LOG_FILE_PATH` | `logfile` in `docker/odoo.conf` / `--logfile` | stdout |
| `OTEL_*` | **N/A** — see deviation above | — |
| *(feature-specific)* `sale_credit_limit_warning.approaching_ratio` | `ir.config_parameter`, editable in *Settings > Technical > System Parameters* | `0.8` |

The threshold as an `ir.config_parameter` is what satisfies **NFR-CONFIG-1 / 12-factor "config in environment"** for this feature: the value is externalised from code, changeable per database at runtime with no code edit, no module upgrade and no restart, and is validated fail-soft (out-of-range → `warning` log + documented `0.8` fallback, never a silent wrong threshold).

---

## Decision

**Chosen: Option 3 — a new addon `sale_credit_limit_warning` that adds two non-stored fields via `_inherit = 'sale.order'` and re-targets the existing banner via `inherit_id` + `xpath`, leaving `addons/sale/` and `addons/account/` byte-identical to upstream.**

### Concrete shape

#### Module skeleton

```
addons/sale_credit_limit_warning/
  __init__.py                       from . import models
  __manifest__.py
  data/ir_config_parameter.xml
  models/__init__.py                from . import sale_order
  models/sale_order.py
  views/sale_order_views.xml
  tests/__init__.py
  tests/test_two_tier_credit_limit.py
```

#### `__manifest__.py`

```python
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales Credit Limit Warning (Two-Tier)",
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Two-tier (approaching / exceeded) customer credit limit banner on Sales Orders",
    'description': """
Adds an 'approaching credit limit' tier to the Sales Order credit warning.

Odoo core shows a single yellow banner only once a customer has already
exceeded its credit limit. This module adds a second, earlier tier and
differentiates the two visually:

  * yellow  - the customer is at or above 80% of its credit limit
  * red     - the customer is over 100% of its credit limit

Both banners break the figure down into the credit limit, the outstanding
receivables and the current order's contribution.

The 80% threshold is configurable via the system parameter
'sale_credit_limit_warning.approaching_ratio'.

This module never modifies the Invoicing (account.move) credit warning.
    """,
    'depends': ['sale'],          # 'account' arrives transitively via sale -> account_payment -> account
    'data': [
        'data/ir_config_parameter.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,        # deliberate: must be an explicit operator choice (see Trade-offs)
    'license': 'LGPL-3',
}
```

*No `security/ir.model.access.csv`*: the module defines no new model, so it inherits `sale.order`'s existing ACLs and record rules (NFR-SEC-2). `auto_install: False` is deliberate — it keeps core's post-install suite runnable in a database without this module, and makes the behaviour change an explicit operator decision.

#### Model extension — `models/sale_order.py`

- **`_inherit` target**: `'sale.order'`
- **New fields** (both **non-stored**, resolving open question 4 — no schema change, no migration):

  ```python
  credit_warning_level = fields.Selection(
      selection=[('none', "None"), ('approaching', "Approaching"), ('over', "Over")],
      compute='_compute_credit_limit_warning_tier',
      default='none',
  )
  credit_limit_detail = fields.Text(compute='_compute_credit_limit_warning_tier')
  ```

- **One compute for both fields** — this is what makes severity and text structurally unable to disagree:

  ```python
  @api.depends('company_id', 'partner_id', 'amount_total', 'currency_rate', 'state')
  def _compute_credit_limit_warning_tier(self):
      for order in self:
          figures = order._get_credit_limit_figures()
          order.credit_warning_level = figures['level']
          order.credit_limit_detail = (
              order._build_credit_limit_detail(figures) if figures['level'] != 'none' else ''
          )
  ```

  Note this is a **new** method name — core's `_compute_partner_credit_warning` is *not* overridden (that is exactly what distinguishes this from rejected Option 4). Note also that `'state'` is included in `@api.depends`, which core's own decorator omits (`sale_order.py:770`) despite reading `order.state` at line 775 — a latent core staleness bug we neither inherit nor propagate.

- **Figures resolver** — the single source of truth:

  ```python
  def _get_credit_limit_figures(self):
      """Return the credit figures for this order, in COMPANY currency.

      All partner credit fields are restricted to account.group_account_invoice /
      account.group_account_readonly, so this reads them sudo'd - mirroring
      addons/sale/models/sale_order.py:779 - to keep the banner visible to
      Sales users without Accounting access (AC-ERROR-1).
      """
      self.ensure_one()
      empty = {'credit_limit': 0.0, 'receivables': 0.0, 'current_amount': 0.0,
               'total_credit': 0.0, 'ratio': 0.0, 'level': 'none'}
      if self.state not in ('draft', 'sent') or not self.company_id.account_use_credit_limit:
          return empty
      # sudo() -> read protected credit fields; with_company() -> credit_limit is company_dependent
      order = self.sudo().with_company(self.company_id)
      partner = order.partner_id.commercial_partner_id
      credit_limit = partner.credit_limit
      if not credit_limit:
          return empty
      receivables = partner.credit + partner.credit_to_invoice
      current_amount = order.amount_total / (order.currency_rate or 1.0)
      total_credit = receivables + current_amount
      ratio = total_credit / credit_limit
      if total_credit > credit_limit:
          level = 'over'
      elif ratio >= order._get_credit_warning_ratio():
          level = 'approaching'
      else:
          level = 'none'
      return {'credit_limit': credit_limit, 'receivables': receivables,
              'current_amount': current_amount, 'total_credit': total_credit,
              'ratio': ratio, 'level': level}
  ```

  Three correctness points, each deliberately mirroring core:
  1. `commercial_partner_id` — matches `_build_credit_warning_message` line 1861, so child/invoice contacts roll up to the company partner (covered by core's `test_commercial_partner_credit`).
  2. `amount_total / currency_rate` — matches `sale_order.py:780`, the exact multi-currency normalisation core's `test_credit_limit_multicurrency` proves.
  3. `.with_company(self.company_id)` — **applied correctly**, unlike core's `sale_order.py:773` where `order.with_company(order.company_id)` is called but its return value is discarded, so the `company_dependent` `credit_limit` is read in the *environment's* company rather than the order's. Fixing this inside our own module is safe (it cannot change `partner_credit_warning`) and is a genuine multi-company correctness improvement.

- **Threshold accessor** (fail-soft, NFR-CONFIG-1):

  ```python
  DEFAULT_APPROACHING_RATIO = 0.8

  def _get_credit_warning_ratio(self):
      raw = self.env['ir.config_parameter'].sudo().get_param(
          'sale_credit_limit_warning.approaching_ratio', DEFAULT_APPROACHING_RATIO)
      try:
          ratio = float(raw)
      except (TypeError, ValueError):
          ratio = 0.0
      if not 0.0 < ratio <= 1.0:
          _logger.warning(
              "Invalid sale_credit_limit_warning.approaching_ratio %r; falling back to %s",
              raw, DEFAULT_APPROACHING_RATIO)
          return DEFAULT_APPROACHING_RATIO
      return ratio
  ```

- **Detail composer** (`_()` + `formatLang`, per NFR-I18N-1 and core's pattern at `account_move.py:1866-1871`):

  ```python
  def _build_credit_limit_detail(self, figures):
      self.ensure_one()
      currency = self.company_id.currency_id
      fmt = lambda v: formatLang(self.env, v, currency_obj=currency)
      lines = []
      if figures['level'] == 'approaching':
          lines.append(_(
              "%(partner_name)s is approaching its credit limit of %(credit_limit)s "
              "(%(ratio)s%% used).",
              partner_name=self.partner_id.commercial_partner_id.name,
              credit_limit=fmt(figures['credit_limit']),
              ratio=round(figures['ratio'] * 100),
          ))
      lines.append(_("Outstanding receivables: %(amount)s", amount=fmt(figures['receivables'])))
      lines.append(_("This order: %(amount)s", amount=fmt(figures['current_amount'])))
      if figures['level'] == 'approaching':
          lines.append(_("Total amount due: %(amount)s", amount=fmt(figures['total_credit'])))
      return "\n".join(lines)
  ```

  For the `over` tier the headline and the total are already supplied by core's `partner_credit_warning` rendered in the same div, so the detail contributes only the two breakdown lines — no duplication on screen, and **R3 (limit + receivables + this order's contribution) is satisfied on both tiers**.

#### View extension — `views/sale_order_views.xml`

Following the `addons/sale_margin/views/sale_order_views.xml` precedent exactly (separate addon, `inherit_id` + `xpath` on a field node):

```xml
<record id="view_order_form_two_tier_credit_warning" model="ir.ui.view">
    <field name="name">sale.order.form.two.tier.credit.warning</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">

        <!-- (1) Re-target core's banner to the OVER tier and restyle it red.
             xpath anchors on the field node's parent because the div at
             addons/sale/views/sale_order_views.xml:301 carries no name/id. -->
        <xpath expr="//field[@name='partner_credit_warning']/.." position="attributes">
            <attribute name="class">alert alert-danger</attribute>
            <attribute name="invisible">credit_warning_level != 'over'</attribute>
        </xpath>

        <!-- (2) Add the breakdown inside that same red banner. -->
        <xpath expr="//field[@name='partner_credit_warning']" position="after">
            <field name="credit_limit_detail" nolabel="1"/>
        </xpath>

        <!-- (3) Sibling yellow banner for the APPROACHING tier. -->
        <xpath expr="//field[@name='partner_credit_warning']/.." position="after">
            <div class="alert alert-warning" role="alert"
                 invisible="credit_warning_level != 'approaching'">
                <field name="credit_warning_level" invisible="1"/>
                <field name="credit_limit_detail" nolabel="1"/>
            </div>
        </xpath>

    </field>
</record>
```

**Anchor rationale**: `//field[@name='partner_credit_warning']/..` is used rather than a class-based expression (`//div[@class='alert alert-warning']`) because `alert alert-warning` is **not unique** in that form — `sale_order_views.xml` has at least three sibling `alert-warning` divs (archived products at :306, duplicate order at :310). Anchoring on the unique field node is the only stable choice, and it is the same technique `sale_margin` uses.

**Why core's div is re-targeted rather than replaced**: `position="replace"` would remove the `partner_credit_warning` field node from the arch, and core's `test_credit_limit_access` (`test_credit_limit.py:352-367`) drives a `Form(sale.order)` and reads `order_form.partner_credit_warning` — the `Form` helper only exposes fields present in the view. Re-targeting keeps that contract intact **and** keeps the AC-ERROR-1 no-accounting-access test meaningful for our banner too, since our fields ride the same form.

#### Severity threading, end to end

`ir.config_parameter` → `_get_credit_warning_ratio()` → `_get_credit_limit_figures()['level']` → `credit_warning_level` (Selection) → the two `invisible="credit_warning_level != '<tier>'"` expressions → exactly one of `alert-danger` / `alert-warning` / nothing renders. The severity crosses the Python→XML boundary **once**, as a three-valued enum on a single field. There is no second place where a threshold is evaluated.

### Rationale

1. **The Guiding Principle is decisive, not advisory.** `systemPatterns.md` states *"Existing models/views are extended via `_inherit` (never edit another module's file directly)."* `productBrief.md` independently ranks *"Diverging from upstream Odoo makes future upstream security/version updates harder to merge"* as a Medium-likelihood / **High-impact** risk whose stated mitigation is verbatim *"Keep Banyan-specific changes in separate addons rather than modifying core."* Options 1 and 2 both require editing core module files. In a repo that is **one commit ahead of stock Odoo 18.0**, permanently forking two of upstream's hottest files to add a colour tier is a bad trade at any diff size. **No deviation from any Guiding Principle is required by this decision.**

2. **The 70%-already-built finding argues *for* a separate addon, not against one.** Because core already computes and displays the >100% case correctly — with proven multi-currency, multi-company and no-accounting-access test coverage — the residual work is genuinely additive: one earlier threshold, one extra colour, one richer breakdown. Additive work maps precisely onto Odoo's additive extension mechanism. Rewriting the shared builder to bolt a tier onto it inverts the cost/benefit: it is the smaller diff but the larger commitment.

3. **Invoicing isolation must be structural, not a convention.** Option 1 contains Invoicing leakage only by a default argument value — one future caller, one refactor, and Invoicing changes. Option 3 contains it because **no code path exists**: the module declares no `account.move` inheritance and no `account.view_move_form` extension. That is an isolation guarantee a reviewer can verify by reading the manifest.

4. **Not touching `partner_credit_warning` is worth two fields.** It is the single property that keeps `addons/sale/tests/test_credit_limit.py` green with zero edits — including the multi-currency exact-string assertion and the `Form()`-driven access test that is the direct evidence for AC-ERROR-1. Owning a core test file to save one field would be a false economy (this is exactly why Option 4 was rejected).

### Answers to the four flagged open questions

**Q1 — Extend vs. build new (the central decision).**
**Build new**, as Option 3: `addons/sale_credit_limit_warning/`, `_inherit = 'sale.order'`, `inherit_id="sale.view_order_form"` with an `xpath` on `//field[@name='partner_credit_warning']/..`. `_build_credit_warning_message()` is **not** modified and **not** overridden; it continues to serve the `over`-tier headline for Sales and the whole message for Invoicing. Option (a) is rejected on Guiding-Principle violation + unavoidable Invoicing blast radius + permanent conflict in `account_move.py`. Option (b) is rejected because it fixes the blast radius but keeps the principle violation and the merge conflict, merely moving them into `sale/`. The "larger diff" cost of (c) is almost entirely module boilerplate (`__init__.py`, manifest, data file) — the business logic is ~60 lines either way, and (c) is the only variant where `git diff` against upstream over `addons/sale/` and `addons/account/` is empty.

**Q2 — Multi-currency / multi-company parity for the new 80% tier.**
**Yes — required, and satisfied by construction rather than by duplication.** `_get_credit_limit_figures()` is the *single* place where currency and company are resolved, and both tiers are classified from its output; the 80% tier therefore cannot use different currency semantics from the 100% tier. It deliberately reuses core's exact inputs — `amount_total / currency_rate` (the normalisation `test_credit_limit_multicurrency` proves) and `partner_id.commercial_partner_id` (matching `account_move.py:1861`, which `test_commercial_partner_credit` proves). Divergence risk from `_build_credit_warning_message()` is contained by **(a)** reusing its inputs verbatim rather than its algorithm, and **(b)** a parity test that asserts, for a given fixture, `figures['total_credit']` formats to the same amount that appears in core's `partner_credit_warning` string, so an upstream change to core's aggregation fails our suite loudly (§ Implementation Guidelines #8). Test coverage mirrors the two proven core cases: a multi-currency 80%-tier test (buck pricelist, rate 2.0 — same fixture shape as `test_credit_limit.py:151-165`) and a multi-company 80%-tier test asserting `credit_limit` is read in the order's company (which also pins the `with_company` correction).

**Q3 — Invoicing scope-creep guardrail.**
**Structurally prevented, and regression-tested.** Three independent barriers: **(i)** the module declares `_inherit = 'sale.order'` only — `credit_warning_level` and `credit_limit_detail` do not exist on `account.move`; **(ii)** the module's only `ir.ui.view` record inherits `sale.view_order_form` — `account.view_move_form` and `addons/account/views/account_move_views.xml:839-842` are untouched, so the Invoicing banner keeps its single `alert alert-warning` class and its `invisible="partner_credit_warning == ''"` condition; **(iii)** `_build_credit_warning_message()` is neither edited nor overridden, so `account.move.partner_credit_warning` is bit-for-bit what it is today. An explicit guardrail test asserts that an invoice for a partner at 85% of limit has `partner_credit_warning == ''` and that `'credit_warning_level' not in self.env['account.move']._fields`. **This is intentional prevention, not intentional allowance** — extending Invoicing later is a separate, deliberately-scoped task (a `account_credit_limit_warning` sibling addon, or a shared mixin promoted at that time).

**Q4 — Data / persistence.**
**No new stored field, no severity column, no schema change.** Both new fields are non-stored computes, matching core's own `partner_credit_warning` (`store` is absent ⇒ `False` at `sale_order.py:299-300`). Justification: the value is a pure function of live data (`partner.credit`, `credit_to_invoice`, `credit_limit`, `amount_total`), it must be correct *during* an unsaved onchange (which a stored field cannot be), and `partner.credit` changes for reasons entirely outside the Sale Order — a stored severity would go stale with no dependable invalidation trigger. Non-stored also means install is a pure metadata/view operation with no mass-recompute over existing Sale Orders (NFR-PERF-2). The only persisted artefact is one `ir.config_parameter` row for the threshold. Security posture is unchanged: no new model ⇒ no new `ir.model.access.csv`; the fields inherit `sale.order`'s existing ACLs and record rules (NFR-SEC-2).

### Trade-offs Accepted

- **Eight new files instead of a ~20-line patch.** Accepted: the file count is boilerplate; what it buys is an empty `git diff` against upstream in `addons/sale/` and `addons/account/`, a unit that appears in `Settings > Apps`, and a clean path for every future upstream bump. Given `productBrief.md` scores upstream divergence as High impact, this is the correct side of the trade.
- **The `over`-tier headline keeps core's wording** ("*X has reached its credit limit of: …*"), so the two tiers read in slightly different registers. Accepted because rewriting it means owning core's exact-string assertions (Option 4). **Escape hatch, if product later demands unified wording**: add `<attribute name="invisible">1</attribute>` to core's field node inside our inherited view and move the full headline into `credit_limit_detail` — a change contained entirely within our module, with no core test impact, because the field stays present in the arch for `Form()`.
- **`credit_limit_detail` is rendered by two `<field>` nodes in one form arch.** Forced by C5 (Odoo cannot compute `class`). Legal and precedented in core views. If a view validator ever objects, the fallback is a single wrapper div with two inner spans carrying the alert classes.
- **Thin arithmetic duplication** (ratio, receivables sum) between `_get_credit_limit_figures()` and `_build_credit_warning_message()`. Accepted as strictly cheaper than the alternative, which is co-owning a method with Invoicing. Contained by the parity test (#8) that fails loudly if core's aggregation changes.
- **A user with `sale.group_sale_salesman` but no Accounting group sees the customer's receivables total.** Accepted: this is precisely the disclosure core already makes deliberately (`sale_order.py:779` — `# ensure access to 'credit' & 'credit_limit' fields`) and is mandated by AC-ERROR-1. The `sudo()` is scoped to reading the figures on the order's own partner; no elevated recordset escapes `_get_credit_limit_figures()`.
- **No OTEL instrumentation.** Deviation from `observability-requirements.md`, documented and justified in § Observability Architecture; the correct seam is a platform-level task on `odoo/http.py`, not a business addon.

---

## Implementation Guidelines

1. **Scaffold** `addons/sale_credit_limit_warning/` with the manifest above. Start every `.py`/`.xml` file with `# Part of Odoo. See LICENSE file for full copyright and licensing details.` (license-header discipline, `systemPatterns.md`).
2. **Guard the boundary from commit one.** After every commit in this task, `git diff --stat -- addons/sale addons/account` MUST be empty. Treat a non-empty result as a build-breaking regression.
3. **Model first, view second.** Implement `_get_credit_warning_ratio()` → `_get_credit_limit_figures()` → `_build_credit_limit_detail()` → `_compute_credit_limit_warning_tier()`, in that order; each is independently testable without the view.
4. **Do not override `_compute_partner_credit_warning`**, and do not assign to `partner_credit_warning` anywhere in this module. This is the single most important invariant; a reviewer should be able to `grep -n "partner_credit_warning" addons/sale_credit_limit_warning/models/` and find only the view file referencing it.
5. **Preserve `.sudo()` (AC-ERROR-1).** `.sudo()` is applied inside `_get_credit_limit_figures()` and the elevated recordset never escapes it — `_build_credit_limit_detail()` receives a plain dict of floats and runs in the user's own environment.
6. **Use `.with_company(self.company_id)` on the sudo'd recordset**, and add a code comment noting this corrects the discarded-result pattern at `addons/sale/models/sale_order.py:773`.
7. **Threshold via `ir.config_parameter`** seeded by `data/ir_config_parameter.xml` (`noupdate="1"` so an operator's edit survives module upgrades), with the fail-soft accessor and its `warning` log.
8. **Parity test (divergence tripwire)**: with a partner over 100%, assert that the amount rendered from `figures['total_credit']` via `formatLang` appears verbatim inside core's `order.partner_credit_warning`. If upstream ever changes how the total is aggregated, this test fails and points at the right place.
9. **Invoicing guardrail test (mandatory)**: partner at 85% of limit → `invoice.partner_credit_warning == ''`; plus `self.assertNotIn('credit_warning_level', self.env['account.move']._fields)`.
10. **Mirror core's test fixtures.** Subclass the same `TestSaleCommon` and reuse the `@tagged('post_install', '-at_install')` convention (`test_credit_limit.py:8-9`), the buck-pricelist multi-currency fixture (lines 19-32) and the `setup_other_company()` multi-company fixture (line 34) so the new tier's coverage is directly comparable to the proven >100% coverage.
11. **Boundary cases to pin explicitly**: exactly 80.0% → `approaching`; exactly 100.0% → `approaching` (core's `over` test is strictly `>`, so equality must not be red — this keeps the two tiers mutually exclusive and jointly exhaustive with no gap); 100.01% → `over`; `credit_limit == 0` → `none`; `account_use_credit_limit == False` → `none`; `state == 'sale'` → `none`.
12. **Never log customer financial figures** — tier and rounded ratio only, at `debug`.
13. **Run**: `python odoo-bin -c docker/odoo.conf -d <db> -i sale_credit_limit_warning --test-enable --test-tags /sale_credit_limit_warning --stop-after-init`, then re-run core's suite with the module installed: `--test-tags /sale` — it must be green with **zero** edits to `addons/sale/tests/`.
14. **Tee all test output** to `.claude-logs/` per the repo's tool-usage rules; do not re-run to re-read output.

---

## Validation Checklist

- [x] Meets all system requirements (R1-R8): two tiers (R2) via `credit_warning_level` + two static-class divs; full breakdown (R3) via `credit_limit_detail` on both tiers; empty states (R4) via the `none` level covering no-limit / gate-off / under-threshold; `sudo()` preserved (R5); `amount_total / currency_rate` (R6); `.with_company()` (R7); Invoicing untouched (R8)
- [x] Respects technical constraints (C1-C7): builds on core's 70% rather than replacing it; never touches the shared builder; obeys "inheritance over modification"; keeps core's post-install tests green; uses two static-class divs rather than a computed class; no JS; no OTEL dependency
- [x] Addresses non-functional requirements: no new queries (NFR-PERF-1), no stored column / no migration (NFR-PERF-2), narrowly-scoped sudo (NFR-SEC-1), no new ACL surface (NFR-SEC-2), empty upstream diff (NFR-MAINT-1), `_()` + `formatLang` (NFR-I18N-1), threshold externalised (NFR-CONFIG-1)
- [x] Technically feasible — `addons/sale_margin/` is a working in-repo precedent for every mechanism used (separate addon, `_inherit = "sale.order"`, `inherit_id ref="sale.view_order_form"`, `xpath expr="//field[@name='…']"`)
- [x] Risks identified and acceptable (see § Risk Assessment)
- [x] **Complies with all Guiding Principles in `systemPatterns.md` — no deviation required.** ORM-only (no raw SQL); module is the unit of deployment; explicit `depends: ['sale']`; **inheritance over modification** (the principle that drove the decision); declarative security (none needed — no new model); convention-based directory shape (`models/ views/ data/ tests/`); transactional `TransactionCase` tests; license header discipline
- [x] Respects established patterns: `post_install` tagging, `*Common` fixture mixins, `Form()` onchange simulation, non-stored computes for live-derived values
- [x] Observability architecture defined (§ Observability Architecture), with the OTEL deviation documented and justified
- [x] Trace context propagation across all service boundaries — **N/A, no new boundary introduced**; documented rather than silently skipped
- [x] Logging strategy consistent with `observability-requirements.md` intent — configurable verbosity at the platform layer, appropriate levels, and a **stricter-than-required** PII rule (no customer financial figures at any level)
- [x] Metrics strategy follows naming conventions — names pre-agreed (`sale_credit_limit_warnings_total{level}`, bounded 2-value label), emission deferred until a registry exists

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| A future upstream change to `_build_credit_warning_message()` alters the `over`-tier headline, desynchronising it from our breakdown lines | M | M | Parity test #8 asserts our total matches the amount in core's string; failure points straight at the drift. Our detail lines are self-describing and remain correct in isolation |
| Upstream renames/moves the `partner_credit_warning` field node, breaking the `xpath` anchor | L | M | Anchor is a field name, the most stable identifier available (the div has no id/name). Failure is loud at module load (`ir.ui.view` validation error), never silent |
| Dev implements the tier by overriding `_compute_partner_credit_warning`, breaking core's post-install suite | M | H | Called out as Guideline #4 and as rejected Option 4; enforced by re-running `--test-tags /sale` with the module installed (Guideline #13) |
| Two-tier behaviour leaks into Invoicing during a later "just reuse it" refactor | L | M | Structural: no `account.move` inheritance exists. Guardrail test #9 fails the moment it does |
| `credit_limit` read in the wrong company yields a wrong tier in multi-company setups | L | H | `.with_company(self.company_id)` applied to the sudo'd recordset (correcting core's discarded-result pattern), pinned by a multi-company test |
| Operator sets an out-of-range `approaching_ratio` (e.g. `80` meaning percent) → banner never fires or always fires | M | M | Fail-soft validation: out of `(0, 1]` → `warning` log + documented `0.8` fallback. Parameter description documents the ratio form |
| `alert-warning` / `alert-danger` colour pair fails a contrast/accessibility check | L | L | Bootstrap-standard classes already used throughout the Odoo backend; colour is not the sole signal — the message text itself distinguishes "approaching" from "reached" |
| Duplicate `<field name="credit_limit_detail">` nodes trigger a view-validation warning in some Odoo build | L | L | Documented fallback: single wrapper div with two inner class-carrying spans |
| Sales-only user sees customer receivables (information disclosure) | H | L | Intentional and required by AC-ERROR-1; identical to core's existing, deliberate behaviour. `sudo()` narrowly scoped to the figures resolver |

---

## Next Steps

1. **Phase 1 — Module foundation**: scaffold `addons/sale_credit_limit_warning/` (`__init__.py`, `__manifest__.py`, `models/`, `data/ir_config_parameter.xml`); implement `_get_credit_warning_ratio()` with fail-soft validation; verify the module installs cleanly and `git diff --stat -- addons/sale addons/account` is empty.
2. **Phase 2 — Severity engine (TDD)**: `_get_credit_limit_figures()`, `_build_credit_limit_detail()`, `_compute_credit_limit_warning_tier()`, and the two non-stored fields. Tests first: the six boundary cases (#11), the multi-currency 80% case, the multi-company 80% case, the no-accounting-access case (AC-ERROR-1, `Form()`-driven per `test_credit_limit.py:341`), the parity tripwire (#8) and the Invoicing guardrail (#9).
3. **Phase 3 — View extension**: `views/sale_order_views.xml` with the three `xpath` operations; confirm exactly one banner renders per tier and none when `none`; re-run core's `--test-tags /sale` with the module installed and confirm zero edits to `addons/sale/tests/`.
4. **Then**: `/bmb:uat` against the documented journey, followed by the E2E-implementation build and `/bmb:reflect`.
