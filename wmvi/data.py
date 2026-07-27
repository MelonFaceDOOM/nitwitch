"""Load and shape WMVI dashboard_summary.json for the /wmvi page.

Uploader contract
-----------------
The separate upload app must write a fixed filename (no dates/versions):

    <uploads_dir>/dashboard_summary.json

Prefer an atomic overwrite so Django never reads a partial file::

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

Keep ``generated_at_utc`` inside the JSON for human freshness. The web app
detects replacements via file mtime/size — filename versioning is not needed.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from django.conf import settings
from django.core.cache import cache

CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX = "wmvi:dashboard"


class DashboardLoadError(Exception):
    """Raised when the dashboard JSON cannot be read or parsed."""


def dashboard_json_path() -> str:
    return getattr(
        settings,
        "WMVI_DASHBOARD_JSON_PATH",
        "/mnt/md0/nitwitch_dl/uploads/dashboard_summary.json",
    )


def load_dashboard_data() -> dict[str, Any]:
    """Return parsed dashboard JSON, cached by path + mtime + size."""
    path = dashboard_json_path()
    try:
        st = os.stat(path)
    except OSError as exc:
        raise DashboardLoadError(f"Cannot stat dashboard file {path!r}: {exc}") from exc

    cache_key = f"{CACHE_KEY_PREFIX}:{path}:{st.st_mtime_ns}:{st.st_size}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise DashboardLoadError(f"Cannot read dashboard file {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardLoadError(f"Invalid JSON in {path!r}: {exc}") from exc

    if not isinstance(data, dict):
        raise DashboardLoadError(f"Dashboard JSON root must be an object, got {type(data).__name__}")

    cache.set(cache_key, data, CACHE_TTL_SECONDS)
    return data


def _sorted_days(days: set[str]) -> list[str]:
    return sorted(days)


def pivot_ingestion_chart(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build Chart.js payload: day labels, one dataset per platform."""
    if not rows:
        return {"labels": [], "datasets": []}

    by_day_platform: dict[str, dict[str, float]] = defaultdict(dict)
    platforms: set[str] = set()
    for row in rows:
        day = str(row.get("day", ""))
        platform = str(row.get("platform", ""))
        n = row.get("n") or 0
        by_day_platform[day][platform] = n
        platforms.add(platform)

    labels = _sorted_days(set(by_day_platform))
    platform_list = sorted(platforms)
    datasets = []
    for platform in platform_list:
        datasets.append(
            {
                "label": platform,
                "data": [by_day_platform[d].get(platform, 0) for d in labels],
                "fill": False,
                "tension": 0.15,
            }
        )
    return {"labels": labels, "datasets": datasets}


def is_en_daily_totals_chart(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum is_en_true/false/null across platforms per day for Chart.js."""
    if not rows:
        return {"labels": [], "datasets": []}

    by_day: dict[str, dict[str, float]] = defaultdict(
        lambda: {"is_en_true": 0, "is_en_false": 0, "is_en_null": 0}
    )
    for row in rows:
        day = str(row.get("day", ""))
        by_day[day]["is_en_true"] += row.get("is_en_true") or 0
        by_day[day]["is_en_false"] += row.get("is_en_false") or 0
        by_day[day]["is_en_null"] += row.get("is_en_null") or 0

    labels = _sorted_days(set(by_day))
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "is_en_true",
                "data": [by_day[d]["is_en_true"] for d in labels],
                "fill": False,
                "tension": 0.15,
            },
            {
                "label": "is_en_false",
                "data": [by_day[d]["is_en_false"] for d in labels],
                "fill": False,
                "tension": 0.15,
            },
            {
                "label": "is_en_null",
                "data": [by_day[d]["is_en_null"] for d in labels],
                "fill": False,
                "tension": 0.15,
            },
        ],
    }


def single_series_chart(
    rows: list[dict[str, Any]],
    *,
    value_key: str,
    label: str,
) -> dict[str, Any]:
    """Line chart from rows with ``day`` + one numeric column."""
    if not rows:
        return {"labels": [], "datasets": []}

    sorted_rows = sorted(rows, key=lambda r: str(r.get("day", "")))
    labels = [str(r.get("day", "")) for r in sorted_rows]
    values = [r.get(value_key) or 0 for r in sorted_rows]
    return {
        "labels": labels,
        "datasets": [
            {
                "label": label,
                "data": values,
                "fill": False,
                "tension": 0.15,
            }
        ],
    }


def first_summary_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return rows[0]


def format_metric(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def build_table(
    rows: list[dict[str, Any]],
    sort_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Return ``{columns, rows}`` where each row is a list of display values."""
    if not rows:
        return {"columns": [], "rows": []}

    columns: list[str] = []
    for row in rows:
        for k in row:
            if k not in columns:
                columns.append(k)

    ordered = rows
    if sort_keys:
        ordered = sorted(
            rows,
            key=lambda r: tuple(str(r.get(k, "")) for k in sort_keys),
        )

    display_rows = []
    for row in ordered:
        display_rows.append([_cell_str(row.get(col)) for col in columns])

    return {"columns": columns, "rows": display_rows}


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
