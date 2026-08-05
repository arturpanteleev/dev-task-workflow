#!/usr/bin/env python3
"""Validate structured task-report data and the rendered standalone HTML."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ALLOWED_SCHEMES = {"", "http", "https", "file"}
MISSING_VALUES = {"Не зафиксировано", "Не измерялось"}
REQUIRED_HTML_IDS = {
    "executive-summary",
    "attention",
    "business-context",
    "solution",
    "decisions",
    "technical",
    "validation",
    "risks",
    "links",
}


def require_mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: ожидался объект")
        return {}
    return value


def require_list(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path}: ожидался массив")
        return []
    return value


def require_string(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: ожидалась непустая строка")
        return ""
    return value.strip()


def require_integer(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> int:
    value = obj.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{path}.{key}: ожидалось целое число")
        return 0
    return value


def require_enum(
    obj: dict[str, Any], key: str, allowed: set[str], path: str, errors: list[str]
) -> str:
    value = require_string(obj, key, path, errors)
    if value and value not in allowed:
        errors.append(f"{path}.{key}: недопустимое значение '{value}'")
    return value


def validate_url(value: str, path: str, errors: list[str], allow_missing: bool = False) -> None:
    if allow_missing and value in MISSING_VALUES:
        return
    if any(character.isspace() for character in value):
        errors.append(f"{path}: URL содержит пробельные символы")
        return
    scheme = urlsplit(value).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        errors.append(f"{path}: запрещённая URL-схема '{scheme}'")


def validate_string_list(value: Any, path: str, errors: list[str]) -> list[str]:
    items = require_list(value, path, errors)
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}]: ожидалась непустая строка")
    return items


def validate_object_list(
    value: Any,
    fields: tuple[str, ...],
    path: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    items = require_list(value, path, errors)
    result: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        mapping = require_mapping(item, item_path, errors)
        for field in fields:
            require_string(mapping, field, item_path, errors)
        result.append(mapping)
    return result


def find_forbidden_keys(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in {"diff", "raw_diff", "logs", "raw_logs", "token", "secret", "password"} \
                    or normalized.endswith("_token"):
                errors.append(f"{path}.{key}: сырые diff/logs или секреты запрещены")
            find_forbidden_keys(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            find_forbidden_keys(child, f"{path}[{index}]", errors)


def validate_data(data: Any) -> list[str]:
    errors: list[str] = []
    root = require_mapping(data, "$", errors)
    if errors:
        return errors

    if root.get("schema_version") != 1:
        errors.append("$.schema_version: поддерживается только значение 1")

    required_root = {
        "task",
        "summary",
        "attention",
        "business",
        "solution",
        "oversight",
        "technical",
        "validation",
        "risks",
        "next_steps",
        "links",
    }
    for key in sorted(required_root - root.keys()):
        errors.append(f"$.{key}: обязательное поле отсутствует")

    task = require_mapping(root.get("task"), "$.task", errors)
    for field in ("id", "title", "generated_at"):
        require_string(task, field, "$.task", errors)
    require_enum(task, "status", {"pr_created"}, "$.task", errors)
    require_enum(task, "approval_mode", {"manual", "auto"}, "$.task", errors)
    source_url = require_string(task, "source_url", "$.task", errors)
    if source_url:
        validate_url(source_url, "$.task.source_url", errors, allow_missing=True)

    summary = require_mapping(root.get("summary"), "$.summary", errors)
    for field in ("business_problem", "solution", "outcome"):
        require_string(summary, field, "$.summary", errors)

    attention = validate_object_list(
        root.get("attention"), ("severity", "title", "detail"), "$.attention", errors
    )
    for index, item in enumerate(attention):
        require_enum(item, "severity", {"info", "warning", "critical"}, f"$.attention[{index}]", errors)

    business = require_mapping(root.get("business"), "$.business", errors)
    for field in ("origin", "impact", "expected_effect", "success_signal", "measured_effect"):
        require_string(business, field, "$.business", errors)
    validate_string_list(business.get("users"), "$.business.users", errors)
    validate_string_list(business.get("confirmed_facts"), "$.business.confirmed_facts", errors)
    validate_string_list(business.get("assumptions"), "$.business.assumptions", errors)

    solution = require_mapping(root.get("solution"), "$.solution", errors)
    for field in ("approach", "rationale"):
        require_string(solution, field, "$.solution", errors)
    validate_string_list(solution.get("before"), "$.solution.before", errors)
    validate_string_list(solution.get("after"), "$.solution.after", errors)
    validate_object_list(
        solution.get("alternatives"),
        ("name", "reason_not_chosen"),
        "$.solution.alternatives",
        errors,
    )

    oversight = require_mapping(root.get("oversight"), "$.oversight", errors)
    approval_gates = validate_object_list(
        oversight.get("approval_gates"),
        ("stage", "status", "evidence"),
        "$.oversight.approval_gates",
        errors,
    )
    for index, item in enumerate(approval_gates):
        require_enum(
            item,
            "status",
            {"auto_approved", "user_approved"},
            f"$.oversight.approval_gates[{index}]",
            errors,
        )
    validate_object_list(
        oversight.get("autonomous_decisions"),
        ("decision", "rationale", "source"),
        "$.oversight.autonomous_decisions",
        errors,
    )
    validate_object_list(
        oversight.get("plan_deviations"),
        ("deviation", "reason", "impact"),
        "$.oversight.plan_deviations",
        errors,
    )
    validate_string_list(oversight.get("unverified"), "$.oversight.unverified", errors)

    technical = require_mapping(root.get("technical"), "$.technical", errors)
    repositories = require_list(technical.get("repositories"), "$.technical.repositories", errors)
    if not repositories:
        errors.append("$.technical.repositories: нужен хотя бы один репозиторий")
    for index, item in enumerate(repositories):
        path = f"$.technical.repositories[{index}]"
        repository = require_mapping(item, path, errors)
        for field in ("name", "path", "base_branch", "target_branch", "commit"):
            require_string(repository, field, path, errors)
        validate_string_list(repository.get("components"), f"{path}.components", errors)
        validate_string_list(repository.get("changes"), f"{path}.changes", errors)
        pull_request = require_mapping(repository.get("pull_request"), f"{path}.pull_request", errors)
        number = require_integer(pull_request, "number", f"{path}.pull_request", errors)
        if number <= 0:
            errors.append(f"{path}.pull_request.number: номер PR должен быть положительным")
        url = require_string(pull_request, "url", f"{path}.pull_request", errors)
        if url:
            validate_url(url, f"{path}.pull_request.url", errors)
        require_enum(
            pull_request,
            "status",
            {"draft", "open", "merged", "closed"},
            f"{path}.pull_request",
            errors,
        )

    validation = require_mapping(root.get("validation"), "$.validation", errors)
    acceptance = validate_object_list(
        validation.get("acceptance_criteria"),
        ("criterion", "status", "evidence"),
        "$.validation.acceptance_criteria",
        errors,
    )
    for index, item in enumerate(acceptance):
        require_enum(
            item,
            "status",
            {"passed", "failed", "partial", "not_checked"},
            f"$.validation.acceptance_criteria[{index}]",
            errors,
        )

    for collection in ("checks", "manual_checks"):
        checks = validate_object_list(
            validation.get(collection),
            ("name", "status", "details"),
            f"$.validation.{collection}",
            errors,
        )
        for index, item in enumerate(checks):
            require_enum(
                item,
                "status",
                {"passed", "failed", "skipped"},
                f"$.validation.{collection}[{index}]",
                errors,
            )

    findings = validate_object_list(
        validation.get("review_findings"),
        ("severity", "finding", "decision", "resolution"),
        "$.validation.review_findings",
        errors,
    )
    for index, item in enumerate(findings):
        require_enum(
            item,
            "severity",
            {"required", "recommended", "irrelevant"},
            f"$.validation.review_findings[{index}]",
            errors,
        )

    risks = validate_object_list(
        root.get("risks"), ("level", "title", "mitigation"), "$.risks", errors
    )
    for index, item in enumerate(risks):
        require_enum(
            item,
            "level",
            {"low", "medium", "high", "critical"},
            f"$.risks[{index}]",
            errors,
        )

    validate_string_list(root.get("next_steps"), "$.next_steps", errors)
    links = validate_object_list(root.get("links"), ("label", "url", "kind"), "$.links", errors)
    for index, item in enumerate(links):
        require_enum(
            item,
            "kind",
            {"task", "proposal", "spec", "commit", "pr", "other"},
            f"$.links[{index}]",
            errors,
        )
        url = item.get("url", "")
        if isinstance(url, str) and url:
            validate_url(url, f"$.links[{index}].url", errors)

    find_forbidden_keys(root, "$", errors)
    return errors


class ReportHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.has_viewport = False
        self.lang = ""
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "html":
            self.lang = values.get("lang", "")
        if tag == "meta" and values.get("name", "").lower() == "viewport":
            self.has_viewport = True
        if tag in {"script", "link", "img", "iframe", "object", "embed", "audio", "video", "source"}:
            self.errors.append(f"HTML: ресурсный или исполняемый тег <{tag}> запрещён")
        if tag == "a" and values.get("href"):
            validate_url(values["href"], "HTML: href", self.errors)


def validate_html(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    inspector = ReportHTMLInspector()
    inspector.feed(text)
    errors.extend(inspector.errors)

    if inspector.lang != "ru":
        errors.append("HTML: ожидается <html lang=\"ru\">")
    if not inspector.has_viewport:
        errors.append("HTML: отсутствует viewport meta")
    for section_id in sorted(REQUIRED_HTML_IDS - inspector.ids):
        errors.append(f"HTML: отсутствует обязательный id='{section_id}'")
    if re.search(r"\{\{[^{}]+\}\}", text):
        errors.append("HTML: остались незаполненные placeholders")
    if re.search(r"@media\s+print", text, flags=re.IGNORECASE):
        errors.append("HTML: print-стили не входят в текущий scope")
    if re.search(r"@import|url\(", text, flags=re.IGNORECASE):
        errors.append("HTML: обнаружена внешняя CSS-зависимость")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="Путь к report-data.json")
    parser.add_argument("--html", type=Path, help="Путь к созданному report.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    try:
        data = json.loads(args.data.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"Файл данных не найден: {args.data}")
        data = None
    except json.JSONDecodeError as error:
        errors.append(f"Некорректный JSON: {error}")
        data = None

    if data is not None:
        errors.extend(validate_data(data))

    if args.html:
        if args.html.is_file():
            errors.extend(validate_html(args.html))
        else:
            errors.append(f"HTML-файл не найден: {args.html}")

    if errors:
        for error in errors:
            print(f"ОШИБКА: {error}", file=sys.stderr)
        return 1

    checked = str(args.data)
    if args.html:
        checked += f" и {args.html}"
    print(f"Проверка отчёта пройдена: {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
