---
name: agent-sdlc-router
description: Route work into define/plan/build/verify/review/ship phases with explicit artifacts and verification gates.
---

# Agent SDLC Router

## Purpose

Map a task to a phase-oriented workflow and require the right artifact at each phase.

## Routing Rules

- Define phase:
  - Trigger: unclear requirements or behavior changes.
  - Required artifact: `docs/superpowers/contracts/<task>.json`.
- Build phase:
  - Trigger: implementation work on source files.
  - Required artifact: `docs/superpowers/evidence/<task>.json`.
- Verify phase:
  - Trigger: completion claims.
  - Required evidence: command outputs in evidence artifact.
- Review phase:
  - Trigger: multi-file code changes.
  - Gate: contract + evidence both present and valid.
- Ship phase:
  - Trigger: merge/deploy readiness.
  - Gate: all required checks passed and risks/rollback documented.

## Non-negotiables

1. No code commit without evidence artifact.
2. No large change without a contract artifact.
3. No session-log rewrites; logs are append-only.
4. No rationalization phrases in evidence entries.

## Verification

- `pre-commit run --files <changed-files>` must pass.
- All required artifacts must validate against hook checks.
