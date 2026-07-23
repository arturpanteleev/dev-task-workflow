#!/usr/bin/env bash
# Validate required headings in workflow artifacts. This script is read-only.

set -u

usage() {
  cat <<'EOF'
Usage:
  validate-artifacts.sh --task-dir <directory>
  validate-artifacts.sh --proposal <path> --spec <path>

Checks that proposal.md and spec.md exist and contain required headings.
EOF
}

task_dir=""
proposal=""
spec=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-dir)
      [[ $# -ge 2 ]] || { echo "ERROR: --task-dir requires a directory" >&2; exit 2; }
      task_dir="$2"
      shift 2
      ;;
    --proposal)
      [[ $# -ge 2 ]] || { echo "ERROR: --proposal requires a path" >&2; exit 2; }
      proposal="$2"
      shift 2
      ;;
    --spec)
      [[ $# -ge 2 ]] || { echo "ERROR: --spec requires a path" >&2; exit 2; }
      spec="$2"
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

if [[ -n "$task_dir" ]]; then
  [[ -z "$proposal" && -z "$spec" ]] || { echo "ERROR: do not combine --task-dir with --proposal or --spec" >&2; exit 2; }
  proposal="$task_dir/proposal.md"
  spec="$task_dir/spec.md"
fi

[[ -n "$proposal" && -n "$spec" ]] || { usage >&2; exit 2; }

errors=0

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "BLOCKER: missing file: $path"
    errors=1
    return 1
  fi
}

require_heading() {
  local path="$1"
  local heading="$2"
  if grep -Eiq "^[[:space:]]*#{1,6}[[:space:]]+${heading}[[:space:]]*$" "$path"; then
    echo "OK: $heading"
  else
    echo "BLOCKER: '$path' lacks heading: $heading"
    errors=1
  fi
}

require_file "$proposal" || true
require_file "$spec" || true

if [[ -f "$proposal" ]]; then
  echo "== $proposal =="
  require_heading "$proposal" "Краткое описание задачи"
  require_heading "$proposal" "Бизнес-цель"
  require_heading "$proposal" "Scope"
  require_heading "$proposal" "Out of scope"
  require_heading "$proposal" "Зафиксированные продуктовые требования"
  require_heading "$proposal" "Спорные моменты и принятые решения"
  require_heading "$proposal" "Acceptance Criteria"
fi

if [[ -f "$spec" ]]; then
  echo "== $spec =="
  require_heading "$spec" "Затронутые репозитории и компоненты"
  require_heading "$spec" "Выбранное техническое решение"
  require_heading "$spec" "Изменения по файлам или модулям"
  require_heading "$spec" "Изменения контрактов и данных"
  require_heading "$spec" "Необходимые проверки"
  require_heading "$spec" "Риски и способы их снижения"
  require_heading "$spec" "Порядок реализации"
fi

if [[ "$errors" -ne 0 ]]; then
  echo "Artifact validation failed." >&2
  exit 1
fi

echo "Artifact validation passed. No files were changed."
