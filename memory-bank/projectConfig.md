# Project Configuration

## Banyan Memory Bank

This section is auto-managed by `/bmb:init`. Do not edit manually.

- **Banyan Version**: 2.2.1
- **Initialized**: 2026-09-18
- **Last Updated**: 2026-09-18

## Git & Branching (v2)

Read by every banyan command for branch routing and protected-branch enforcement.

```yaml
metadata_branch: banyan
protected_branches: [banyan]
pr_target: banyan
sync_automation: none
archive_strategy: push-and-pr
worktree_root: ~/banyan-wt/odoo/
```

## Agent Backends

Which execution backend drives each configurable seam of the workflow. Codex companion plugin not detected on this machine — every seam defaults to Anthropic.

```yaml
backends:
  plan:                  anthropic
  tdd:                   anthropic
  code-review:           anthropic
  creative-architecture: anthropic
  creative-uiux:         anthropic
  creative-algorithm:    anthropic
  creative-user-journey: anthropic
  creative-critique:     codex
  auto-final-review:     anthropic
  availability:          auto
```

## Team

Maps each contributor's git identity (email) to a friendly first name.

```yaml
team:
  # <git-email>: <friendly first name>
  # Crowd-sourced and self-populating: every mutating command backfills the
  # current author's entry (from `git config user.email`) before pushing, if
  # it is missing.
  bob@hwainternational.com: Bob
```

## UAT

Project-wide defaults for `/bmb:uat`. Not yet configured for this project — no web/UI surface for `/bmb:uat` to walk (the repo is the Odoo framework itself, not a Banyan-authored UI). Run `/bmb:uat-init` if UAT becomes relevant later.

## Notes

- This is a fork of stock Odoo 18.0 (`github.com/DaKaZ/odoo`) with local Docker dev tooling added. No Banyan-specific business logic exists yet — this is the base for future customization.
- Codebase is large (12,325+ source files across 621 addon modules) — classified brownfield at init.
