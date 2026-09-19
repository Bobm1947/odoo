# Reflection: customer-credit-limit-warning - Customer Credit Limit Warning

**Date**: 2026-09-19
**Task Complexity**: Level 3
**Total Phases**: 3
**Duration**: 2026-09-18 to 2026-09-19

## Executive Summary

This task added a second ("approaching", 80%+) severity tier to Odoo core's existing binary customer-credit-limit banner on the Sale Order form, without editing a single byte inside `addons/sale/` or `addons/account/`. The Spec Writer's discovery that core already implements ~70% of the feature (`partner_credit_warning`, shared with Invoicing) reframed the whole task from "build a banner" to "extend a shared core mechanism safely" — the single highest-leverage moment in the entire workflow, because it is what made the eventual new-addon architecture decision even thinkable as a small, additive change rather than a large one.

The implementation is genuinely good: a new addon (`addons/sale_credit_limit_warning/`) that `_inherit`s `sale.order`, adds two non-stored fields computed from a single figures dict (so severity and message can never disagree), re-targets the existing banner div via `xpath` rather than replacing it (preserving core's `Form()`-driven access test contract), and fixes two real, cited core bugs (a discarded `.with_company()` and a missing `'state'` `@api.depends` entry) entirely inside its own resolver rather than touching core. 15/15 addon tests pass, and the two full regression sweeps of core's own `sale` test suite (221/221 in Phases 1-2, 7/7 of `TestSaleOrderCreditLimit` in Phase 3) show zero regressions. The `git diff --stat -- addons/sale addons/account` empty-diff invariant held for all three phases, satisfying the repo's dominant "upstream-merge safety" NFR.

The process was not friction-free. Three independently-authored creative documents (User Journey, Architecture, UI/UX) each made a defensible call on a detail the others didn't fully own — most consequentially, a direct contradiction between the UI/UX doc (`role="alert"` on both tiers) and the User Journey doc's explicit, reasoned AC-A11Y-1 (`role="status"` on the approaching tier, to avoid interrupting screen readers on every keystroke). The build orchestrator's Step 8 code review found this and "fixed" it by silently picking the UI/UX doc's version — which was actually *regressing* a correct accessibility decision — and it was only caught because a human reviewed the build-phase gate and asked the question explicitly. A second, unrelated code-review catch (a `.sudo()`-parity test that was actually running under the privileged default test user, so it tested nothing) shows the review step working as intended when there is no cross-document ambiguity to be silently resolved. Overall: strong technical outcome, with one process gap worth fixing before it recurs on a task with a less attentive human in the loop.

---

## Dimension 1: Task Implementation Quality

### Requirements Achievement

**Status**: ✅ All Met

All 5 originally-planned ACs plus the 3 Phase-3-added ACs are genuinely satisfied by the code, not just claimed by task-file prose:

- **AC-ENTRY-1** (banner present, zero navigation) — satisfied structurally: the view re-targets the existing div in its existing slot; `test_view_and_access.py` and `test_e2e_live_flow.py` both read the div directly from `get_view()['arch']`, not just from a rendered screenshot claim.
- **AC-HAPPY-1** (red/over-limit, all 3 data points) — `test_just_over_100_percent_is_over` + `test_total_credit_parity_with_core_message` (the parity tripwire) together prove both the tier boundary and that the totals genuinely agree with core's own string, not just independently computed.
- **AC-HAPPY-2** (yellow/approaching at ≥80%) — `test_exactly_80_percent_is_approaching`, `test_between_80_and_100_percent_is_approaching`, and critically `test_exactly_100_percent_stays_approaching` — this last one is the test that actually proves trigger parity (core returns `''` at exactly 100%, so red must not fire there either), and it is present and passing.
- **AC-HAPPY-3** (absent, not hidden) — `test_no_credit_limit_set`, `test_credit_use_disabled`, `test_comfortably_under_threshold`, plus the view-layer `test_view_both_banners_hidden_when_level_none` which checks the actual `invisible` expression via `safe_eval`, not just the field value. This is a meaningfully stronger assertion than "the field is empty."
- **AC-ERROR-1** (visible to non-Accounting Sales users) — `test_credit_warning_fields_readable_without_accounting_access` in Phase 2, later strengthened in Phase 3 (see Challenges) once the code review caught that the Phase 3 confirm-flow variant wasn't actually exercising a restricted user.
- **AC-LIVE-1** (live, no-save threshold walk) — `test_live_flow_crosses_thresholds_without_save` walks none→approaching→over→none inside one `Form()` context with no `.save()` call, and additionally asserts structural equality (same icon/field skeleton) between the two divs, which is a real proxy for the "zero reflow" claim the User Journey doc cared about.
- **AC-NAV-1** (never blocks confirm; retires post-confirm) — `test_confirm_never_blocked_and_banner_absent_after_confirm`, run under a restricted Sales user after the Step 8 fix.
- **AC-A11Y-1** (tier legible without color) — `test_tier_distinguishable_by_text_and_aria_role` asserts both the verb-phrase text distinction and the `role` attribute per div, straight from the arch.

No scope creep observed: the addon declares no `account.move` inheritance and no `account.view_move_form` extension, and `test_invoicing_isolation_guardrail` makes that structural claim into an executable regression guard rather than a design-doc assertion nobody re-checks.

### Code Quality Assessment

**Overall Rating**: Excellent

- **Maintainability**: `models/sale_order.py` is a clean single-responsibility chain — `_get_credit_warning_ratio()` → `_get_credit_limit_figures()` → `_build_credit_limit_detail()` → `_compute_credit_limit_warning_tier()` — each independently testable, matching the Architecture doc's own "model first" guideline verbatim. The one-figures-dict-drives-two-fields design (`credit_warning_level` and `credit_limit_detail` computed together) is the single best structural decision in the codebase: it makes it *impossible* for severity and message text to disagree, which is exactly the kind of invariant that prevents an entire class of future bugs (e.g., a yellow banner with red-tier wording).
- **Architecture**: The `xpath` re-target of the existing `partner_credit_warning` div (rather than `position="replace"`) is a subtle and correct call — replacing it would have removed the field node from the arch and broken core's `Form()`-driven `test_credit_limit_access`, which is exactly the kind of contract violation that would only surface as a mysterious regression later. The Architecture doc called this out explicitly and the implementation honors it.
- **Error Handling**: `_get_credit_warning_ratio()`'s fail-soft threshold validation (out-of-range or unparseable `ir.config_parameter` → `warning` log + documented `0.8` fallback, never a silent wrong threshold) is a well-considered piece of defensive code for a value an operator can misconfigure (e.g., entering `80` meaning percent instead of `0.8`).
- **Testing**: See below — this is the strongest dimension of the implementation.

### Technical Decisions

**Key Decisions:**
1. **New addon vs. extend shared core method** — Architecture creative doc weighed 5 options with an explicit evaluation matrix and picked "new addon, additive fields, view re-target" over editing `_build_credit_warning_message()` in place. Outcome: correct. The empty upstream diff held for all 3 phases, and the addon is independently installable/uninstallable, matching this fork's explicitly documented (`productBrief.md` risk list) upstream-merge-safety priority.
2. **Non-stored computed fields, no schema change** — matches core's own `partner_credit_warning` pattern; avoids a migration and a mass-recompute over existing Sale Orders at install. Outcome: correct, and consistent with why the live/no-save-required behavior (AC-LIVE-1) works at all.
3. **Threshold as `ir.config_parameter` rather than hardcoded 0.8** — goes beyond the task spec's literal instruction ("80% is a fixed spec value... unless Creative Phase says otherwise") by making it operator-configurable, justified as satisfying the repo's own 12-factor "config in environment" convention. This is a reasonable interpretation, not scope creep, since the task file explicitly left the door open to Creative Phase overriding the fixed-value assumption.
4. **Two real core bugs found and fixed only inside the new addon** (discarded `.with_company()` return at `sale_order.py:772-773`; missing `'state'` in core's `@api.depends`) — correctly scoped: fixed in the new addon's own resolver, not upstream, with a code comment explaining why. This is the right call for a fork that cannot get such fixes upstreamed within this task's boundary, though it is worth flagging (see Technical Debt) that these bugs remain live in core itself.

**Trade-offs:**
- **8 small files instead of a ~20-line patch**: accepted deliberately; buys an empty upstream diff and an installable/uninstallable unit visible in Settings > Apps. Correct trade given this fork's stated risk priorities.
- **The over-tier headline keeps core's exact wording, giving the two tiers a slightly different phrasing register** (one is a full sentence pair, the other splices core's sentence with an addon-supplied breakdown): accepted to avoid owning core's exact-string test assertions. This is a real, visible seam in the output but a correctly-reasoned one — the alternative (Option 4, overriding `_compute_partner_credit_warning`) was explicitly evaluated and rejected for exactly this reason.
- **`credit_limit_detail` rendered by two separate `<field>` nodes in one arch** — forced by Odoo's inability to compute a dynamic `class` attribute (cited as C5 in the Architecture doc). Legal and precedented; a minor structural smell rather than a real problem.

### What Went Well

1. **The Spec Writer's core-mechanism discovery.** Finding that `partner_credit_warning` already existed, was shared with Invoicing, and was strictly binary — before any creative or build work began — is what made every downstream decision tractable. Without it, this task could easily have been scoped and built as a from-scratch feature, very possibly by editing `addons/sale/` directly.
2. **The figures-dict-as-single-source-of-truth design.** One compute produces both the severity enum and the detail text; there is structurally no way for them to disagree. This is exactly the kind of design decision that prevents an entire class of bugs other implementations invite (e.g., separately computing "is it yellow" and "what does the yellow text say").
3. **The parity and guardrail tests as tripwires, not just correctness checks.** `test_total_credit_parity_with_core_message` and `test_invoicing_isolation_guardrail` are not testing *this task's* logic so much as testing that a *future* upstream change to core's shared method will be caught loudly rather than silently drifting. This is unusually forward-looking test design for a Level 3 task.
4. **Zero regressions across two full core-suite sweeps** (221/221, then 7/7 of the narrower `TestSaleOrderCreditLimit` tag) — the upstream-merge-safety invariant wasn't just claimed, it was mechanically re-verified at the end of every phase.

### Challenges Encountered

1. **Phase 1 lint gate failure (28 flake8 violations)** — resolved via mechanical reformatting (line length, lambda-to-def, `# noqa` on `__init__.py` imports per the repo's own `sale_margin` precedent), no logic change, re-verified clean. Minor friction, correctly and quickly resolved; not a design problem.
2. **Phase 2 cross-creative-document a11y conflict** — see the dedicated analysis below (Guardrail Misses & Root-Cause Analysis). The technical resolution (reverting to `role="status"` on the approaching tier) was correct once surfaced, but it took a human noticing during the phase-gate review rather than the orchestrator's own Step 8 process.
3. **Phase 3 access-parity test that tested nothing** — `test_confirm_never_blocked_and_banner_absent_after_confirm` originally ran under the privileged default test user, meaning a regression that dropped the `.sudo()` elevation inside `action_confirm()`'s call path would have passed silently. Code review caught this correctly and the fix (a `sales_user` fixture + `with_user()`) is exactly right. This is the code-review step working as designed — worth contrasting directly with the Phase 2 miss, since both are "code review found a test/implementation gap," but only one was handled without human intervention.

### Technical Debt & Future Work

- **Two real core bugs remain unfixed in `addons/sale/models/sale_order.py`** (discarded `.with_company()` at lines 772-773; missing `'state'` in `@api.depends` at line 770): correctly out of scope for this fork's own addon, but worth a tracked upstream issue/PR against Odoo so the fix isn't perpetually re-derived by every fork that notices it. Not a defect in this task's own scope, but worth naming explicitly so it doesn't get lost.
- **Invoicing (`account.move`) never received the equivalent two-tier treatment** — explicitly out of scope per the task, and the User Journey doc's Option 3 rejection already documents this as a deferred enhancement. No action needed now, but the architecture (a sibling addon or a promoted mixin) is already sketched in the Architecture doc's Q3 answer if it's ever picked up.
- **The two tiers' banner text has a slightly different phrasing register** (documented trade-off above) — low priority, but if the product ever wants a fully unified single-message wording across both tiers, the Architecture doc's own documented escape hatch (hide core's field entirely, move the full headline into `credit_limit_detail`) is the path, contained entirely within this addon.
- **No list/kanban-view credit signal** — noted as an explicit non-goal in the User Journey doc's Trade-offs; a reasonable future enhancement, not a gap in this task.

---

## Dimension 2: Claude Code Ecosystem Effectiveness

### Build Session Analysis

No `.agent-logs/claude/by-task/` directory exists for this repo/session setup, and no fallback date-range logs were available either — this analysis is based entirely on the task file's Execution State log, the git commit history, and direct inspection of the addon source and creative docs. No tool-call counts, sub-agent invocation counts, or per-step timing figures are fabricated below; where the task file's own narrative supplies a concrete, attributable event (a lint failure, a code-review finding, a specific fix), it is cited as such. **Recommendation**: run `/bmb:init` (or verify the by-task log-indexing upgrade) so future reflections on this repo can ground the ecosystem-effectiveness dimension in actual tool-utilization data rather than task-file narrative alone.

### Command Workflow Evaluation

**Commands used** (per the task file and commit history): `/bmb:roadmap feature create` → `/bmb:plan` → `/bmb:creative` (3 parallel agents) → `/bmb:build` ×3 phases → `/bmb:reflect` (this invocation).

**Workflow Efficiency**: Good

- The Level 3 workflow (`roadmap → plan → creative → build×N → uat → reflect → archive`) was followed correctly in shape, with one nuance: the task's Test Strategy and Next Steps sections both mention a UAT step before Phase 3 ("Then: `/bmb:uat` against the documented journey, followed by the E2E-implementation build and `/bmb:reflect`" — Architecture doc's Next Steps), but the actual execution ran Phase 3 (E2E + regression guard) directly after Phase 2 without a documented intervening `/bmb:uat` pass. Given this is a backend-heavy, low-UI-surface feature (a text banner, no new interaction), skipping UAT is a defensible judgment call, but it is a deviation from what the creative docs themselves specified as the intended sequence, and it's worth the human confirming that was an intentional skip rather than a dropped step.
- The Spec Writer's discovery of the 70%-already-built core mechanism was surfaced *before* the Creative phase, which is exactly the right place for it — it reframed all three creative agents' starting context rather than being discovered mid-build and forcing rework.

### Context File Effectiveness

- `systemPatterns.md`'s "Inheritance over modification" Guiding Principle was the single most load-bearing piece of context in this task — every creative document cites it directly as the deciding factor against Options 1/2/4, and the Architecture doc's Validation Checklist explicitly checks against it. This is context doing exactly what it's for.
- `productBrief.md`'s Risks section (upstream-merge-safety ranked Medium-likelihood/High-impact, with the stated mitigation "keep Banyan-specific changes in separate addons") was likewise directly cited and decisive in the Architecture doc's rationale. Good example of Level 3 creative phases actually reading and using productBrief rather than treating it as boilerplate.
- **Gap**: `observability-requirements.md`'s OpenTelemetry mandate does not fit this codebase at all (no OTEL dependency exists anywhere in this fork), and the Architecture doc had to spend a substantial section ("Observability Architecture") explaining and justifying the deviation rather than just satisfying it. This is not wasted effort — the documented deviation is exactly the right way to handle it — but it suggests `observability-requirements.md` (or a per-project override of it) should have an explicit "N/A for platforms with no telemetry layer" escape hatch documented once, rather than requiring every Level 3+ task's Architecture agent to re-derive and re-justify the same deviation from scratch.

### Sub-Agent Performance

| Agent Type | Invocations | Model | Effectiveness |
|------------|-------------|-------|---------------|
| Spec Writer | 1 | (per model-selection-strategy, tier for L3) | High — the core-mechanism discovery was the single highest-leverage output of the whole workflow |
| User Journey Design | 1 | Sonnet (creative) | High — thorough, and the a11y politeness-split reasoning (AC-A11Y-1) was correct and well-justified; its Findings section fed the Architecture agent three concrete, cited bugs/constraints |
| Architecture Design | 1 | Sonnet (creative) | High — the 5-option evaluation matrix, the explicit reasoning for re-targeting vs. replacing the banner div, and the observability-deviation writeup were all substantive, not boilerplate |
| UI/UX Design | 1 | Sonnet (creative) | Medium — strong on color/copy/Bootstrap precedent (the `account_edi` structural-precedent citation was genuinely useful), but its accessibility section asserted `role="alert"` on both tiers without apparently cross-checking the User Journey doc's already-published, more carefully-reasoned AC-A11Y-1 split. See root-cause analysis below. |
| TDD Agent | 3 (one per phase) | Sonnet (build) | High — RED confirmed before GREEN in every phase per the task file; the Phase 3 test-authoring bug (invalid post-`Form()` assertion) was caught and fixed in-context without escalation |
| Code Review | 3 (one per phase) | Sonnet/Codex-configured but fell back to Anthropic (`unresolved:no-companion`, per task file) | Mixed — correctly caught the Phase 3 `.sudo()`-parity test gap (a genuine, well-specified, single-option fix); on Phase 2 it detected the a11y attribute deviation but resolved it by silently picking a side of a cross-document conflict rather than flagging the conflict itself (see below) |
| Documentation Agent | 3 (one per phase) | Haiku (per model-selection-strategy) | Low-Medium — correct content in each individual update, but see the recurring process-friction pattern below |
| Creative Critique | 0 (skipped) | — | N/A — `unresolved:no-companion` (Codex glob empty on this machine); silent fallback per `availability: auto`. Not a finding against this task, but worth noting the advisory critique pass never actually ran, so it could not have caught the cross-document a11y conflict either. |

### Command Workflow Evaluation — Build Orchestrator Step 8 Gap (detailed)

The Phase 2 Step 8 code review found a genuine deviation: the shipped view had `role="alert"` on both tiers, while the UI/UX creative doc's Design Specifications section also says `role="alert"` on both. The orchestrator "fixed" the code to match the UI/UX doc — but the User Journey doc, published in the same creative phase, contains an entire subsection ("Accessibility of live updates (a new requirement the second tier creates)") that explicitly derives `role="status"` for the approaching tier from first principles (it recomputes on every order-line edit; an assertive region would interrupt screen-reader speech on nearly every keystroke) and states it as a **Decision** table with an explicit a11y rationale, later restated as a normative table in the Copy Specification section and as a checklist item in the Accessibility Checklist. This was not a subtle or buried detail — it is one of the User Journey doc's most carefully-argued sections, explicitly framed as "a new requirement the second tier creates."

The orchestrator's Step 8 treated this as a simple "code deviates from a creative doc, fix the code" case, when it was actually "two creative docs disagree, and the code happens to match one of them." Those are different failure modes requiring different responses: the former is safe to auto-fix; the latter is a DECISION_NEEDED that the human gate exists to catch. It was caught — but only because the human reviewing the build-phase gate happened to notice the discrepancy and asked about it explicitly (per the task file's Guard & Recovery Log), not because the orchestrator's own process surfaced it as a conflict.

### Memory Bank Organization

- **Structure**: Adequate. Three separate creative docs for one Level 3 task, each with its own "Decision" + "Validation Checklist" + "Next Steps" sections, worked well for keeping each design lane's reasoning legible and independently reviewable.
- **Navigation**: Good — the task file's Execution State log is detailed enough that this reflection could be written largely from it plus the creative docs, without needing to reconstruct intent from code alone.
- **Completeness**: One structural gap this task exposed: there is no memory-bank artifact whose job is specifically "reconcile creative-phase documents against each other." Each creative doc has a "Next Steps" pointing at the *next* phase, but none has a cross-check pointing *sideways* at its siblings. See Memory-Bank Corrections below.

### Memory-Bank Corrections (from Guardrail Misses) — ACT ON THESE

| File · section | Current (stale/wrong) | Correction | Evidence (guard flag / re-invocation) |
|---|---|---|---|
| `context/agents/build-*.md` (or wherever Step 8 code-review methodology lives) · Code Review decision procedure | Step 8 treats "implementation deviates from a creative doc" as a single case to be auto-fixed | Add a branch: before auto-fixing a deviation, check whether the *other* creative docs for the same task state a conflicting requirement on the same attribute/behavior. If they do, this is a cross-document conflict, not a simple drift — escalate as DECISION_NEEDED to the human gate rather than silently picking either side. This is a process gap, not a memory-bank content bug, but it is the single most consequential guardrail-adjacent miss in this build and belongs in the same corrective loop. | Phase 2 Step 8: orchestrator silently reverted `role="status"` to `role="alert"`, undoing a correct, explicitly-reasoned a11y decision from the User Journey doc; caught only by human review at the phase gate, not by the orchestrator's own process. |
| `agents/creative-uiux-agent` methodology (or a shared creative-phase instruction) | UI/UX and User Journey creative agents each write their Decision/Validation sections independently, with no instruction to check sibling creative docs for the same task before finalizing overlapping details (ARIA roles, interaction semantics) | Add an explicit instruction: before finalizing a Decision, a creative agent should check whether a sibling creative doc for the same task (if already DECIDED) makes a claim about the same UI attribute, and reconcile or explicitly flag the discrepancy in its own doc rather than silently asserting its own value | Same evidence as above — the UI/UX doc's `role="alert"`-on-both-tiers assertion and the User Journey doc's `role="status"`-on-approaching assertion were never reconciled by either document; the UI/UX doc shows no awareness the User Journey doc existed or disagreed. |

This is a **process** correction rather than a stale-content correction (unlike the canonical "systemPatterns.md test-scope entry is wrong" example) — there is no single memory-bank file whose prose is factually stale here. The applicable fix lives in the build orchestrator's and creative agents' own methodology files, which `/bmb:archive` or a human maintainer should route to accordingly.

### Suggested Improvements to Claude Code System

**High Priority**:
1. **Add a cross-document consistency check as a discrete step in `/bmb:creative`'s fan-out**, run after all three (or four) creative agents complete but before the phase is marked DECIDED — even a cheap, mechanical pass (e.g., grep each doc for the other docs' pinned attribute values like `role=`, CSS classes, field names) would have caught this specific conflict before build ever started, which is strictly cheaper than catching it at Step 8 of Phase 2.
2. **Change the build orchestrator's Step 8 procedure so any code-review finding that traces to a discrepancy between two creative documents is escalated as DECISION_NEEDED, not auto-resolved.** The orchestrator has no principled way to know which creative doc is "more authoritative" on a given micro-decision (UI/UX owns Bootstrap classes/copy; User Journey owns end-to-end interaction/accessibility flow — neither is strictly senior to the other), so silent resolution is structurally unsound regardless of which doc happens to be picked.

