#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage: ./install.sh <codex|claude|opencode|all>

Creates symlinks for every bundled skill. Existing paths are never replaced.
EOF
}

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skills_dir="$root_dir/skills"

install_to() {
  target_dir="$1"
  mkdir -p "$target_dir"

  for source_dir in "$skills_dir"/*; do
    skill_name=$(basename "$source_dir")
    target_path="$target_dir/$skill_name"

    if [ -e "$target_path" ] || [ -L "$target_path" ]; then
      echo "ERROR: already exists: $target_path" >&2
      return 1
    fi
  done

  for source_dir in "$skills_dir"/*; do
    skill_name=$(basename "$source_dir")
    ln -s "$source_dir" "$target_dir/$skill_name"
  done

  echo "Installed skills into $target_dir"
}

[ "$#" -eq 1 ] || { usage >&2; exit 2; }

case "$1" in
  codex)
    install_to "$HOME/.agents/skills"
    ;;
  claude)
    install_to "$HOME/.claude/skills"
    ;;
  opencode)
    install_to "$HOME/.config/opencode/skills"
    ;;
  all)
    install_to "$HOME/.agents/skills"
    install_to "$HOME/.claude/skills"
    install_to "$HOME/.config/opencode/skills"
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
