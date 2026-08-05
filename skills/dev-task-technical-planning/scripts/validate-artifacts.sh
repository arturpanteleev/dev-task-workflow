#!/usr/bin/env bash
# Проверяй обязательные заголовки в артефактах workflow. Скрипт выполняет только чтение.

set -u

usage() {
  cat <<'EOF'
Использование:
  validate-artifacts.sh --task-dir <каталог>
  validate-artifacts.sh [--proposal <путь>] [--spec <путь>]

Проверяет, что один или оба указанных артефакта существуют и содержат обязательные заголовки.
EOF
}

task_dir=""
proposal=""
spec=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-dir)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --task-dir требует каталог" >&2; exit 2; }
      task_dir="$2"
      shift 2
      ;;
    --proposal)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --proposal требует путь" >&2; exit 2; }
      proposal="$2"
      shift 2
      ;;
    --spec)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --spec требует путь" >&2; exit 2; }
      spec="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ОШИБКА: неизвестный аргумент: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "$task_dir" ]]; then
  [[ -z "$proposal" && -z "$spec" ]] || { echo "ОШИБКА: не сочетайте --task-dir с --proposal или --spec" >&2; exit 2; }
  proposal="$task_dir/proposal.md"
  spec="$task_dir/spec.md"
fi

[[ -n "$proposal" || -n "$spec" ]] || { usage >&2; exit 2; }

errors=0

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "БЛОКЕР: отсутствует файл: $path"
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
    echo "БЛОКЕР: в '$path' отсутствует заголовок: $heading"
    errors=1
  fi
}

if [[ -n "$proposal" ]]; then
  require_file "$proposal" || true
fi

if [[ -n "$spec" ]]; then
  require_file "$spec" || true
fi

if [[ -f "$proposal" ]]; then
  echo "== $proposal =="
  require_heading "$proposal" "Краткое описание задачи"
  require_heading "$proposal" "Бизнес-цель"
  require_heading "$proposal" "Происхождение и обнаружение проблемы"
  require_heading "$proposal" "Контекст и пользователи"
  require_heading "$proposal" "Пользовательские сценарии"
  require_heading "$proposal" "Scope"
  require_heading "$proposal" "Out of scope"
  require_heading "$proposal" "Зафиксированные продуктовые требования"
  require_heading "$proposal" "Нефункциональные требования"
  require_heading "$proposal" "Зависимости, rollout и откат"
  require_heading "$proposal" "Спорные моменты и принятые решения"
  require_heading "$proposal" "Допущения и открытые вопросы"
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
  echo "Проверка артефактов не пройдена." >&2
  exit 1
fi

echo "Проверка артефактов пройдена. Файлы не изменялись."
