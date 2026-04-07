from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from emergency_intel.models import RawItem
from emergency_intel.utils import normalize_whitespace, slugify, utc_now_iso

_TAVILY_API_URL = "https://api.tavily.com/search"
_QUERIES_PATH = Path(__file__).resolve().parents[3] / "data" / "tavily_queries.json"


def collect_tavily_items(
    api_key: str,
    queries_path: Path | None = None,
) -> List[RawItem]:
    """
    Run all configured Tavily queries and return deduplicated RawItems.
    Returns an empty list if api_key is blank or the queries file is missing/disabled.
    """
    if not api_key:
        return []

    path = queries_path or _QUERIES_PATH
    if not path.exists():
        return []

    config: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if not config.get("enabled", True):
        return []

    search_depth: str = config.get("search_depth", "basic")
    max_results: int = int(config.get("max_results_per_query", 5))
    days: int = int(config.get("days", 7))
    domains_config: Dict[str, List[str]] = config.get("domains", {})

    items: List[RawItem] = []
    seen_urls: set[str] = set()
    total_queries = sum(len(qs) for qs in domains_config.values())
    done = 0

    for domain, queries in domains_config.items():
        for query in queries:
            done += 1
            try:
                results = _search(api_key, query, search_depth, max_results, days)
                new_count = 0
                for result in results:
                    url = (result.get("url") or "").strip()
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    items.append(_to_raw_item(result, domain))
                    new_count += 1
                print(
                    f"[Tavily] ({done}/{total_queries}) '{query[:50]}' → {new_count} 条",
                    flush=True,
                )
                time.sleep(0.3)
            except Exception as exc:
                print(f"[Tavily] ({done}/{total_queries}) ✗ '{query[:50]}': {exc}", flush=True)

    print(f"[Tavily] 完成：共 {len(items)} 条不重复内容", flush=True)
    return items


def _search(
    api_key: str,
    query: str,
    search_depth: str,
    max_results: int,
    days: int,
) -> List[Dict[str, Any]]:
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "days": days,
        "include_answer": False,
        "include_raw_content": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        _TAVILY_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    return data.get("results", [])


def _to_raw_item(result: Dict[str, Any], domain: str) -> RawItem:
    url: str = (result.get("url") or "").strip()
    title: str = normalize_whitespace(result.get("title") or "")
    content: str = normalize_whitespace(result.get("content") or "")
    published: str = result.get("published_date") or utc_now_iso()

    parsed = urlparse(url)
    source_name = parsed.netloc.replace("www.", "") or "tavily"
    source_type = _infer_source_type(url)

    return RawItem(
        id=f"tavily-{slugify(url[:80])}",
        source_type=source_type,
        source_name=source_name,
        title=title or "（无标题）",
        url=url,
        published_at=published,
        language="en",
        raw_text=content,
        content_depth="summary",
        body_extraction_status="tavily_search",
    )


def _infer_source_type(url: str) -> str:
    u = url.lower()
    if any(d in u for d in ("arxiv.org", "researchgate.net", "ieee.org", "acm.org", "scholar.google")):
        return "paper"
    if any(d in u for d in (".gov", "fema.gov", "fcc.gov", "itu.int", "3gpp.org", "etsi.org", "cisa.gov")):
        return "official"
    if any(d in u for d in ("blog.", "/blog/", "medium.com", "substack.com")):
        return "blog"
    return "news"
