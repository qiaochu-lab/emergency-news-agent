from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from pathlib import Path
from typing import Iterable, List

from emergency_intel.collect.adapters import _download_response_text, _extract_best_body, _extract_og_image
from emergency_intel.models import ScoredItem
from emergency_intel.utils import normalize_whitespace, write_json


ENRICHABLE_SOURCE_TYPES = {"official", "news", "company", "blog"}

# High-score items get a larger text budget for deeper analysis
_HIGH_SCORE_THRESHOLD = 7.0
_MAX_CHARS_HIGH_SCORE = 20000
_MAX_CHARS_NORMAL = 12000


_ENRICH_WORKERS = 6


def enrich_fulltext(
    items: Iterable[ScoredItem],
    output_path: Path,
    timeout_seconds: int = 15,
) -> List[ScoredItem]:
    item_list = list(items)
    enriched: List[ScoredItem] = [None] * len(item_list)  # type: ignore[list-item]

    def _enrich_one(idx: int, item: ScoredItem) -> tuple[int, ScoredItem]:
        if not _should_enrich(item):
            return idx, _clone(
                item,
                body_extraction_status=item.body_extraction_status or "skipped",
                content_depth=item.content_depth or "summary",
            )

        html, full_text = _fetch_with_retry(item.url, timeout_seconds)

        if full_text is None:
            return idx, _clone(
                item,
                body_extraction_status="failed:timeout",
                content_depth=item.content_depth or "summary",
            )

        thumbnail = _extract_og_image(html or "", base_url=item.url) if html else ""

        max_chars = (
            _MAX_CHARS_HIGH_SCORE if item.final_score >= _HIGH_SCORE_THRESHOLD
            else _MAX_CHARS_NORMAL
        )
        min_acceptable = max(600, len(normalize_whitespace(item.raw_text)) + 200)

        if len(normalize_whitespace(full_text)) >= min_acceptable:
            return idx, _clone(
                item,
                raw_text=normalize_whitespace(full_text)[:max_chars],
                content_depth="fulltext",
                body_extraction_status="enriched",
                thumbnail_url=thumbnail,
            )
        return idx, _clone(
            item,
            body_extraction_status="fallback_summary",
            content_depth=item.content_depth or "summary",
            thumbnail_url=thumbnail,
        )

    with ThreadPoolExecutor(max_workers=_ENRICH_WORKERS) as executor:
        futures = {executor.submit(_enrich_one, i, item): i for i, item in enumerate(item_list)}
        for future in as_completed(futures):
            idx, result = future.result()
            enriched[idx] = result

    write_json(output_path, [entry.__dict__ for entry in enriched])
    return enriched


def _should_enrich(item: ScoredItem) -> bool:
    if item.source_type not in ENRICHABLE_SOURCE_TYPES:
        return False
    if item.report_content_type in {"resource", "podcast", "landing_page"}:
        return False
    if not item.url.startswith(("http://", "https://")):
        return False
    if item.source_type == "official":
        return item.final_score >= 3.0
    return item.include_in_top_report or item.final_score >= 5.0


def _fetch_with_retry(url: str, timeout_seconds: int) -> tuple[str | None, str | None]:
    """Fetch HTML and extracted text with one retry. Returns (html, text)."""
    result = _fetch_fulltext_with_timeout(url, timeout_seconds)
    if result[1] is not None:
        return result
    return _fetch_fulltext_with_timeout(url, timeout_seconds * 2)


def _fetch_fulltext_with_timeout(url: str, timeout_seconds: int) -> tuple[str | None, str | None]:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_fetch_html_and_text, url)
    try:
        return future.result(timeout=timeout_seconds)
    except Exception:
        return None, None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _fetch_html_and_text(url: str) -> tuple[str, str]:
    html = _download_response_text(url)
    text = normalize_whitespace(_extract_best_body(html))
    return html, text


def _clone(item: ScoredItem, **overrides: object) -> ScoredItem:
    payload = dict(item.__dict__)
    payload.update(overrides)
    payload.setdefault("thumbnail_url", "")
    return ScoredItem(**payload)
