# Branch Protection and Pre-Merge Checks

This repository uses GitHub Actions to ensure code quality before merging to `main` or `master` branches.

## Required Checks

### Shell Script Linting

The `Shell Script Linting` workflow automatically runs on:

- Pull requests targeting `main` or `master` branches (including from forks)
- Direct pushes to `main` or `master` branches

This workflow checks:

- Shell script syntax with `shellcheck`
- Code formatting with `shfmt` (2-space indentation, no tabs)
- Optional checks: `checkbashisms`, syntax validation

## Enabling Branch Protection

To make the shell linting check **required** before merging PRs, follow these steps:

1. Go to repository **Settings** → **Branches**
2. Click **Add rule** or edit existing rule for `main`/`master`
3. Configure the following settings:
   - ✅ **Require a pull request before merging**
   - ✅ **Require status checks to pass before merging**
     - Search for and select: `Lint Shell Scripts`
   - ✅ **Require branches to be up to date before merging** (recommended)
   - ✅ **Do not allow bypassing the above settings** (recommended)
4. Click **Create** or **Save changes**

## Running Checks Locally

Before pushing changes, run the linting script locally to catch issues early:

```bash
bash scripts/meta/shell_check.sh
```

This will:

- Install required linters on Arch Linux (if needed)
- Check all shell scripts in the repository
- Report any formatting or syntax issues

To auto-fix formatting issues:

```bash
# Install shfmt if not already installed
# On Arch: sudo pacman -S shfmt
# Or download from: https://github.com/mvdan/sh/releases

# Fix formatting in-place
find . -name "*.sh" -type f | xargs shfmt -w -i 2 -ci -sr -s
```

## What Gets Checked

The workflow validates shell scripts with these extensions or shebangs:

- `*.sh`, `*.bash`, `*.zsh` files
- Executable files with shell shebangs (`#!/bin/bash`, `#!/bin/sh`, etc.)

## Troubleshooting

If the check fails on your PR:

1. Review the workflow logs to see which files failed
2. Run `bash scripts/meta/shell_check.sh` locally to reproduce
3. Fix the issues (usually formatting with `shfmt -w -i 2 -ci -sr -s`)
4. Commit and push the fixes

The workflow will automatically re-run on new commits to the PR.
