import asyncio
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .client import JsonObject, TrackerClient
from .duration import duration_to_minutes, format_minutes


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD format") from exc


def _worklog_start_date(worklog: JsonObject) -> date | None:
    raw = worklog.get("start")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _within_period(worklog: JsonObject, date_from: date | None, date_to: date | None) -> bool:
    if date_from is None and date_to is None:
        return True
    started = _worklog_start_date(worklog)
    if started is None:
        return False
    return (date_from is None or started >= date_from) and (date_to is None or started <= date_to)


def _reference_label(
    value: Any,
    fallback: str,
    fields: tuple[str, ...] = ("login", "display", "key", "id"),
) -> str:
    if not isinstance(value, dict):
        return fallback
    for field in fields:
        candidate = value.get(field)
        if candidate not in (None, ""):
            return str(candidate)
    return fallback


def _duration_with_warning(
    value: Any,
    *,
    context: str,
    warnings: list[str],
) -> int | None:
    if not isinstance(value, str):
        warnings.append(f"{context}: duration is missing")
        return None
    try:
        return duration_to_minutes(value)
    except ValueError as exc:
        warnings.append(f"{context}: {exc}")
        return None


def _estimate_minutes(issue: JsonObject, field: str, warnings: list[str]) -> int | None:
    value = issue.get(field)
    if value in (None, ""):
        return None
    return _duration_with_warning(
        value,
        context=f"{issue.get('key', 'unknown issue')} {field}",
        warnings=warnings,
    )


