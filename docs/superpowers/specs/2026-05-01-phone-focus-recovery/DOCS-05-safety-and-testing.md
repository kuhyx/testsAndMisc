# Automation safety rules, testing expectations and non-goals

## Automation safety rules

Because the phone may appear repeatedly over USB or Wi-Fi, automation must be
conservative.

Required safeguards:

- single-instance lock to prevent overlapping runs
- cooldown window so repeated reconnects do not trigger backup storms
- clear separation between lightweight `auto` mode and heavier full-backup
  behavior
- retry and backoff rules for transient ADB failures
- no automatic `fresh-phone` restore without explicit user intent

## Testing and verification expectations

The implementation phase should follow strict shell hygiene and repository
quality rules.

- use `set -euo pipefail`
- prefer reusable functions over repeated ADB snippets
- validate parameters and environment clearly
- keep destructive operations explicit and well-logged
- add tests where practical for shell logic or parser behavior
- run `pre-commit run --files <changed-files>` before claiming completion

Verification must include:

- shell syntax validation
- targeted script execution in safe modes
- README/help-text verification against the approved user flows
- evidence that backups and monitoring output are actually produced

## Constraints and non-goals

The design deliberately does not promise impossible guarantees.

- It cannot make a rooted phone impossible to tamper with locally.
- It cannot safely restore every app’s private data without app-specific risk.
- It should prefer explicit warnings over pretending unsupported restores are
  safe.

The goal is a robust, repeatable, operator-friendly recovery and monitoring
system, not an infallible anti-root fortress.

## Open implementation notes

- Reuse code patterns already present in `linux_configuration/scripts/utils/`
  and `python_pkg/screen_locker/_phone_verification.py` where they help with
  ADB detection and wireless reconnection.
- Keep the wrapper stable even if the internal phone implementation evolves.
- Preserve the existing `deploy.sh` value rather than rewriting it from
  scratch.
- Make backup scope declarative so expanding or narrowing coverage does not
  require editing core shell control flow.
