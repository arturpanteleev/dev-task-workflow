# Схема результата этапа `stage-results/{stage}.json`

Машиночитаемый контракт передачи результата от специализированного навыка оркестратору. Каждый суб-навык в конце работы записывает файл `{artifact_dir}/{TASK-ID}/stage-results/{stage}.json`. Оркестратор читает его, валидирует по этой схеме и зеркалит в `.workflow-state.json` и `report-data.json`, не парся свободный текст сообщений.

Файл — рабочий артефакт этапа. Перед вызовом этапа оркестратор удаляет файл его результата, чтобы не принять устаревший результат за свежий. При прямом вызове навыка без оркестратора файл можно не создавать.

## Пример (успех)

```json
{
  "schema_version": 1,
  "stage": "implementation",
  "status": "ok",
  "summary": "Preflight пройден, 4 файла изменено, 12 тестов зелёные",
  "artifacts": [".../spec.md", "src/app.py", "tests/test_app.py"],
  "duration_ms": null,
  "warnings": ["Генерация схемы не перепроверялась на CI"],
  "error": null,
  "suggested_next": "verification"
}
```

## Пример (ошибка)

```json
{
  "schema_version": 1,
  "stage": "implementation",
  "status": "error",
  "summary": "Preflight: ветка feature/dev-task/DEV-42 уже существует",
  "artifacts": [],
  "duration_ms": null,
  "warnings": [],
  "error": {
    "code": "preflight_blocked",
    "message": "Ветка feature/dev-task/DEV-42 уже существует, сначала слейте или удалите её",
    "retryable": false
  },
  "suggested_next": "await_user"
}
```

## Поля

| Поле | Тип | Описание |
| --- | --- | --- |
| `schema_version` | int | Всегда `1` |
| `stage` | string | Идентификатор этапа; должен совпадать с именем файла |
| `status` | string | `ok`, `blocked`, `error` или `skipped` |
| `summary` | string | Краткое описание результата для пользователя и `workflow_trace` |
| `artifacts` | array\<string\> | Созданные или изменённые артефакты; пустой массив, если их нет |
| `duration_ms` | int \| null | Опционально; длительность этапа считает оркестратор по паре `started`/итоговой записи `workflow_trace`, значение из файла не требуется |
| `warnings` | array\<string\> | Неблокирующие замечания; пустой массив, если их нет |
| `error` | object \| null | Обязателен при `status = error` или `blocked`; иначе `null` |
| `suggested_next` | string \| null | Куда переходить дальше; см. допустимые значения |

## Объект `error`

```json
{
  "code": "preflight_blocked",
  "message": "Человекочитаемое описание",
  "retryable": false
}
```

* `code` — один из допустимых кодов (ниже);
* `message` — описание проблемы;
* `retryable` — имеет ли смысл повторять этап без изменений.

## Коды ошибок и действия оркестратора

| code | Действие оркестратора |
| --- | --- |
| `preflight_blocked` | Показать причину, `suggested_next = await_user`; Git-операции не выполняются |
| `requirements_error` | Вернуться на продуктовый анализ, `suggested_next = back_to_product_analysis` |
| `test_failed` | Вернуться на реализацию, `suggested_next = back_to_implementation` |
| `review_required` | Исправить обязательные замечания, `suggested_next = back_to_implementation` |
| `missing_input` | Запросить недостающие входы у пользователя, `suggested_next = await_user` |
| `user_cancelled` | Остановить workflow, `suggested_next = stop` |
| `unknown` | Один retry этапа, при повторе — остановить и показать проблему |

## Допустимые `suggested_next`

`approval-proposal`, `approval-spec`, `verification`, `code-review`, `delivery`, `reporting`, `back_to_product_analysis`, `back_to_implementation`, `await_user`, `stop`, `null`.

Для `status = ok` `suggested_next` указывает следующий этап по плану (после `reporting` — `null`). Для `status = blocked` или `error` — действие из таблицы выше. Для `status = skipped` — следующий этап по плану (например, `code-review` → `delivery`).

## Соответствие `status` и событий `workflow_trace`

| status | event в `workflow_trace` |
| --- | --- |
| `ok` | `completed` |
| `blocked` | `blocked` |
| `error` | `error` |
| `skipped` | `skipped` |

## Правила валидации (оркестратор)

1. Файл отсутствует или содержит невалидный JSON — считать `status = error`, `error.code = unknown`.
2. `stage` в файле не совпадает с именем файла или ожидаемым этапом — считать `status = error`, `error.code = unknown`.
3. `error` не заполнен при `status = error` или `blocked` — считать `status = error`, `error.code = unknown`.
4. Отсутствие или невалидное значение `duration_ms` ошибкой не считается: длительность фиксирует оркестратор.
5. В остальных случаях принять результат как есть и действовать по `suggested_next`.
