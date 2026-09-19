# Agent Rules Index

Generated: 2026-09-19T00:00:00Z
Indexed: 4 rules (0 human-authored, 4 learned) | Rejected: 0 (unsafe) | Warnings: 0

## Validation Summary

### Health Check
- Total rules: 4
- Human-authored rules: 0
- Learned rules (auto-generated): 4
- Estimated max context: ~89 lines (OK)
- Conflicts detected: 0

### ⚠️ Warnings
None.

### 🚫 Rejected Rules (Unsafe)
None.

---

## Rules by File Pattern

| Pattern | Rule | Priority | Lines |
|---------|------|----------|-------|
| `memory-bank/creative/*.md` | [creative-cross-doc-consistency.md](agent-rules/_learned/creative-cross-doc-consistency.md) | low | 21 |
| `addons/*/models/*.py`, `addons/*/views/*.xml` | [odoo-inherit-safety.md](agent-rules/_learned/odoo-inherit-safety.md) | low | 21 |
| `**/*` | [build-review-escalation.md](agent-rules/_learned/build-review-escalation.md) | low | 24 |
| `**/*` | [subagent-commit-discipline.md](agent-rules/_learned/subagent-commit-discipline.md) | low | 23 |

## Rules by Path

(none — no `paths` entries in current rule set)

## Rules by Topic

| Keywords | Rule | Priority |
|----------|------|----------|
| creative-phase, consistency | [creative-cross-doc-consistency.md](agent-rules/_learned/creative-cross-doc-consistency.md) | low |
| build-orchestrator, code-review, creative-phase | [build-review-escalation.md](agent-rules/_learned/build-review-escalation.md) | low |
| build-orchestrator, documentation-agent, git | [subagent-commit-discipline.md](agent-rules/_learned/subagent-commit-discipline.md) | low |
| odoo, upstream-merge-safety | [odoo-inherit-safety.md](agent-rules/_learned/odoo-inherit-safety.md) | low |

---

## Conflict Resolutions

None — all 4 rules are additive with no overlapping instructions on the same topic.
