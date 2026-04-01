from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Dict, List

from emergency_intel.analyze.provider import ProviderClient
from emergency_intel.analyze.service import analyze_items, screen_items
from emergency_intel.collect.service import collect_items
from emergency_intel.config import DATA_DIR, OUTPUTS_DIR, Settings
from emergency_intel.dedup.service import deduplicate_items
from emergency_intel.classify.service import classify_items
from emergency_intel.normalize.service import normalize_items
from emergency_intel.enrich.service import enrich_fulltext
from emergency_intel.report.html_renderer import render_report_html
from emergency_intel.report.service import build_weekly_report, render_report_markdown
from emergency_intel.run_log import append_weekly_run_log
from emergency_intel.score.service import score_items
from emergency_intel.utils import week_range_label, write_json


def run_weekly_pipeline(
    reference_date: date | None = None,
    use_mock_data: bool = False,
    settings: Settings | None = None,
    source_registry_path: Path | None = None,
) -> Dict[str, object]:
    settings = settings or Settings()
    if use_mock_data and settings.provider != "mock":
        settings = Settings(
            provider="mock",
            model="mock",
            api_base="",
            api_key="",
            x_bearer_token=settings.x_bearer_token,
            x_api_key=settings.x_api_key,
            x_api_secret=settings.x_api_secret,
            x_client_id=settings.x_client_id,
            x_client_secret=settings.x_client_secret,
            x_access_token=settings.x_access_token,
            x_access_token_secret=settings.x_access_token_secret,
            analysis_min_score=settings.analysis_min_score,
            schedule_weekday=settings.schedule_weekday,
            schedule_hour=settings.schedule_hour,
            timezone=settings.timezone,
        )
    source_registry = source_registry_path or (DATA_DIR / "source_registry.json")
    raw_path = DATA_DIR / "raw" / "items.json"
    normalized_path = DATA_DIR / "normalized" / "items.json"
    deduped_path = DATA_DIR / "deduped" / "items.json"
    classified_path = DATA_DIR / "classified" / "items.json"
    scored_path = DATA_DIR / "scored" / "items.json"
    screened_path = DATA_DIR / "scored" / "screened_items.json"
    enriched_path = DATA_DIR / "enriched" / "items.json"
    analyzed_path = DATA_DIR / "scored" / "analyzed_items.json"

    if use_mock_data:
        items = _mock_raw_items()
        write_json(raw_path, items)
        from emergency_intel.collect.service import load_raw_items

        raw_items = load_raw_items(raw_path)
        collection_errors: List[str] = []
    else:
        raw_items, collection_errors = collect_items(
            source_registry,
            raw_path,
            per_source_timeout_seconds=settings.collect_timeout_seconds,
            manual_dir=DATA_DIR / "manual",
        )

    normalized_items = normalize_items(raw_items, normalized_path)
    deduped_items, duplicates_removed = deduplicate_items(normalized_items, deduped_path)
    classified_items = classify_items(deduped_items, classified_path)
    scored_items = score_items(classified_items, scored_path)

    provider = ProviderClient(
        provider=settings.provider,
        model=settings.model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    enriched_items = enrich_fulltext(scored_items, enriched_path, timeout_seconds=settings.enrich_timeout_seconds)
    screened_items = screen_items(enriched_items, screened_path, provider, reference_date)
    analyzed_items = analyze_items(screened_items, analyzed_path, provider, settings.analysis_min_score)

    week_range = week_range_label(reference_date)
    report = build_weekly_report(analyzed_items, week_range)
    output_path = OUTPUTS_DIR / _report_filename(
        week_range,
        source_registry_path=source_registry,
        use_mock_data=use_mock_data,
    )
    markdown = render_report_markdown(report, output_path)
    html_path = output_path.with_suffix(".html")
    render_report_html(report, html_path)
    items_screened_in = len([item for item in screened_items if item.include_in_top_report])
    append_weekly_run_log(
        DATA_DIR.parent / "docs" / "weekly_run_log.md",
        source_registry_path=source_registry,
        items_collected=len(raw_items),
        items_screened_in=items_screened_in,
        items_selected=len(report.selected_items),
        duplicates_removed=duplicates_removed,
        report_path=output_path,
        collection_errors=collection_errors,
    )

    return {
        "collection_errors": collection_errors,
        "duplicates_removed": duplicates_removed,
        "items_collected": len(raw_items),
        "items_screened_in": items_screened_in,
        "items_selected": len(report.selected_items),
        "report_path": str(output_path),
        "report_markdown": markdown,
        "report": asdict(report),
    }


def _mock_raw_items() -> List[Dict[str, object]]:
    return [
        {
            "id": "mock-ai-emergency-1",
            "source_type": "news",
            "source_name": "Mock Tech News",
            "title": "AI coordination platform improves emergency response planning",
            "url": "https://example.com/ai-emergency-response",
            "published_at": "2026-03-22T08:00:00Z",
            "language": "en",
            "raw_text": "A new AI platform was deployed to improve emergency response planning, communications resilience, and situational awareness across agencies.",
        },
        {
            "id": "mock-drone-1",
            "source_type": "official",
            "source_name": "Mock Agency Release",
            "title": "Agency launches drone and satellite pilot for disaster mapping",
            "url": "https://example.com/drone-satellite-pilot",
            "published_at": "2026-03-21T12:00:00Z",
            "language": "en",
            "raw_text": "The official announcement describes a drone deployment paired with satellite communications for search and rescue during severe flooding.",
        },
        {
            "id": "mock-paper-1",
            "source_type": "paper",
            "source_name": "Mock Research Archive",
            "title": "Foundation model approach for resilient mesh communications in disaster zones",
            "url": "https://example.com/resilient-mesh-paper",
            "published_at": "2026-03-20T09:30:00Z",
            "language": "en",
            "raw_text": "This paper proposes an AI-assisted method to optimize mesh network recovery in emergency environments with damaged infrastructure.",
        },
    ]


def _report_filename(week_range: str, source_registry_path: Path, use_mock_data: bool) -> str:
    if " to " in week_range:
        start, end = week_range.split(" to ", 1)
        return f"应急周报_{start}_{end}.md"
    return f"应急周报_{week_range}.md"
