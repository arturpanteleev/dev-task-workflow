# dev-task-workflow

Переносимый поэтапный workflow для задач разработки от анализа требований до доставки изменений и итогового отчёта.

Он разделяет продуктовый анализ, техническое планирование, реализацию, проверку, независимое code review, доставку и итоговый HTML-отчёт. Основной skill управляет последовательностью этапов и поддерживает ручные подтверждения или автоматические quality gates перед реализацией.

## Состав

- `dev-task-workflow` — оркестратор;
- `dev-task-product-analysis`;
- `dev-task-technical-planning`;
- `dev-task-implementation`;
- `dev-task-verification`;
- `dev-task-code-review`;
- `dev-task-delivery`;
- `dev-task-reporting`.

Каждый skill использует переносимую структуру Agent Skills: каталог с именем skill, файл `SKILL.md` и при необходимости каталоги `assets/` и `scripts/`.

## Быстрая установка и обновление

Рекомендуемый вариант — установить skills сразу для Codex, Claude Code и OpenCode. Скопируйте команду кнопкой в правом верхнем углу блока и запустите её в терминале:

```sh
curl -fsSL https://raw.githubusercontent.com/arturpanteleev/dev-task-workflow/master/bootstrap.sh | sh -s -- all
```

Тот же bootstrap можно запустить только для одного агента:

```sh
# Codex
curl -fsSL https://raw.githubusercontent.com/arturpanteleev/dev-task-workflow/master/bootstrap.sh | sh -s -- codex

# Claude Code
curl -fsSL https://raw.githubusercontent.com/arturpanteleev/dev-task-workflow/master/bootstrap.sh | sh -s -- claude

# OpenCode
curl -fsSL https://raw.githubusercontent.com/arturpanteleev/dev-task-workflow/master/bootstrap.sh | sh -s -- opencode
```

Нужны `git` и `curl`. Перед запуском через pipe можно [открыть и проверить `bootstrap.sh`](https://raw.githubusercontent.com/arturpanteleev/dev-task-workflow/master/bootstrap.sh).

Bootstrap хранит служебный checkout в `~/.local/share/dev-task-workflow`. При первом запуске он клонирует репозиторий, при следующих — выполняет только fast-forward обновление и снова запускает идемпотентный установщик. Поэтому та же команда одновременно устанавливает и обновляет workflow.

Skills устанавливаются в официальные пользовательские каталоги:

| Агент | Глобальный каталог skills |
| --- | --- |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills` |
| [OpenCode](https://opencode.ai/docs/skills/) | `~/.config/opencode/skills` |

Установщик создаёт символические ссылки на skills в checkout. Повторный запуск:

- оставляет актуальные ссылки без изменений;
- обновляет ссылки, созданные из предыдущей копии `dev-task-workflow`;
- никогда не заменяет обычные файлы, каталоги или посторонние ссылки с совпадающими именами;
- сначала проверяет все назначения, поэтому `all` не начинает установку, если хотя бы в одном агенте найден конфликт.

Если в служебном checkout есть локальные изменения или история разошлась с `origin`, безопасное fast-forward обновление остановится и покажет ошибку вместо перезаписи изменений.

После первой установки перезапустите активные сессии агентов, чтобы они перечитали глобальные каталоги skills.

### Ручная установка

Если вы хотите сами выбирать расположение checkout:

```sh
git clone https://github.com/arturpanteleev/dev-task-workflow.git
cd dev-task-workflow
./install.sh all
```

Для последующего обновления:

```sh
git pull --ff-only
./install.sh all
```

Вместо `all` можно передать `codex`, `claude` или `opencode`. Для установки на уровне отдельного репозитория создайте ссылки на подкаталоги `skills/` в каталоге агента: `.agents/skills/`, `.claude/skills/` или `.opencode/skills/`.

## Workflow

Используйте `dev-task-workflow`, когда пользователь просит сделать, выполнить, реализовать или проработать задачу, передаёт её номер либо ссылку, похожую на задачу Jira. В начале skill единым блоком собирает недостающие параметры: идентификатор задачи, каталог для артефактов вне затронутых репозиториев, режим подтверждений, репозитории и ветки.

В `manual` пользователь подтверждает `proposal.md` и `spec.md`. В `auto` оркестратор валидирует их, проводит self-review, самостоятельно фиксирует внутреннее подтверждение и продолжает работу. Существенные продуктовые вопросы всё равно адресуются пользователю, а `commit`, `push` и создание pull request требуют отдельного явного разрешения.

Продуктовый анализ по умолчанию работает в `grill-me` режиме: исследует доступные источники, задаёт несколько коротких раундов предметных вопросов, проверяет ответы контрпримерами и фиксирует допущения.

После успешного создания PR этап `dev-task-reporting` локально создаёт `{artifact_dir}/{TASK-ID}/report-data.json` и адаптивный `{artifact_dir}/{TASK-ID}/report.html`. Отчёт связывает бизнес-проблему, решения, технические изменения, проверки, риски, commits и PR. Публикация отчёта не выполняется.

По умолчанию все артефакты и сообщения создаются на русском языке. Другой язык используется только когда он явно задан в правилах проекта или репозитория.

Workflow не выполняет commit, push или создание pull request без явного подтверждения пользователя.

## Лицензия

[MIT](LICENSE)
