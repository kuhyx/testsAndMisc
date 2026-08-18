# best-of-Agent-Harnesses vs. kuhy's actual work — evaluation

Source list: github.com/RyanAlberts/best-of-Agent-Harnesses (160 projects, pulled via `gh api` on 2026-08-18).
Evidence base: full read of ~140 memory files (39 project, 52 feedback, 45 reference), CLAUDE.md + all `rules/`/`memories/`,
session-autopsy REPORT.md (445 sessions / 153,946 assistant messages), and a live filesystem survey of ~50 repos + `~/.claude/`
harness internals + self-hosted infra. Every claim below cites the specific memory file, repo path, or measured stat behind it.

---

## Baseline, stated plainly

You are not a harness *shopper* — you are a harness *builder*. The existing `~/.claude/` setup has 17 hooks across 6
lifecycle events, 21 support scripts, 27 project skills + 13 process-methodology skills (`~/.agents/skills`), a
background daemon, and a session-autopsy pipeline that mines your own transcripts (445 sessions, 153,946 messages)
to auto-detect automation candidates and compile them into deterministic scripts — two already done (`finish`:
-57% tokens/call, `phone-deploy`: -40%). You independently arrived at the exact thesis of Adam Jacob's token-spend
piece you've already encoded as a standing rule (`rules/token-spend.instructions.md`) *before* evaluating this list.
That reframes the right question from "which harness should I adopt" to "does anything on this list do something my
current setup doesn't, better than I could bolt on myself."

---

## High confidence

Backed by repeated, concrete evidence across multiple sessions/repos.

### MCP Inspector (mcp, typescript, 10.6k★)
You author and maintain **7+ MCP servers** (`i3wm-mcp`, `yay-mcp`, `aseprite-mcp`, `reaper-mcp`, `opengameart-mcp`,
`freesound-mcp`, plus 23 more under `~/mcp-servers/servers/`) per `project-mcp-server-fleet.md` and the deployment
skill `project-mcp-per-repo-pattern.md`. Nothing in your memory or tooling survey shows a dedicated tool/resource/prompt
debugger for the servers you *build* — you've been testing them indirectly through Claude Code sessions themselves.
MCP Inspector is a GUI built exactly for this gap: exercising tools/resources/prompts in isolation before wiring a new
server into a real session. Direct, unambiguous fit for your own MCP-authorship workflow.

### cocoindex-code (mcp, cli, tree-sitter/AST, 2.6k★)
Your token-spend discipline is measured, not aspirational: `err-549ef470` ("ALREADY IN CONTEXT" read-hook error) fired
**870 times across 190 sessions** — the single most common error in your corpus — and 16% of all tool turns (11,532 of
73,904) are mechanical, non-decision reads/greps. cocoindex-code replaces grep-and-re-read-whole-file with AST-aware
semantic lookup, attacking exactly this measured cost center. This is a closer match to your actual bottleneck than
generic "compression" tools (see Headroom/context-mode rejection below) because it targets the *read* side specifically,
which your own hook (`track_reads_pretool.sh`, since disabled) was already trying to police mechanically.

### Docker MCP Gateway (mcp, sandbox, cli, 1.5k★)
You run 23+ Dockerfiles for self-hosted MCP server containers (`~/mcp-servers/servers/*`) per the repo survey, on top
of an already-Docker-heavy self-hosted stack (Gitea, SearXNG, Syncyomi, Joplin Server, all `docker-compose.yml`-based).
A container-aware MCP gateway is a direct fit for consolidating discovery/auth across a fleet this size, rather than
each server being wired in ad hoc. Speculative on the *specific* tool, high-confidence on the *need* — you already
have the infrastructure pattern this tool assumes.

