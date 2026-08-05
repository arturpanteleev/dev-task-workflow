#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage: ./install.sh <codex|claude|opencode|all>

Installs every bundled skill using symbolic links. Re-running the command is
safe: links from an older dev-task-workflow checkout are updated, while regular
files, directories, and unrelated links are never replaced.
EOF
}

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skills_dir="$root_dir/skills"

: "${HOME:?HOME must be set}"

codex_dir=${DEV_TASK_WORKFLOW_CODEX_SKILLS_DIR:-"$HOME/.agents/skills"}
claude_dir=${DEV_TASK_WORKFLOW_CLAUDE_SKILLS_DIR:-"$HOME/.claude/skills"}
opencode_dir=${DEV_TASK_WORKFLOW_OPENCODE_SKILLS_DIR:-"$HOME/.config/opencode/skills"}

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

root_repository=""
if command -v git >/dev/null 2>&1; then
  root_repository=$(git -C "$root_dir" remote get-url origin 2>/dev/null || true)
fi
root_repository_identity=$(repository_identity "$root_repository")

is_previous_workflow_link() {
  target_path="$1"
  current_source="$2"
  skill_name="$3"

  current_name=$(basename "$current_source")
  current_parent=$(basename "$(dirname "$current_source")")
  if [ "$current_name" != "$skill_name" ] || [ "$current_parent" != "skills" ]; then
    return 1
  fi

  # A broken link in the expected bundle layout is safe to repair.
  if [ ! -e "$target_path" ]; then
    return 0
  fi

  # Older versions of this installer created absolute links into a Git checkout.
  case "$current_source" in
    /*) ;;
    *) return 1 ;;
  esac

  [ -n "$root_repository_identity" ] || return 1
  previous_root=$(dirname "$(dirname "$current_source")")
  previous_repository=$(git -C "$previous_root" remote get-url origin 2>/dev/null || true)
  previous_repository_identity=$(repository_identity "$previous_repository")
  [ -n "$previous_repository_identity" ] || return 1
  [ "$previous_repository_identity" = "$root_repository_identity" ]
}

for_each_skill() {
  callback="$1"
  callback_arg="$2"
  found_skill=false

  for source_dir in "$skills_dir"/*; do
    [ -d "$source_dir" ] || continue
    [ -f "$source_dir/SKILL.md" ] || continue
    found_skill=true
    "$callback" "$callback_arg" "$source_dir"
  done

  if [ "$found_skill" = false ]; then
    echo "ERROR: no skills found in $skills_dir" >&2
    return 1
  fi
}

preflight_skill() {
  target_dir="$1"
  source_dir="$2"
  skill_name=$(basename "$source_dir")
  target_path="$target_dir/$skill_name"

  if [ ! -e "$target_path" ] && [ ! -L "$target_path" ]; then
    return 0
  fi

  if [ ! -L "$target_path" ]; then
    echo "ERROR: refusing to replace existing path: $target_path" >&2
    return 1
  fi

  current_source=$(readlink "$target_path")
  if [ "$current_source" = "$source_dir" ]; then
    return 0
  fi

  if ! is_previous_workflow_link "$target_path" "$current_source" "$skill_name"; then
    echo "ERROR: refusing to replace unrelated symlink: $target_path -> $current_source" >&2
    return 1
  fi
}

preflight_target() {
  target_dir="$1"

  if [ -e "$target_dir" ] && [ ! -d "$target_dir" ]; then
    echo "ERROR: skills destination is not a directory: $target_dir" >&2
    return 1
  fi

  for_each_skill preflight_skill "$target_dir"
}

install_skill() {
  target_dir="$1"
  source_dir="$2"
  skill_name=$(basename "$source_dir")
  target_path="$target_dir/$skill_name"

  if [ ! -e "$target_path" ] && [ ! -L "$target_path" ]; then
    ln -s "$source_dir" "$target_path"
    echo "INSTALLED  $target_path"
    return 0
  fi

  if [ ! -L "$target_path" ]; then
    echo "ERROR: destination changed after preflight: $target_path" >&2
    return 1
  fi

  current_source=$(readlink "$target_path")
  if [ "$current_source" = "$source_dir" ]; then
    echo "UP TO DATE $target_path"
    return 0
  fi

  temporary_path="$target_path.dev-task-workflow.$$"
  if [ -e "$temporary_path" ] || [ -L "$temporary_path" ]; then
    echo "ERROR: temporary path already exists: $temporary_path" >&2
    return 1
  fi

  ln -s "$source_dir" "$temporary_path"
  if [ ! -L "$target_path" ] || [ "$(readlink "$target_path")" != "$current_source" ]; then
    rm "$temporary_path"
    echo "ERROR: destination changed after preflight: $target_path" >&2
    return 1
  fi
  if ! rm "$target_path"; then
    rm "$temporary_path"
    return 1
  fi
  if ! mv "$temporary_path" "$target_path"; then
    ln -s "$current_source" "$target_path" 2>/dev/null || true
    echo "ERROR: could not finish updating $target_path" >&2
    return 1
  fi

  echo "UPDATED    $target_path"
}

install_target() {
  target_dir="$1"
  mkdir -p "$target_dir"
  for_each_skill install_skill "$target_dir"
}

preflight_selection() {
  case "$1" in
    codex) preflight_target "$codex_dir" ;;
    claude) preflight_target "$claude_dir" ;;
    opencode) preflight_target "$opencode_dir" ;;
    all)
      preflight_target "$codex_dir"
      preflight_target "$claude_dir"
      preflight_target "$opencode_dir"
      ;;
  esac
}

install_selection() {
  case "$1" in
    codex) install_target "$codex_dir" ;;
    claude) install_target "$claude_dir" ;;
    opencode) install_target "$opencode_dir" ;;
    all)
      install_target "$codex_dir"
      install_target "$claude_dir"
      install_target "$opencode_dir"
      ;;
  esac
}

[ "$#" -eq 1 ] || { usage >&2; exit 2; }

case "$1" in
  codex|claude|opencode|all)
    preflight_selection "$1"
    install_selection "$1"
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