**Medium Priority**:
1. **Give sub-agents an explicit "do not create your own commit" instruction when the orchestrator's protocol is a single end-of-phase commit.** The Documentation Agent committed separately mid-phase in all three phases (`0876738d`, `c674ad3f`, `5aa4e8f6`) rather than leaving its changes for the orchestrator's single phase commit, and in Phase 1 additionally skipped a task-file Execution State update it was asked to perform, requiring the orchestrator to complete that part itself. This is low-severity (git history stays legible either way — each commit is well-scoped and correctly named) but is a repeated pattern across all 3 phases, suggesting the current instruction wording is being interpreted as "commit your own artifact" rather than "stage your own artifact for the phase commit."
2. **Document an explicit "N/A for platforms with no telemetry layer" escape hatch in `observability-requirements.md`** (or as a per-project override mechanism) rather than requiring every Level 3+ Architecture agent on a codebase like this Odoo fork to independently re-derive and re-justify the same OTEL-inapplicability writeup from scratch each time. This is boilerplate the Architecture doc did well, but it's the same boilerplate this codebase will need again on its next Level 3-4 task.

**Low Priority / Nice to Have**:
1. **Note the UAT-before-Phase-3 sequencing question explicitly in the task file when it happens** — the Architecture doc's own Next Steps specified a UAT pass before the E2E-implementation build, and Phase 3 appears to have proceeded directly without one. This may well have been the correct judgment call for a low-UI-surface feature, but a one-line note in the Execution State ("UAT skipped: text-only banner, no new interaction surface, judged low-risk") would make that an explicit, auditable decision rather than a silent deviation from the creative docs' own stated plan.

