# Working safely in a shared `~/testsAndMisc` checkout

Split out of `refactor_claude_todo_resume.md` (which hit the 250-line cap it
exists to enforce). Nothing here is specific to the file-length refactor -- it
applies to any long session in this tree.

## Check for another agent FIRST

A past session collided with a second Claude from
`~/.claude/scripts/claude-autoresume.sh` on the same tree: shared git index, so
its files landed in the other's staging area, it won a commit race, then hung
for 17 minutes on an API request with no read timeout. **Run this before
touching the index**, and `kill` anything live (it commits in-flight work on
the way out):

```bash
pgrep -af 'claude -p' | grep -v grep     # autoresume runs `claude -p ... --continue`
ps -o pid=,etime=,time= -p <pid>         # 7s CPU over 17min = not working
pgrep -P <pid> -a                        # only MCP servers = no command running
ss -tnp | grep <pid>                     # ESTAB to :443 with 0/0 queued = half-open
```

**If the tree looks suspiciously clean**, killing a process mid-`pre-commit`
stranded the changes it stashed. Recover them, do not retype them:
`ls -lt ~/.cache/pre-commit/patch* | head` then `git apply` the newest.
