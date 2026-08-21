# Схема `.workflow-state.json`

Файл состояния оркестратора — единственный источник истины о прогрессе этапов. Создаётся перед первым этапом, обновляется после каждого этапа, читается при старте для возобновления после обрыва сессии. Не используется в итоговом отчёте — для этого есть `report-data.json`.

## Пример

```json
{
  "schema_version": 1,
  "task_id": "DEV-42",
  "artifact_dir": "/abs/path/artifacts",
  "approval_mode": "auto",
  "status": "in_progress",
  "current_stage": "implementation",
  "completed_stages": ["init", "product-analysis", "approval-proposal", "technical-planning", "approval-spec"],
  "last_error": null,
  "resumable": true
}
```

## Поля

| Поле | Тип | Описание |
| --- | --- | --- |
| `schema_version` | int | Всегда `1` |
| `task_id` | string | Идентификатор задачи (`TASK-ID`) |
| `artifact_dir` | string | Абсолютный путь к каталогу артефактов задачи |
| `approval_mode` | string | `manual` или `auto`; обновляется при смене режима пользователем |
| `status` | string | `in_progress`, `blocked` или `completed` |
| `current_stage` | string \| null | Этап, который должен выполниться следующим; `null` после полного завершения |
| `completed_stages` | array\<string\> | Этапы, успешно завершённые в этой сессии, в порядке прохождения |
| `last_error` | string \| null | Описание последнего блокера или ошибки; `null`, если их не было |
| `return_counts` | object \| null | Опционально; счётчик возвратов на этап (`{"implementation": 1}`); инкрементируется при каждом `back_to_*`, при возобновлении не сбрасывается |
| `resumable` | bool | `true`, пока workflow имеет смысл возобновлять; `false` после полного завершения |

## Допустимые этапы

`init`, `product-analysis`, `approval-proposal`, `technical-planning`, `approval-spec`, `implementation`, `verification`, `code-review`, `delivery`, `reporting`, `retrospective`.

## Правила обновления

* Перед этапом 1 создай файл с `status: "in_progress"`, `current_stage: "product-analysis"`, `completed_stages: ["init"]`, `last_error: null`, `resumable: true`.
* После успешного завершения этапа добавь его в `completed_stages` и установи `current_stage` на следующий этап.
* При блокере или ошибке установи `status: "blocked"`, `current_stage` — этап, на котором остановились, `last_error` — краткое описание проблемы, `resumable: true`.
* После успешного `retrospective` установи `status: "completed"`, `current_stage: null`, `resumable: false`.
* `completed_stages` никогда не удаляй и не переупорядочивай: это история выполнения.
* При каждом возврате на этап (`back_to_*`) увеличь счётчик этого этапа в `return_counts`; больше трёх возвратов на один этап не допускается — останови workflow.

### Источник данных: результат этапа

Статус и ошибку бери из файла результата этапа `stage-results/{stage}.json` (схема — в `references/stage-result-schema.md`), а не из пересказа навыка. `status = ok`/`skipped` → успех и следующий этап; `status = error`/`blocked` → `status: "blocked"`, `last_error` из `error.message`. Файлы `stage-results` — рабочие артефакты этапа, в состояние не записываются и удаляются перед повторным запуском этапа.