**Note**: These are suggestions only. Do NOT implement these changes — they are recommendations for future system enhancements.

---

## Key Learnings

### Extractable Learnings (for Continuous Learning)

1. **cross-doc-consistency** (`memory-bank/creative/*.md`, Level 3-4 tasks): Before marking a creative phase DECIDED, grep sibling creative documents for the same task for conflicting pinned values on shared attributes (ARIA roles, CSS classes, field names, thresholds) and reconcile or flag discrepancies explicitly rather than letting each document assert its own value independently.
2. **build-review-escalation** (`build orchestrator Step 8 / code review`): When a code-review finding traces to a contradiction between two creative documents rather than a single implementation drift, escalate it as DECISION_NEEDED to the human gate instead of silently picking one document's version to "fix" the code toward.
3. **subagent-commit-discipline** (build sub-agents given "commit at end of phase" instructions, especially the Documentation Agent): Stage documentation/task-file changes for the orchestrator's single end-of-phase commit rather than creating a separate mid-phase commit, and complete every requested task-file Execution State update before handing back — don't leave partial updates for the orchestrator to finish.
4. **odoo-inherit-safety** (`addons/*/models/*.py`, `addons/*/views/*.xml` in this fork): When extending a core Odoo compute/view that another module's `post_install`-tagged tests assert exact-string/`Form()`-field-presence contracts against, re-target via `xpath` on the existing field node (never `position="replace"` on it, never override the original compute method) — this is what keeps upstream regression suites green with zero edits to files this task doesn't own.

