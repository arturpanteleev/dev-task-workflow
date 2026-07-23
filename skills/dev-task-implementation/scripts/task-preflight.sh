#!/usr/bin/env bash
# Проверяй готовность репозитория перед Git-операциями смены ветки. Скрипт выполняет только чтение.

set -u

usage() {
  cat <<'EOF'
Использование: task-preflight.sh --repo <путь> [--repo <путь> ...] --base <ветка> --branch <ветка>

Проверяет, что каждый репозиторий корректен, имеет чистую рабочую директорию,
содержит базовую ветку и не содержит целевую ветку. Не выполняет операций записи.
EOF
}

base_branch=""
target_branch=""
repos=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --repo требует путь" >&2; exit 2; }
      repos+=("$2")
      shift 2
      ;;
    --base)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --base требует имя ветки" >&2; exit 2; }
      base_branch="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { echo "ОШИБКА: --branch требует имя ветки" >&2; exit 2; }
      target_branch="$2"
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

[[ ${#repos[@]} -gt 0 ]] || { echo "ОШИБКА: укажите хотя бы один --repo" >&2; exit 2; }
[[ -n "$base_branch" ]] || { echo "ОШИБКА: укажите --base" >&2; exit 2; }
[[ -n "$target_branch" ]] || { echo "ОШИБКА: укажите --branch" >&2; exit 2; }

blockers=0

for repo in "${repos[@]}"; do
  echo "== $repo =="

  if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "БЛОКЕР: это не рабочая директория Git"
    blockers=1
    continue
  fi

  current_branch="$(git -C "$repo" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  [[ -n "$current_branch" ]] || current_branch="DETACHED"
  echo "Текущая ветка: $current_branch"

  if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
    echo "БЛОКЕР: в рабочей директории есть незакоммиченные изменения"
    blockers=1
  else
    echo "Рабочая директория: чистая"
  fi

  if git -C "$repo" show-ref --verify --quiet "refs/heads/$base_branch"; then
    echo "Базовая ветка: локальная $base_branch"
  elif git -C "$repo" show-ref --verify --quiet "refs/remotes/origin/$base_branch"; then
    echo "Базовая ветка: origin/$base_branch"
  else
    echo "БЛОКЕР: базовая ветка '$base_branch' не найдена локально или в origin"
    blockers=1
  fi

  if git -C "$repo" show-ref --verify --quiet "refs/heads/$target_branch" \
    || git -C "$repo" show-ref --verify --quiet "refs/remotes/origin/$target_branch"; then
    echo "БЛОКЕР: целевая ветка '$target_branch' уже существует"
    blockers=1
  else
    echo "Целевая ветка: доступна ($target_branch)"
  fi
done

if [[ "$blockers" -ne 0 ]]; then
  echo "Предварительная проверка не пройдена: устраните блокеры до Git-операций записи." >&2
  exit 1
fi

echo "Предварительная проверка пройдена. Файлы и состояние Git не изменялись."
