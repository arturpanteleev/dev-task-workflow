# Схема `report-data.json`

Используй UTF-8 JSON с `schema_version: 1`. Все перечисленные поля обязательны, даже если массивы пусты. Неизвестное текстовое значение записывай как `Не зафиксировано`, ещё не измеренный эффект — как `Не измерялось`.

## Содержание

* [Корневой объект](#корневой-объект)
* [Метаданные и резюме](#метаданные-и-резюме)
* [Бизнес-контекст и решение](#бизнес-контекст-и-решение)
* [Контроль автономной работы](#контроль-автономной-работы)
* [Техническая реализация](#техническая-реализация)
* [Проверки и review](#проверки-и-review)
* [Риски, шаги и ссылки](#риски-шаги-и-ссылки)

## Корневой объект

```json
{
  "schema_version": 1,
  "task": {},
  "summary": {},
  "attention": [],
  "business": {},
  "solution": {},
  "oversight": {},
  "technical": {},
  "validation": {},
  "risks": [],
  "next_steps": [],
  "links": []
}
```

## Метаданные и резюме

`task`:

* `id`, `title`, `generated_at` — непустые строки;
* `status` — `pr_created`;
* `approval_mode` — `manual` или `auto`;
* `source_url` — безопасный URL или `Не зафиксировано`.

`summary` содержит непустые строки `business_problem`, `solution` и `outcome`.

`attention` — массив объектов:

```json
{"severity": "warning", "title": "Что проверить", "detail": "Почему это важно"}
```

`severity`: `info`, `warning` или `critical`.

## Бизнес-контекст и решение

`business`:

* `origin` — как обнаружили проблему;
* `users` — массив затронутых ролей или групп;
* `confirmed_facts` — массив подтверждённых фактами или источниками утверждений;
* `assumptions` — массив явно обозначенных допущений;
* `impact` — наблюдаемое влияние проблемы;
* `expected_effect` — ожидаемый эффект изменения;
* `success_signal` — как позднее определить успех;
* `measured_effect` — фактически измеренный эффект либо `Не измерялось`.

`solution`:

* `before` и `after` — массивы шагов процесса до и после изменения;
* `approach` и `rationale` — непустые строки;
* `alternatives` — массив объектов `name` и `reason_not_chosen`.

## Контроль автономной работы

`oversight`:

* `approval_gates` — объекты `stage`, `status`, `evidence`; статус: `auto_approved` или `user_approved`;
* `autonomous_decisions` — объекты `decision`, `rationale`, `source`;
* `plan_deviations` — объекты `deviation`, `reason`, `impact`;
* `unverified` — массив непроверенных сценариев.

Не скрывай отсутствие отклонений: используй пустой массив, чтобы отчёт явно показал это состояние.

## Техническая реализация

`technical.repositories` — непустой массив:

```json
{
  "name": "owner/repository",
  "path": "/absolute/path/to/repository",
  "base_branch": "main",
  "target_branch": "feature/task",
  "commit": "0123456789abcdef",
  "pull_request": {
    "number": 42,
    "url": "https://github.com/owner/repository/pull/42",
    "status": "draft"
  },
  "components": ["api", "storage"],
  "changes": ["Добавлена проверка ..."]
}
```

`pull_request.status`: `draft`, `open`, `merged` или `closed`. Для финального запуска каждый репозиторий должен иметь положительный номер PR и безопасный URL.

## Проверки и review

`validation`:

* `acceptance_criteria` — объекты `criterion`, `status`, `evidence`; статус: `passed`, `failed`, `partial`, `not_checked`;
* `checks` — объекты `name`, `status`, `details`; статус: `passed`, `failed`, `skipped`;
* `manual_checks` — объекты того же формата;
* `review_findings` — объекты `severity`, `finding`, `decision`, `resolution`; severity: `required`, `recommended`, `irrelevant`.

## Риски, шаги и ссылки

`risks` — объекты `level`, `title`, `mitigation`; level: `low`, `medium`, `high`, `critical`.

`next_steps` — массив строк. `links` — массив объектов `label`, `url`, `kind`. В `kind` используй `task`, `proposal`, `spec`, `commit`, `pr` или `other`.

Разрешены `http`, `https`, `file` и относительные ссылки. Запрещены исполняемые URL-схемы. Не добавляй в JSON поля с полным diff, сырыми логами, токенами или секретами.