### Learned Rules Applied

No learned rules available — `memory-bank/agent-rules/_learned/` was not checked against a specific prior rule set as part of this reflection; no existing learned-rule file was cited as directly applicable in the creative or build docs reviewed for this task. (If `/bmb:archive` finds relevant `_learned/` entries when consolidating, this section should be updated to note whether they were applied.)

### For Claude Code Workflow

1. **A cheap, mechanical cross-doc consistency pass after creative fan-out is strictly cheaper than catching the same conflict during build-phase code review** — the conflict here was caught, but only by a human at a gate that exists for a different purpose (approving phase completion, not resolving design disagreements).
2. **Sub-agent "commit as part of the phase" instructions need to be explicit about *not* creating separate commits**, not merely imply it by describing a single-commit workflow — the pattern repeated identically across all 3 phases, suggesting it isn't an isolated slip.
3. **A Spec Writer that discovers "most of this already exists in the codebase" before Creative phase begins is disproportionately valuable** — it reframed every subsequent decision in this task from "build X" to "extend X safely," and is worth treating as a template for any Level 2-4 task on a brownfield/fork codebase.

---

## Conclusion

The implementation itself is strong: a correctly-scoped, well-tested, upstream-merge-safe addition to a shared core mechanism, with genuinely good test design (parity tripwires and structural guardrail tests, not just boundary-value checks) and two real core bugs found and correctly contained rather than either ignored or upstreamed inappropriately. The workflow that produced it worked well in the large — Spec Writer's discovery, the Architecture agent's disciplined option evaluation, and the code-review step's Phase 3 catch all demonstrate the ecosystem functioning as designed. The one clear gap — a code-review step that silently resolved a genuine cross-creative-document accessibility conflict instead of escalating it, caught only by an attentive human at the phase gate — is narrow, well-understood, and has a specific, actionable fix (escalate rather than auto-resolve when a finding traces to disagreeing creative docs; add a cheap cross-doc check after creative fan-out). Both are cheap to make and would have prevented this specific incident without adding meaningful process overhead to future tasks.

**Overall Task Success**: ✅ Success

**Overall Workflow Effectiveness**: ⚠️ Moderately Effective (strong technical outcome; one specific, fixable orchestration gap identified and documented above)

**Recommendation**: Ready to archive. Route the two High Priority ecosystem-improvement suggestions (cross-doc consistency check post-creative-fan-out; Step 8 escalate-don't-resolve on doc-conflict findings) to whoever maintains the `bmb:creative` and build-orchestrator methodology files, since they are process fixes rather than memory-bank content fixes.