### agents.md (ide, typescript, 23.7k★) — as a *format*, not a new tool
You've independently built the same thing at larger scale: `CLAUDE.md` + recursively-loaded `rules/` + `memories/` +
skills, already proven to load automatically and tested with your own canary methodology
(`reference-claude-context-loading.md`). `agents.md`'s pitch (nested per-directory briefings, load-what's-relevant) is
something you could evaluate for the **multi-repo** problem specifically — right now your `CLAUDE.md` is global and
your `rules/` load on every turn of every session regardless of which of your ~50 repos you're in
(explicitly flagged as a cost in `rules/token-spend.instructions.md`: "Everything under `rules/` ... load[s] on every
turn"). Nested, directory-scoped AGENTS.md files are a plausible answer to a problem you've already named in writing.
Not "adopt this tool" — "the format you're missing is this one, for the repo-scoping gap you already flagged."

---

## Speculative

Plausible fit, but the evidence is thinner or the tool may just be a worse version of what you have.

### Composio (sandbox, tool-discovery, python/typescript, 29.7k★)
You've hand-rolled the "toolkit + OAuth" pattern per-app already: `reference-oauth-connect-github-pattern.md`
(device-flow buttons registered per-repo under your own GitHub account) and Firebase RTDB credentials at
`~/.config/crdt-sync/`. Composio centralizes 1,000+ toolkit integrations with auth handled once. Thin evidence because
your current per-app pattern is deliberate (`project-oauth-connect-github-pattern.md` reads as a chosen design, not a
pain point) — no session shows friction from *lacking* a centralized toolkit layer, only evidence that you'd need one
if you started integrating third-party SaaS tools at volume, which you haven't been doing.

### planning-with-files / get-shit-done (memory / cli-python, skill packs)
Your `~/.agents/skills` tree already has `writing-plans`, `executing-plans`, and `subagent-driven-development` — a
self-built process-methodology layer covering similar ground (crash-proof planning, session recovery). Also
`feedback-split-big-plans-into-session-prompts.md` documents you independently arrived at "one self-contained prompt
per session, not one big plan" for the same reason these tools exist (context rot avoidance in `get-shit-done`'s
pitch). Speculative because I can't confirm your existing skills' *content* matches these tools' specific mechanics
line-for-line — worth a side-by-side read, not a blind swap.

### Vibe-kanban / Symphony / AgentBox (multi-agent fleet managers)
You already run background forks/subagents heavily (session-autopsy shows this as a standard pattern) and have
`~/.agents/skills/dispatching-parallel-agents`. A fleet-queue UI for running many coding-agent tasks at once is
plausible if your parallel-agent volume grows, but no memory file documents friction from *managing* concurrent agent
runs — the one documented multi-agent friction (`feedback-check-for-concurrent-agent-work.md`, a duplicate-build
incident) was about **coordination visibility** (not knowing another session had already built something), which a
fleet manager doesn't obviously solve — that's a `git status`-before-building discipline problem, already fixed as a
standing rule, not a tooling gap.

### Terminal-Bench / SWE-bench (eval harnesses)
You hold a genuinely rigorous testing bar (100% branch coverage standing rule in `code-quality.md`, CI-mirror gates on
5 repos, `pre-commit run --all-files` before every rerun) — the *rigor* profile these benchmarks assume. But these are
benchmarks for evaluating *which model/harness* performs best on held-out tasks, not for evaluating *your own repos'*
code — you don't train or fine-tune agents, you use Claude Code directly. Speculative only as a way to sanity-check a
harness choice in the abstract, not as something you'd integrate into your workflow.

---

## Explicitly rejected

Looked relevant on the surface; concrete evidence says otherwise.

### Headroom, context-mode, MCP-Zero (progressive-disclosure / token-compression harnesses)
**Rejected, not "no evidence" — actively contradicted by evidence.** These pitch generic tool-output/context
compression as a bolt-on layer. You've already built two purpose-specific, *measured* compilations of exactly this
idea for your two highest-frequency workflows: `finish` (123 invocations/93 sessions → compiled script, -57% tokens)
and `phone-deploy` (30 invocations/29 sessions → compiled script, -40% tokens), governed by a written standing
principle (`rules/token-spend.instructions.md`) that explicitly says "convert to deterministic coordination only once
the steps are predictable" — i.e., generic compression proxies are the wrong layer; you compile the *specific*
recurring loop into code instead. A general-purpose compression proxy is a regression from what you're already doing:
narrower, deterministic, and measured per-workflow beats a blanket lossy compressor in front of everything.

### Mem0, cognee, Graphiti (memory layers)
Rejected on direct substitution grounds: you run **vestige**, a self-hosted memory MCP with local embedding models
(`~/.cache/vestige/fastembed`, 669MB, `nomic-embed-text-v1.5` + reranker) and a 27-table SQLite schema
(`knowledge_nodes`, `sessions`, `domains`, `agent_traces`, `insights`, `fsrs_cards`), actively written to as of today's
session (fresh WAL mtime). This is not a "you haven't tried memory tooling yet" gap — you're already running a more
sophisticated, self-hosted, locally-embedded memory system than any of these three, plus the separate file-based
memory system (`~/.claude/projects/.../memory/`) this very conversation is using. Adding a second memory layer would
create exactly the kind of redundant-parallel-system friction `feedback-check-for-concurrent-agent-work.md` warns
about.

### Langfuse, MLflow, Opik, Arize Phoenix (observability/eval-ops platforms)
Rejected — these are built for teams operating LLM apps *in production for other users*, with tracing/scoring/prompt-
versioning over live traffic. Your friction pattern is the opposite shape: `feedback-verify-real-deployment-path.md`,
`feedback-migrated-means-installed-on-phone.md`, and `feedback-verify-apk-contents-before-install.md` all show the
recurring failure is **claiming "done" without running the real deployment path** (dev venv vs. systemd interpreter,
git commit vs. installed APK) — a single-developer discipline problem already solved with a standing CLAUDE.md
workflow rule ("testing is always the LAST step") plus the phone-deploy skill's verification gate. None of these
platforms address "did you actually run it on the target device" — that's not what LLM-tracing tools check.

