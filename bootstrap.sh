#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [codex|claude|opencode|all]

Downloads or fast-forward updates dev-task-workflow, then installs its skills.
The default target is "all".

Environment overrides:
  DEV_TASK_WORKFLOW_INSTALL_DIR  Checkout location
  DEV_TASK_WORKFLOW_REPOSITORY   Git repository URL
  DEV_TASK_WORKFLOW_BRANCH       Git branch or tag (default: master)
EOF
}

if [ "$#" -gt 1 ]; then
  usage >&2
  exit 2
fi

selection=${1:-all}
case "$selection" in
  codex|claude|opencode|all) ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

: "${HOME:?HOME must be set}"

command -v git >/dev/null 2>&1 || {
  echo "ERROR: git is required" >&2
  exit 1
}

repository_identity() {
  repository_url=${1%.git}
  case "$repository_url" in
    https://github.com/*) printf '%s\n' "${repository_url#https://github.com/}" ;;
    http://github.com/*) printf '%s\n' "${repository_url#http://github.com/}" ;;
    git@github.com:*) printf '%s\n' "${repository_url#git@github.com:}" ;;
    ssh://git@github.com/*) printf '%s\n' "${repository_url#ssh://git@github.com/}" ;;
    *) printf '%s\n' "$repository_url" ;;
  esac
}

data_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_dir=${DEV_TASK_WORKFLOW_INSTALL_DIR:-"$data_dir/dev-task-workflow"}
repository=${DEV_TASK_WORKFLOW_REPOSITORY:-"https://github.com/arturpanteleev/dev-task-workflow.git"}
branch=${DEV_TASK_WORKFLOW_BRANCH:-master}

if [ -e "$install_dir" ]; then
  if ! git -C "$install_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: install location exists but is not a Git checkout: $install_dir" >&2
    exit 1
  fi

  current_repository=$(git -C "$install_dir" remote get-url origin 2>/dev/null || true)
  current_repository_identity=$(repository_identity "$current_repository")
  expected_repository_identity=$(repository_identity "$repository")
  if [ -z "$current_repository_identity" ] || [ "$current_repository_identity" != "$expected_repository_identity" ]; then
    echo "ERROR: install checkout has an unexpected origin: $current_repository" >&2
    echo "Expected: $repository" >&2
    exit 1
  fi

  if ! git -C "$install_dir" diff --quiet ||
     ! git -C "$install_dir" diff --cached --quiet ||
     [ -n "$(git -C "$install_dir" ls-files --others --exclude-standard)" ]; then
    echo "ERROR: install checkout has local changes: $install_dir" >&2
    echo "Commit, move, or remove them before updating." >&2
    exit 1
  fi

  echo "Updating dev-task-workflow in $install_dir"
  git -C "$install_dir" fetch --prune origin "$branch"
  git -C "$install_dir" merge --ff-only FETCH_HEAD
else
  mkdir -p "$(dirname "$install_dir")"
  echo "Downloading dev-task-workflow into $install_dir"
  git clone --depth 1 --branch "$branch" "$repository" "$install_dir"
fi

exec "$install_dir/install.sh" "$selection"
