#!/usr/bin/env bash
# Verify repository readiness before branch-changing Git operations. This script is read-only.

set -u

usage() {
  cat <<'EOF'
Usage: task-preflight.sh --repo <path> [--repo <path> ...] --base <branch> --branch <branch>

Checks that each repository is valid, has a clean worktree, contains the base branch,
and does not already contain the target branch. Performs no write operations.
EOF
}

base_branch=""
target_branch=""
repos=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "ERROR: --repo requires a path" >&2; exit 2; }
      repos+=("$2")
      shift 2
      ;;
    --base)
      [[ $# -ge 2 ]] || { echo "ERROR: --base requires a branch name" >&2; exit 2; }
      base_branch="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { echo "ERROR: --branch requires a branch name" >&2; exit 2; }
      target_branch="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ ${#repos[@]} -gt 0 ]] || { echo "ERROR: specify at least one --repo" >&2; exit 2; }
[[ -n "$base_branch" ]] || { echo "ERROR: specify --base" >&2; exit 2; }
[[ -n "$target_branch" ]] || { echo "ERROR: specify --branch" >&2; exit 2; }

blockers=0

for repo in "${repos[@]}"; do
  echo "== $repo =="

  if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "BLOCKER: not a Git working tree"
    blockers=1
    continue
  fi

  current_branch="$(git -C "$repo" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  [[ -n "$current_branch" ]] || current_branch="DETACHED"
  echo "Current branch: $current_branch"

  if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
    echo "BLOCKER: worktree has uncommitted changes"
    blockers=1
  else
    echo "Worktree: clean"
  fi

  if git -C "$repo" show-ref --verify --quiet "refs/heads/$base_branch"; then
    echo "Base branch: local $base_branch"
  elif git -C "$repo" show-ref --verify --quiet "refs/remotes/origin/$base_branch"; then
    echo "Base branch: origin/$base_branch"
  else
    echo "BLOCKER: base branch '$base_branch' was not found locally or in origin"
    blockers=1
  fi

  if git -C "$repo" show-ref --verify --quiet "refs/heads/$target_branch" \
    || git -C "$repo" show-ref --verify --quiet "refs/remotes/origin/$target_branch"; then
    echo "BLOCKER: target branch '$target_branch' already exists"
    blockers=1
  else
    echo "Target branch: available ($target_branch)"
  fi
done

if [[ "$blockers" -ne 0 ]]; then
  echo "Preflight failed: resolve the blockers before Git write operations." >&2
  exit 1
fi

echo "Preflight passed. No files or Git state were changed."
