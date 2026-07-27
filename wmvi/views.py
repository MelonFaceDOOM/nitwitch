from __future__ import annotations

from django.shortcuts import render

from accounts.permissions import admin_required

from .data import (
    DashboardLoadError,
    build_table,
    dashboard_json_path,
    first_summary_row,
    format_metric,
    is_en_daily_totals_chart,
    load_dashboard_data,
    pivot_ingestion_chart,
    single_series_chart,
)


def _transcription_context(
    *,
    title: str,
    summary_rows: list,
    daily_rows: list,
    chart_id: str,
) -> dict:
    summary = first_summary_row(summary_rows)
    metrics = []
    if summary:
        metrics = [
            ("Total", format_metric(summary.get("total"))),
            ("Completed", format_metric(summary.get("completed"))),
            ("In progress", format_metric(summary.get("in_progress"))),
            ("Percent completion", format_metric(summary.get("percent_completion"))),
            ("Avg completed/day (30d)", format_metric(summary.get("avg_completed_per_day_30d"))),
            ("Estimated finish date", format_metric(summary.get("estimated_finish_date"))),
        ]
    return {
        "title": title,
        "metrics": metrics,
        "summary_table": build_table(summary_rows),
        "daily_table": build_table(daily_rows, ["day"]),
        "chart_id": chart_id,
        "chart_data": single_series_chart(
            daily_rows, value_key="transcriptions", label="transcriptions"
        ),
    }


@admin_required
def dashboard(request):
    path = dashboard_json_path()
    try:
        data = load_dashboard_data()
    except DashboardLoadError as exc:
        return render(
            request,
            "wmvi/dashboard.html",
            {
                "error": str(exc),
                "source_path": path,
            },
        )

    ingestion_rows = data.get("ingestion_daily") or []
    is_en_rows = data.get("is_en_counts_7d") or []
    term_rows = data.get("term_matches_per_day") or []
    podcast_summary = data.get("podcast_transcription_summary") or []
    podcast_daily = data.get("podcast_transcriptions_per_day") or []
    youtube_summary = data.get("youtube_transcription_summary") or []
    youtube_daily = data.get("youtube_transcriptions_per_day") or []

    context = {
        "error": None,
        "source_path": path,
        "generated_at": data.get("generated_at_utc") or "",
        "ingestion_table": build_table(ingestion_rows, ["day", "platform"]),
        "ingestion_chart": pivot_ingestion_chart(ingestion_rows),
        "is_en_table": build_table(is_en_rows, ["day", "platform"]),
        "is_en_chart": is_en_daily_totals_chart(is_en_rows),
        "term_table": build_table(term_rows, ["day"]),
        "term_chart": single_series_chart(term_rows, value_key="matches", label="matches"),
        "podcast": _transcription_context(
            title="Podcast transcriptions",
            summary_rows=podcast_summary,
            daily_rows=podcast_daily,
            chart_id="podcast-transcriptions-chart",
        ),
        "youtube": _transcription_context(
            title="YouTube transcriptions",
            summary_rows=youtube_summary,
            daily_rows=youtube_daily,
            chart_id="youtube-transcriptions-chart",
        ),
    }
    return render(request, "wmvi/dashboard.html", context)
