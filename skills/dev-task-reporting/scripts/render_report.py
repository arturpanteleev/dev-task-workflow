#!/usr/bin/env python3
"""Render a standalone responsive HTML task report from report-data.json."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from validate_report import ALLOWED_SCHEMES, validate_data


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SCRIPT_DIR.parent / "assets" / "report-template.html"

STATUS_LABELS = {
    "pr_created": "PR создан",
    "in_progress": "В процессе",
    "blocked": "Заблокирован",
    "manual": "Ручной режим",
    "auto": "Авторежим",
    "draft": "Draft",
    "open": "Open",
    "merged": "Merged",
    "closed": "Closed",
    "passed": "Пройдено",
    "failed": "Ошибка",
    "partial": "Частично",
    "not_checked": "Не проверено",
    "skipped": "Пропущено",
    "required": "Обязательное",
    "recommended": "Рекомендация",
    "irrelevant": "Нерелевантно",
    "info": "Информация",
    "warning": "Внимание",
    "critical": "Критично",
    "auto_approved": "Auto-approved",
    "user_approved": "Подтверждено пользователем",
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}

STATUS_CLASSES = {
    "pr_created": "success",
    "in_progress": "accent",
    "blocked": "danger",
    "manual": "neutral",
    "auto": "accent",
    "draft": "neutral",
    "open": "accent",
    "merged": "success",
    "closed": "danger",
    "passed": "success",
    "failed": "danger",
    "partial": "warning",
    "not_checked": "neutral",
    "skipped": "neutral",
    "required": "danger",
    "recommended": "warning",
    "irrelevant": "neutral",
    "info": "accent",
    "warning": "warning",
    "critical": "danger",
    "auto_approved": "accent",
    "user_approved": "success",
    "low": "success",
    "medium": "warning",
    "high": "danger",
    "started": "neutral",
    "completed": "success",
    "error": "danger",
    "retried": "warning",
}

STAGE_LABELS: dict[str, str] = {
    "init": "Инициализация",
    "product-analysis": "Продуктовый анализ",
    "approval-proposal": "Утверждение proposal",
    "technical-planning": "Техническое планирование",
    "approval-spec": "Утверждение spec",
    "implementation": "Реализация",
    "verification": "Верификация",
    "code-review": "Code Review",
    "delivery": "Доставка",
    "reporting": "Итоговый отчёт",
}

EVENT_LABELS: dict[str, str] = {
    "started": "Начат",
    "completed": "Завершён",
    "blocked": "Заблокирован",
    "error": "Ошибка",
    "retried": "Повторно",
    "skipped": "Пропущен",
}

STAGE_ORDER = [
    "init",
    "product-analysis",
    "approval-proposal",
    "technical-planning",
    "approval-spec",
    "implementation",
    "verification",
    "code-review",
    "delivery",
    "reporting",
]


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def prose(value: Any) -> str:
    return escape(value).replace("\n", "<br>")


def safe_url(value: str) -> str:
    scheme = urlsplit(value).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Запрещённая URL-схема: {scheme}")
    return escape(value)


def badge(status: str) -> str:
    label = STATUS_LABELS.get(status, status)
    css_class = STATUS_CLASSES.get(status, "neutral")
    return f'<span class="badge badge--{css_class}">{escape(label)}</span>'


def link_button(url: str, label: str, subtle: bool = False) -> str:
    css_class = "button button--subtle" if subtle else "button"
    return f'<a class="{css_class}" href="{safe_url(url)}">{escape(label)} <span aria-hidden="true">↗</span></a>'


def render_string_list(items: list[str], empty_text: str = "Не зафиксировано") -> str:
    if not items:
        return f'<p class="empty-state">{escape(empty_text)}</p>'
    return '<ul class="clean-list">' + "".join(f"<li>{prose(item)}</li>" for item in items) + "</ul>"


def render_hero(data: dict[str, Any]) -> str:
    task = data["task"]
    repositories = data["technical"]["repositories"]
    pr_buttons = "".join(
        link_button(repo["pull_request"]["url"], f'{repo["name"]} · PR #{repo["pull_request"]["number"]}')
        for repo in repositories
        if repo.get("pull_request") and repo["pull_request"].get("url")
    )
    return f"""
    <header class="hero" id="top">
      <div class="hero__eyebrow">Итоговый отчёт задачи · {escape(task['id'])}</div>
      <div class="hero__layout">
        <div>
          <h1>{escape(task['title'])}</h1>
          <p class="hero__lead">{prose(data['summary']['outcome'])}</p>
        </div>
        <div class="hero__status" aria-label="Статус отчёта">
          {badge(task['status'])}
          {badge(task['approval_mode'])}
        </div>
      </div>
      <div class="hero__actions">{pr_buttons}</div>
      <p class="hero__meta">Сформировано {escape(task['generated_at'])}. Отчёт фиксирует состояние на момент создания PR и не подтверждает выпуск в production.</p>
    </header>
    """


def render_summary(data: dict[str, Any]) -> str:
    validation = data["validation"]
    acceptance = validation["acceptance_criteria"]
    checks = validation["checks"] + validation["manual_checks"]
    passed_acceptance = sum(item["status"] == "passed" for item in acceptance)
    passed_checks = sum(item["status"] == "passed" for item in checks)
    metrics = (
        ("Репозитории", len(data["technical"]["repositories"]), "с изменениями"),
        ("Acceptance Criteria", f"{passed_acceptance}/{len(acceptance)}", "подтверждено"),
        ("Проверки", f"{passed_checks}/{len(checks)}", "успешно"),
        ("Точки внимания", len(data["attention"]), "требуют просмотра"),
    )
    metric_cards = "".join(
        f'<article class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong><small>{escape(note)}</small></article>'
        for label, value, note in metrics
    )
    summary_cards = "".join(
        f'<article class="summary-card"><span class="kicker">{escape(label)}</span><p>{prose(value)}</p></article>'
        for label, value in (
            ("Проблема", data["summary"]["business_problem"]),
            ("Решение", data["summary"]["solution"]),
            ("Результат работы", data["summary"]["outcome"]),
        )
    )
    oversight = data["oversight"]

    def preview(items: list[str], empty_text: str) -> str:
        if not items:
            return f'<p class="empty-state">{escape(empty_text)}</p>'
        visible = items[:3]
        remainder = len(items) - len(visible)
        suffix = f'<small>Ещё: {remainder}</small>' if remainder else ""
        return render_string_list(visible) + suffix

    control_cards = "".join(
        f'<article class="control-card"><span class="kicker">{escape(label)}</span>{preview(items, empty_text)}</article>'
        for label, items, empty_text in (
            ("Требует внимания", [item["title"] for item in data["attention"]], "Нет отдельных точек внимания."),
            ("Автономные решения", [item["decision"] for item in oversight["autonomous_decisions"]], "Не зафиксированы."),
            ("Отклонения", [item["deviation"] for item in oversight["plan_deviations"]], "Отклонений от плана нет."),
            ("Непроверено", oversight["unverified"], "Непроверенных сценариев нет."),
        )
    )
    return f"""
    <section id="executive-summary" class="section section--first">
      <div class="section-heading"><span>01</span><div><p>Быстрый обзор</p><h2>Главное за несколько минут</h2></div></div>
      <div class="summary-grid">{summary_cards}</div>
      <div class="metrics-grid" aria-label="Сводные показатели">{metric_cards}</div>
      <div class="control-grid" aria-label="Контрольные точки">{control_cards}</div>
    </section>
    """


def render_attention(data: dict[str, Any]) -> str:
    items = data["attention"]
    if items:
        content = "".join(
            f'<article class="attention-card attention-card--{STATUS_CLASSES[item["severity"]]}">'
            f'<div>{badge(item["severity"])}<h3>{escape(item["title"])}</h3></div><p>{prose(item["detail"])}</p></article>'
            for item in items
        )
    else:
        content = '<div class="positive-state"><span aria-hidden="true">✓</span><p>Отдельных точек внимания не зафиксировано.</p></div>'
    return f"""
    <section id="attention" class="section">
      <div class="section-heading"><span>02</span><div><p>Контроль</p><h2>Требует вашего внимания</h2></div></div>
      <div class="attention-grid">{content}</div>
    </section>
    """


def render_business(data: dict[str, Any]) -> str:
    business = data["business"]
    source = data["task"]["source_url"]
    source_link = ""
    if source != "Не зафиксировано":
        source_link = link_button(source, "Открыть исходную задачу", subtle=True)
    return f"""
    <section id="business-context" class="section">
      <div class="section-heading"><span>03</span><div><p>Контекст</p><h2>Почему появилась задача</h2></div></div>
      <div class="two-column">
        <article class="panel panel--featured"><span class="kicker">Происхождение проблемы</span><p>{prose(business['origin'])}</p>{source_link}</article>
        <article class="panel"><span class="kicker">Наблюдаемое влияние</span><p>{prose(business['impact'])}</p></article>
      </div>
      <div class="detail-grid">
        <article class="detail"><h3>Кого затрагивает</h3>{render_string_list(business['users'])}</article>
        <article class="detail"><h3>Подтверждённые факты</h3>{render_string_list(business['confirmed_facts'])}</article>
        <article class="detail"><h3>Допущения</h3>{render_string_list(business['assumptions'], 'Допущения не зафиксированы.')}</article>
        <article class="detail"><h3>Ожидаемый эффект</h3><p>{prose(business['expected_effect'])}</p></article>
        <article class="detail"><h3>Сигнал успеха</h3><p>{prose(business['success_signal'])}</p></article>
        <article class="detail"><h3>Измеренный эффект</h3><p>{prose(business['measured_effect'])}</p></article>
      </div>
    </section>
    """


def render_flow(title: str, items: list[str], modifier: str) -> str:
    return f"""
    <article class="flow-card flow-card--{modifier}">
      <span class="kicker">{escape(title)}</span>
      {render_string_list(items)}
    </article>
    """


def render_solution(data: dict[str, Any]) -> str:
    solution = data["solution"]
    alternatives = "".join(
        f'<article class="compact-card"><h3>{escape(item["name"])}</h3><p>{prose(item["reason_not_chosen"])}</p></article>'
        for item in solution["alternatives"]
    ) or '<p class="empty-state">Альтернативы не зафиксированы.</p>'
    arrow = """
      <div class="flow-arrow" aria-label="Переход к новому состоянию">
        <svg viewBox="0 0 48 48" role="img" aria-hidden="true"><path d="M8 24h28M27 14l10 10-10 10"/></svg>
      </div>
    """
    return f"""
    <section id="solution" class="section">
      <div class="section-heading"><span>04</span><div><p>Решение</p><h2>Что и почему изменили</h2></div></div>
      <div class="two-column">
        <article class="panel panel--featured"><span class="kicker">Выбранный подход</span><p>{prose(solution['approach'])}</p></article>
        <article class="panel"><span class="kicker">Обоснование</span><p>{prose(solution['rationale'])}</p></article>
      </div>
      <div class="before-after">
        {render_flow('До изменения', solution['before'], 'before')}
        {arrow}
        {render_flow('После изменения', solution['after'], 'after')}
      </div>
      <details class="details-block"><summary>Рассмотренные альтернативы</summary><div class="compact-grid">{alternatives}</div></details>
    </section>
    """


def format_duration(ms: int | None) -> str:
    if ms is None:
        return ""
    if ms < 1000:
        return f"{ms} мс"
    if ms < 60000:
        return f"{ms / 1000:.1f} с"
    if ms < 3600000:
        m = int(ms / 60000)
        s = int((ms % 60000) / 1000)
        return f"{m} мин {s} с" if s else f"{m} мин"
    return "—"


def render_trace(data: dict[str, Any]) -> str:
    trace = data.get("workflow_trace", [])
    if not trace:
        return ""

    stages: dict[str, dict[str, Any]] = {}
    for entry in trace:
        stage = entry.get("stage", "")
        if stage not in stages:
            stages[stage] = {"started": None, "result": None}
        if entry.get("event") == "started":
            stages[stage]["started"] = entry
        elif entry.get("event") in {"completed", "blocked", "error", "skipped"}:
            stages[stage]["result"] = entry

    items: list[str] = []
    for stage_id in STAGE_ORDER:
        if stage_id not in stages:
            continue
        info = stages[stage_id]
        result = info.get("result")
        if result is None:
            continue

        event = result.get("event", "")
        event_class = STATUS_CLASSES.get(event, "neutral")
        stage_label = STAGE_LABELS.get(stage_id, stage_id)
        event_label = EVENT_LABELS.get(event, event)
        timestamp = result.get("timestamp", "")
        duration = format_duration(result.get("duration_ms"))
        summary = result.get("summary", "")
        approval = result.get("approval", "")

        approval_badge = badge(approval) if approval else ""
        summary_html = f'<p class="timeline-item__summary">{prose(summary)}</p>' if summary else ""

        items.append(f"""
        <div class="timeline-item timeline-item--{event_class}">
          <div class="timeline-item__marker"><span></span></div>
          <div class="timeline-item__content">
            <div class="timeline-item__header">
              <h3>{escape(stage_label)}</h3>
              <div class="timeline-item__meta">
                {badge(event_label)}
                {approval_badge}
                <span class="timeline-item__duration">{escape(duration)}</span>
                <time datetime="{escape(timestamp)}">{escape(timestamp)}</time>
              </div>
            </div>
            {summary_html}
          </div>
        </div>
        """)

    if not items:
        return ""

    return f"""
    <section id="trace" class="section trace-section">
      <h2 class="trace-heading">Ход выполнения</h2>
      <div class="timeline">{"".join(items)}</div>
    </section>
    """


def render_decisions(data: dict[str, Any]) -> str:
    oversight = data["oversight"]
    approval_gates = "".join(
        f'<article class="gate-card"><div>{badge(item["status"])}<h3>{escape(item["stage"])}</h3></div><p>{prose(item["evidence"])}</p></article>'
        for item in oversight["approval_gates"]
    ) or '<p class="empty-state">Внутренние approval gates не зафиксированы.</p>'
    decisions = "".join(
        f'<article class="decision"><h3>{escape(item["decision"])}</h3><p>{prose(item["rationale"])}</p><small>Основание: {prose(item["source"])}</small></article>'
        for item in oversight["autonomous_decisions"]
    ) or '<p class="empty-state">Самостоятельные решения не зафиксированы.</p>'
    deviations = "".join(
        f'<article class="decision decision--warning"><h3>{escape(item["deviation"])}</h3><p>{prose(item["reason"])}</p><small>Влияние: {prose(item["impact"])}</small></article>'
        for item in oversight["plan_deviations"]
    ) or '<p class="empty-state">Отклонений от согласованного плана нет.</p>'
    return f"""
    <section id="decisions" class="section">
      <div class="section-heading"><span>05</span><div><p>Прозрачность</p><h2>Решения агента и отклонения</h2></div></div>
      <h3 class="subheading">Внутренние approval gates</h3><div class="gate-grid">{approval_gates}</div>
      <div class="two-column">
        <div><h3 class="subheading">Самостоятельные решения</h3><div class="stack">{decisions}</div></div>
        <div><h3 class="subheading">Отклонения от плана</h3><div class="stack">{deviations}</div></div>
      </div>
      <article class="unverified"><h3>Непроверенные сценарии</h3>{render_string_list(oversight['unverified'], 'Непроверенных сценариев не зафиксировано.')}</article>
    </section>
    """


def render_technical(data: dict[str, Any]) -> str:
    cards = []
    for repository in data["technical"]["repositories"]:
        pull_request = repository.get("pull_request")
        pr_status = badge(pull_request["status"]) if pull_request else ""
        pr_url = ""
        if pull_request and pull_request.get("url") and pull_request.get("number"):
            pr_url = f'<a href="{safe_url(pull_request["url"])}">#{pull_request["number"]} <span aria-hidden="true">↗</span></a>'
        elif not pull_request:
            pr_url = '<span class="empty-state">Не создан</span>'
        components = "".join(f'<span class="tag">{escape(item)}</span>' for item in repository["components"])
        cards.append(f"""
        <article class="repo-card">
          <div class="repo-card__header"><div><span class="kicker">Репозиторий</span><h3>{escape(repository['name'])}</h3></div>{pr_status}</div>
          <dl class="metadata">
            <div><dt>Ветки</dt><dd>{escape(repository['base_branch'])} → {escape(repository['target_branch'])}</dd></div>
            <div><dt>Commit</dt><dd><code>{escape(repository['commit'])}</code></dd></div>
            <div><dt>PR</dt><dd>{pr_url}</dd></div>
            <div><dt>Путь</dt><dd><code>{escape(repository['path'])}</code></dd></div>
          </dl>
          <div class="tags">{components or '<span class="tag">Компоненты не зафиксированы</span>'}</div>
          <div class="repo-card__changes"><h4>Что изменилось</h4>{render_string_list(repository['changes'])}</div>
        </article>
        """)
    return f"""
    <section id="technical" class="section">
      <div class="section-heading"><span>06</span><div><p>Реализация</p><h2>Технические изменения</h2></div></div>
      <div class="repo-grid">{''.join(cards)}</div>
    </section>
    """


def render_status_table(items: list[dict[str, str]], name_key: str, detail_key: str) -> str:
    if not items:
        return '<p class="empty-state">Данные не зафиксированы.</p>'
    rows = "".join(
        f'<tr><td>{prose(item[name_key])}</td><td>{badge(item["status"])}</td><td>{prose(item[detail_key])}</td></tr>'
        for item in items
    )
    return f'<div class="table-wrap"><table><thead><tr><th>Проверка</th><th>Статус</th><th>Подтверждение</th></tr></thead><tbody>{rows}</tbody></table></div>'


def render_validation(data: dict[str, Any]) -> str:
    validation = data["validation"]
    acceptance = render_status_table(validation["acceptance_criteria"], "criterion", "evidence")
    automatic = render_status_table(validation["checks"], "name", "details")
    manual = render_status_table(validation["manual_checks"], "name", "details")
    findings = "".join(
        f'<article class="review-item"><div>{badge(item["severity"])}<h3>{escape(item["finding"])}</h3></div><p><strong>Решение:</strong> {prose(item["decision"])}</p><p><strong>Результат:</strong> {prose(item["resolution"])}</p></article>'
        for item in validation["review_findings"]
    ) or '<p class="empty-state">Замечаний review не зафиксировано.</p>'
    return f"""
    <section id="validation" class="section">
      <div class="section-heading"><span>07</span><div><p>Доказательства</p><h2>Как проверили результат</h2></div></div>
      <h3 class="subheading">Acceptance Criteria</h3>{acceptance}
      <div class="two-column validation-columns">
        <div><h3 class="subheading">Автоматические проверки</h3>{automatic}</div>
        <div><h3 class="subheading">Ручные проверки</h3>{manual}</div>
      </div>
      <details class="details-block" open><summary>Результаты code review</summary><div class="stack">{findings}</div></details>
    </section>
    """


def render_risks(data: dict[str, Any]) -> str:
    risks = "".join(
        f'<article class="risk-card risk-card--{STATUS_CLASSES[item["level"]]}"><div>{badge(item["level"])}<h3>{escape(item["title"])}</h3></div><p>{prose(item["mitigation"])}</p></article>'
        for item in data["risks"]
    ) or '<div class="positive-state"><span aria-hidden="true">✓</span><p>Остаточные риски не зафиксированы.</p></div>'
    return f"""
    <section id="risks" class="section">
      <div class="section-heading"><span>08</span><div><p>После PR</p><h2>Риски и следующие шаги</h2></div></div>
      <div class="risk-grid">{risks}</div>
      <article class="next-steps"><h3>Следующие шаги</h3>{render_string_list(data['next_steps'], 'Дополнительные шаги не зафиксированы.')}</article>
    </section>
    """


def render_links(data: dict[str, Any]) -> str:
    cards = "".join(
        f'<a class="link-card" href="{safe_url(item["url"])}"><span>{escape(item["kind"].upper())}</span><strong>{escape(item["label"])}</strong><small>{escape(item["url"])}</small></a>'
        for item in data["links"]
    ) or '<p class="empty-state">Дополнительные ссылки не зафиксированы.</p>'
    return f"""
    <section id="links" class="section">
      <div class="section-heading"><span>09</span><div><p>Материалы</p><h2>Артефакты и ссылки</h2></div></div>
      <div class="links-grid">{cards}</div>
    </section>
    """


def render_navigation() -> str:
    items = (
        ("Обзор", "executive-summary"),
        ("Внимание", "attention"),
        ("Проблема", "business-context"),
        ("Решение", "solution"),
        ("Реализация", "technical"),
        ("Проверки", "validation"),
        ("Риски", "risks"),
    )
    links = "".join(f'<a href="#{section_id}">{escape(label)}</a>' for label, section_id in items)
    return f'<nav class="page-nav" aria-label="Разделы отчёта">{links}</nav>'


def build_body(data: dict[str, Any]) -> str:
    return "".join(
        (
            '<a class="skip-link" href="#executive-summary">Перейти к содержанию</a>',
            '<div class="page-shell">',
            render_hero(data),
            render_trace(data),
            render_navigation(),
            '<main>',
            render_summary(data),
            render_attention(data),
            render_business(data),
            render_solution(data),
            render_decisions(data),
            render_technical(data),
            render_validation(data),
            render_risks(data),
            render_links(data),
            '</main>',
            f'<footer><a href="#top">Наверх ↑</a><p>{escape(data["task"]["id"])} · локальный отчёт dev-task-workflow</p></footer>',
            '</div>',
        )
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Путь к report-data.json")
    parser.add_argument("--output", type=Path, help="Путь к report.html")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Путь к HTML-шаблону")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ОШИБКА: не удалось прочитать данные: {error}", file=sys.stderr)
        return 1

    errors = validate_data(data)
    if errors:
        for error in errors:
            print(f"ОШИБКА: {error}", file=sys.stderr)
        return 1

    try:
        template = args.template.read_text(encoding="utf-8")
    except OSError as error:
        print(f"ОШИБКА: не удалось прочитать шаблон: {error}", file=sys.stderr)
        return 1

    placeholders = {"{{DOCUMENT_TITLE}}", "{{REPORT_BODY}}"}
    missing = [placeholder for placeholder in placeholders if placeholder not in template]
    if missing:
        print(f"ОШИБКА: в шаблоне отсутствуют placeholders: {', '.join(missing)}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_name("report.html")
    document = template.replace(
        "{{DOCUMENT_TITLE}}", escape(f"{data['task']['id']} — {data['task']['title']}")
    ).replace("{{REPORT_BODY}}", build_body(data))
    atomic_write(output, document)
    print(f"HTML-отчёт создан: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