def _sorted_groups(values: dict[str, int]) -> list[JsonObject]:
    return [
        {"name": name, "minutes": minutes, "display": format_minutes(minutes)}
        for name, minutes in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _summarize_worklogs(
    records: list[tuple[JsonObject, JsonObject]],
    warnings: list[str],
) -> JsonObject:
    by_user: defaultdict[str, int] = defaultdict(int)
    by_issue: defaultdict[str, int] = defaultdict(int)
    by_queue: defaultdict[str, int] = defaultdict(int)
    by_day: defaultdict[str, int] = defaultdict(int)
    total_minutes = 0
    counted_entries = 0

    for issue, worklog in records:
        context = f"worklog {worklog.get('id', 'unknown')}"
        minutes = _duration_with_warning(
            worklog.get("duration"),
            context=context,
            warnings=warnings,
        )
        if minutes is None:
            continue

        issue_key = str(issue.get("key") or issue.get("id") or "unknown")
        queue = _reference_label(issue.get("queue"), "unknown", ("key", "display", "id"))
        user = _reference_label(worklog.get("createdBy"), "unknown")
        started = _worklog_start_date(worklog)

        total_minutes += minutes
        counted_entries += 1
        by_user[user] += minutes
        by_issue[issue_key] += minutes
        by_queue[queue] += minutes
        if started is not None:
            by_day[started.isoformat()] += minutes

    return {
        "total_minutes": total_minutes,
        "total": format_minutes(total_minutes),
        "entry_count": counted_entries,
        "by_user": _sorted_groups(dict(by_user)),
        "by_issue": _sorted_groups(dict(by_issue)),
        "by_queue": _sorted_groups(dict(by_queue)),
        "by_day": _sorted_groups(dict(by_day)),
    }


async def build_issue_time_report(
    client: TrackerClient,
    issue_id: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> JsonObject:
    period_from = _parse_date(date_from, "date_from")
    period_to = _parse_date(date_to, "date_to")
    if period_from is not None and period_to is not None and period_from > period_to:
        raise ValueError("date_from must not be later than date_to")

    issue, all_worklogs = await asyncio.gather(
        client.get_issue(issue_id),
        client.get_issue_worklogs(issue_id),
    )
    worklogs = [
        worklog for worklog in all_worklogs if _within_period(worklog, period_from, period_to)
    ]
    warnings: list[str] = []
    summary = _summarize_worklogs([(issue, worklog) for worklog in worklogs], warnings)

    original = _estimate_minutes(issue, "originalEstimation", warnings)
    current = _estimate_minutes(issue, "estimation", warnings)
    tracker_spent = _estimate_minutes(issue, "spent", warnings)
    actual = int(summary["total_minutes"])
    variance = actual - current if current is not None else None
    utilization = round(actual / current * 100, 2) if current else None

    return {
        "issue": {
            "key": issue.get("key", issue_id),
            "summary": issue.get("summary"),
            "queue": _reference_label(
                issue.get("queue"),
                "unknown",
                ("key", "display", "id"),
            ),
        },
        "period": {"from": date_from, "to": date_to},
        "estimate": {
            "original_minutes": original,
            "original": format_minutes(original),
            "current_minutes": current,
            "current": format_minutes(current),
        },
        "actual": summary,
        "tracker_spent_minutes": tracker_spent,
        "tracker_spent": format_minutes(tracker_spent),
        "variance_minutes": variance,
        "variance": format_minutes(variance),
        "utilization_percent": utilization,
        "truncated": len(all_worklogs) == 500,
        "warnings": warnings,
    }


async def build_time_report(
    client: TrackerClient,
    query: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    max_issues: int = 50,
    concurrency: int = 5,
) -> JsonObject:
    period_from = _parse_date(date_from, "date_from")
    period_to = _parse_date(date_to, "date_to")
    if period_from is not None and period_to is not None and period_from > period_to:
        raise ValueError("date_from must not be later than date_to")
    if not 1 <= max_issues <= 200:
        raise ValueError("max_issues must be between 1 and 200")
    if not 1 <= concurrency <= 10:
        raise ValueError("concurrency must be between 1 and 10")

    issues: list[JsonObject] = []
    issue_probe_limit = max_issues + 1
    page = 1
    while len(issues) < issue_probe_limit:
        per_page = min(50, issue_probe_limit - len(issues))
        batch = await client.search_issues(
            query,
            page=page,
            per_page=per_page,
            fields=[
                "key",
                "summary",
                "queue",
                "originalEstimation",
                "estimation",
                "spent",
            ],
        )
        issues.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    issues_truncated = len(issues) > max_issues
    issues = issues[:max_issues]

    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_worklogs(issue: JsonObject) -> tuple[JsonObject, list[JsonObject]]:
        issue_id = str(issue.get("key") or issue.get("id") or "")
        if not issue_id:
            return issue, []
        async with semaphore:
            return issue, await client.get_issue_worklogs(issue_id)

    fetched = await asyncio.gather(*(fetch_worklogs(issue) for issue in issues))
    records: list[tuple[JsonObject, JsonObject]] = []
    truncated_issues: list[str] = []
    for issue, worklogs in fetched:
        if len(worklogs) == 500:
            truncated_issues.append(str(issue.get("key") or issue.get("id") or "unknown"))
        records.extend(
            (issue, worklog)
            for worklog in worklogs
            if _within_period(worklog, period_from, period_to)
        )

    warnings: list[str] = []
    summary = _summarize_worklogs(records, warnings)
    estimated_minutes = sum(
        estimate
        for issue in issues
        if (estimate := _estimate_minutes(issue, "estimation", warnings)) is not None
    )
    actual_minutes = int(summary["total_minutes"])
    variance = actual_minutes - estimated_minutes if estimated_minutes else None

    return {
        "query": query,
        "period": {"from": date_from, "to": date_to},
        "issue_count": len(issues),
        "summary": summary,
        "current_estimate_minutes": estimated_minutes or None,
        "current_estimate": format_minutes(estimated_minutes) if estimated_minutes else None,
        "variance_minutes": variance,
        "variance": format_minutes(variance),
        "utilization_percent": (
            round(actual_minutes / estimated_minutes * 100, 2) if estimated_minutes else None
        ),
        "truncated": issues_truncated or bool(truncated_issues),
        "truncated_issues": truncated_issues,
        "warnings": warnings,
    }
