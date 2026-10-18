from __future__ import annotations

import pytest

from python_pkg.token_dashboard import classify


@pytest.mark.parametrize(
    ("command", "family"),
    [
        ("ls -la", "ls"),
        ("git -C /repo status --short | head", "git status"),
        ("cd /x && git log --oneline -3", "git log"),
        ("~/.claude/scripts/capped.sh python3 -m pytest -q", "python3 -m pytest"),
        (
            "CAP_MEM=4G CAP_CPU_PCT=20 ~/.claude/scripts/capped.sh pnpm -s lint",
            "pnpm lint",
        ),
        ("timeout 40 nice -n 19 grep -r x .", "grep"),
        ("python3 scripts/check.py --all", "python3 check.py"),
        ("bash ~/src/utils/scripts/gate_stamp.sh step x", "bash gate_stamp.sh"),
        ("/usr/bin/sqlite3 db 'SELECT 1'", "sqlite3"),
        ("cd /x", "cd"),
        ("python3 -m", "python3 -m"),
        ("python3 <<'EOF'\nprint(1)\nEOF", "python3"),
        ("bash -c 'x' > /dev/null", "bash -c"),
        ("git", "git"),
        ("FOO=1", "(empty)"),
        ("", "(empty)"),
    ],
)
def test_bash_family(command: str, family: str) -> None:
    assert classify.bash_family(command) == family


@pytest.mark.parametrize(
    ("name", "tool_input", "family", "target"),
    [
        ("Bash", {"command": "git  status\n"}, "git status", "git status"),
        ("Bash", {}, "(empty)", ""),
        (
            "mcp__claude-in-chrome__navigate",
            {"url": "x"},
            "mcp:claude-in-chrome",
            "navigate",
        ),
        ("Skill", {"skill": "dataviz"}, "skill", "dataviz"),
        (
            "Read",
            {"file_path": "/h/.claude/rules/a.md"},
            "Read:rules",
            "/h/.claude/rules/a.md",
        ),
        (
            "Read",
            {"file_path": "/h/.claude/projects/p/memory/m.md"},
            "Read:memory",
            "/h/.claude/projects/p/memory/m.md",
        ),
        ("Read", {"file_path": "/r/CLAUDE.md"}, "Read:claude-md", "/r/CLAUDE.md"),
        (
            "Edit",
            {"file_path": "/h/.claude/skills/x/SKILL.md"},
            "Edit:skill",
            "/h/.claude/skills/x/SKILL.md",
        ),
        (
            "Write",
            {"file_path": "/h/.claude/settings.json"},
            "Write:claude",
            "/h/.claude/settings.json",
        ),
        ("Read", {"file_path": "/r/shot.PNG"}, "Read:image", "/r/shot.PNG"),
        ("Read", {"file_path": "/r/a.py"}, "Read:file", "/r/a.py"),
        ("Read", {}, "Read:file", ""),
        ("Grep", {"pattern": "def x", "path": "/r"}, "Grep", "def x"),
        (
            "WebFetch",
            {"url": "https://docs.example.com/a?b"},
            "WebFetch",
            "docs.example.com",
        ),
        ("WebSearch", {"query": "sqlite window"}, "WebSearch", "sqlite window"),
        ("Agent", {"subagent_type": "Explore"}, "Agent", "Explore"),
        ("Agent", {"isolation": "worktree"}, "Agent", "general-purpose [worktree]"),
        ("TaskStop", {"id": 1}, "TaskStop", ""),
    ],
)
def test_family_and_target(
    name: str, tool_input: dict[str, object], family: str, target: str
) -> None:
    assert classify.family(name, tool_input) == family
    assert classify.target(name, tool_input) == target


def test_target_is_capped() -> None:
    long = {"command": "echo " + "x" * 1000}
    assert len(classify.target("Bash", long)) == classify.TARGET_CHARS


def test_signature_ignores_key_order_but_not_values() -> None:
    one = classify.signature("Bash", {"command": "ls", "timeout": 5})
    same = classify.signature("Bash", {"timeout": 5, "command": "ls"})
    other = classify.signature("Bash", {"command": "ls -a", "timeout": 5})
    assert one == same
    assert one != other
    assert len(one) == classify.SIG_CHARS


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Exit code 1\nboom", "exit_code"),
        ("<tool_use_error>File has not been read yet</tool_use_error>", "tool_error"),
        ("The user doesn't want to proceed with this tool use.", "rejected"),
        ("Permission for this action was denied by the classifier", "denied"),
        ("PreToolUse:Bash hook error: blocked by policy", "hook"),
        ("TIME CAP: this command was killed at 60s", "time_cap"),
        ("[Request interrupted by user for tool use]", "interrupted"),
        ("something else", "error"),
    ],
)
def test_error_kind(text: str, kind: str) -> None:
    assert classify.error_kind(text) == kind
