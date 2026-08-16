---
post_title: "Phone focus recovery design"
author1: "GitHub Copilot"
post_slug: "phone-focus-recovery-design"
microsoft_alias: "copilot"
featured_image: ""
categories:
	- "Documentation"
tags:
	- "android"
	- "adb"
	- "backup"
	- "shell"
ai_note: "AI-assisted design document"
summary: "Design for a rooted-Android recovery, backup, monitoring, and one-command orchestration workflow built on phone_focus_mode."
post_date: "2026-05-01"
---

## Goal

Create a repeatable rooted-Android management workflow that can:

- restore a freshly formatted phone to the previously hardened state
- back up important phone state whenever the phone appears on this PC
- monitor security and device-health drift over time
- expose one highly visible entrypoint at `scripts/run_all/run_phone.sh`

The design must build on the existing `phone_focus_mode/` deployment system
instead of replacing it with a second parallel toolchain.

## Existing foundation

The existing `phone_focus_mode/` implementation already provides the core
security stack:

- `deploy.sh` deploys the focus scripts and companion app over ADB
- `focus_daemon.sh` enforces location-based focus restrictions
- `hosts_enforcer.sh` protects `/system/etc/hosts`
- `dns_enforcer.sh` forces DNS behavior that respects the hosts file
- `launcher_enforcer.sh` keeps the approved launcher installed and pinned
- `magisk_service.sh` restores the protections automatically on boot

The new workflow should reuse these assets rather than re-implement them.

Split into one file per area to stay under the 250-line cap.

- [Approved user experience, file layout and backup storage](2026-05-01-phone-focus-recovery/01-experience-and-layout.md)
- [Command modes, repair policy and device detection](2026-05-01-phone-focus-recovery/02-commands-and-repair.md)
- [Monitoring scope and the report contract](2026-05-01-phone-focus-recovery/03-monitoring.md)
- [Restore priority, backup policy and documentation requirements](2026-05-01-phone-focus-recovery/04-restore-and-policy.md)
- [Automation safety rules, testing expectations and non-goals](2026-05-01-phone-focus-recovery/05-safety-and-testing.md)