### n8n, Dify, langflow (low-code workflow builders)
Rejected. You have zero evidence of wanting a visual/low-code layer anywhere — every automation in your stack (39
systemd user units, 17 Claude Code hooks, CI workflows across ~15 repos) is code-first, version-controlled, and
reviewed via pre-commit/CI. Your entire `shell.instructions.md` + `token-spend.instructions.md` posture is explicitly
anti-abstraction ("don't design for hypothetical future requirements," "an LLM must not sit in a coordination loop
that code can express" — code, not a drag-and-drop canvas). A low-code workflow engine is a step backward from your
demonstrated preference for deterministic scripts you can read, diff, and put under CI.

### browser-use, Stagehand, Steel (standalone browser-agent harnesses)
Rejected as *redundant*, not irrelevant — you already have `claude-in-chrome` MCP tools wired in and actively used this
session, plus `servo-fetch` (Servo-engine fetch/crawl/screenshot MCP) under `~/mcp-servers/servers/`. Both solve the
"drive a real browser from an agent" problem you'd otherwise reach for these tools to solve. No session shows friction
with the browser tooling you already have that a swap would fix.

### OpenClaw, Khoj, nanobot, CowAgent (self-hosted "personal agent" runtimes)
Surface-level strong fit — you unambiguously self-host (Gitea, SearXNG, Syncyomi, Joplin Server + DuckDNS, Ollama on
an RTX 3090) and run 39 systemd user units as personal automation. But these products are chat/webhook-fronted
always-on daemons (Telegram/Discord/WhatsApp bots, "second brain" Q&A) — a different shape of automation than what you
actually build, which is narrow, single-purpose guard daemons with typed configs and 100%-coverage test suites
(diet-guard, screen-locker, wake-alarm, leetcode-guard). Adopting a general personal-agent runtime would mean
rewriting working, well-tested purpose-built daemons into a chatbot-shaped framework for no documented benefit — no
memory file shows you wanting conversational/chat-triggered automation, only scheduled/event-triggered guard logic.

### SWE-agent, AutoGen/AG2, CrewAI, LangGraph, MetaGPT, and the rest of the general-purpose multi-agent frameworks
Rejected as a category. You don't build third-party-facing agent products — you use Claude Code as your harness and
extend it via skills/hooks/MCP servers. None of these frameworks solve a problem you have; they solve "how do I build
my own multi-agent LLM application," which isn't your work. If you ever start building an agent *product* (not
personal tooling), this verdict would flip — but nothing in ~140 memory files or 51 session-history directories shows
that intent.

---

## Adjacent opportunity (explicitly speculative, not evidence-backed — per your request)

Flagged for your consideration, not recommended:

- **strands-agents / pydantic-ai** — if you ever want your own MCP servers to expose typed, multi-provider agent
  logic (not just tool wrappers), these are the closest fit to your existing Python-first, typed-function style
  (`code_style` in CLAUDE.md: "typed functions/dataclasses"). No current repo does this, so this is a "new capability"
  flag, not a gap-fill.
- **Google ADK / agents-cli** — Google-first, evals-integrated agent SDKs. You run local LLM inference via Ollama
  (`project-qwen-code-ollama-local-llm-setup.md`) as a Claude alternative for some tasks; if that local-model track
  grows, a provider-agnostic eval/deploy layer could matter. Currently unused territory.
- **Agent Governance Toolkit / agent-vault** — you don't currently have a documented credential-leakage incident, but
  given the scale of your self-hosted surface (Gitea PAT, DuckDNS, Firebase creds, Joplin brute-force limiter already
  hand-built), a secrets-proxy layer in front of agent tool calls is a plausible hardening step you haven't taken,
  not a fix for a problem you've hit.

---

## Bottom line

For the categories that matter most to how you actually work — harness customization, memory, token-spend discipline,
testing rigor, self-hosting — **you already have what you need, and in several cases (finish/phone-deploy compilation,
vestige, the CI-mirror gate) a more specific, better-measured version of what this list offers generically.** The
short list of concrete gaps worth pursuing is narrow: MCP Inspector (debug your own MCP servers), cocoindex-code
(attack your #1 measured error, the 870-hit "ALREADY IN CONTEXT" pattern, with AST search instead of re-reads), Docker
MCP Gateway (consolidate the 23-container MCP fleet you already run), and a close read of `agents.md`'s per-directory
scoping model against the "rules load on every turn regardless of repo" cost you've already named in writing. Nothing
else on this 160-project list moves the needle against your real history.
