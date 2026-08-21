#!/usr/bin/env bash
# Проверяй обязательные разделы в артефактах workflow. Скрипт выполняет только чтение.
#
# Для каждого артефакта проверяется:
# 1. наличие всех обязательных заголовков (допустим русский или английский вариант);
# 2. отсутствие незаполненных HTML-комментариев шаблона;
# 3. непустое содержимое под каждым обязательным заголовком.

set -u

usage() {
  cat <<'EOF'
Использование:
  validate-artifacts.sh --task-dir <каталог>
  validate-artifacts.sh [--proposal <путь>] [--spec <путь>]

Проверяет, что указанные артефакты существуют, содержат обязательные заголовки
(на русском или английском языке), не содержат HTML-комментариев шаблона
и имеют непустое содержимое в каждом обязательном разделе.
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

# Формат элемента: "русский заголовок|english heading"
PROPOSAL_SECTIONS=(
  "Краткое описание задачи|Task summary"
  "Бизнес-цель|Business goal"
  "Происхождение и обнаружение проблемы|Problem origin and discovery"
  "Контекст и пользователи|Context and users"
  "Пользовательские сценарии|User scenarios"
  "Scope|Scope"
  "Out of scope|Out of scope"
  "Зафиксированные продуктовые требования|Product requirements"
  "Нефункциональные требования|Non-functional requirements"
  "Зависимости, rollout и откат|Dependencies, rollout and rollback"
  "Спорные моменты и принятые решения|Open questions and decisions"
  "Допущения и открытые вопросы|Assumptions and open questions"
  "Acceptance Criteria|Acceptance criteria"
)

SPEC_SECTIONS=(
  "Затронутые репозитории и компоненты|Affected repositories and components"
  "Выбранное техническое решение|Selected technical solution"
  "Альтернативы и почему не выбраны|Alternatives considered"
  "Изменения по файлам или модулям|Changes by file or module"
  "Изменения контрактов и данных|Contract and data changes"
  "Необходимые проверки|Required checks"
  "Риски и способы их снижения|Risks and mitigations"
  "Порядок реализации|Implementation order"
)

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "БЛОКЕР: отсутствует файл: $path"
    errors=1
    return 1
  fi
}

check_artifact() {
  local path="$1"; shift
  local item label pattern sec_re re_lc body

  echo "== $path =="

  if grep -q '<!--' "$path"; then
    echo "БЛОКЕР: остались незаполненные комментарии шаблона (<!-- -->)"
    errors=1
  fi

  for item in "$@"; do
    label="${item%%|*}"
    pattern="${item#*|}"
    sec_re="^[[:space:]]*#{1,6}[[:space:]]+(${label}|${pattern})[[:space:]]*$"

    if ! grep -Eiq "$sec_re" "$path"; then
      echo "БЛОКЕР: отсутствует заголовок: $label / $pattern"
      errors=1
      continue
    fi
    echo "OK: $label / $pattern"

    # Содержимое раздела: от заголовка до следующего заголовка,
    # без HTML-комментариев (в том числе многострочных) и пустых строк.
    re_lc="$(printf '%s' "$sec_re" | tr '[:upper:]' '[:lower:]')"
    body="$(awk -v re="$re_lc" '
      tolower($0) ~ re {insec=1; next}
      /^[[:space:]]*#/ {insec=0}
      insec {print}
    ' "$path" \
      | sed -e '/^[[:space:]]*<!--/,/-->[[:space:]]*$/d' -e 's/<!--[^>]*-->//g' \
      | grep -E '[^[:space:]]' || true)"

    if [[ -z "$body" ]]; then
      echo "БЛОКЕР: раздел пуст: $label / $pattern"
      errors=1
    fi
  done
}

if [[ -n "$proposal" ]]; then
  if require_file "$proposal"; then
    check_artifact "$proposal" "${PROPOSAL_SECTIONS[@]}"
  fi
fi

if [[ -n "$spec" ]]; then
  if require_file "$spec"; then
    check_artifact "$spec" "${SPEC_SECTIONS[@]}"
  fi
fi

if [[ "$errors" -ne 0 ]]; then
  echo "Проверка артефактов не пройдена." >&2
  exit 1
fi

echo "Проверка артефактов пройдена. Файлы не изменялись."
