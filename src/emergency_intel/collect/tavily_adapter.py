from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from emergency_intel.models import RawItem
from emergency_intel.utils import normalize_whitespace, slugify, utc_now_iso

_RAW_CONTENT_LIMIT = 3000  # chars — Tavily raw_content 截断上限

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
    default_max_results: int = int(config.get("max_results_per_query", 3))
    days: int = _dynamic_days(config.get("days"))
    topic: str = config.get("topic", "general")
    include_answer: bool = bool(config.get("include_answer", False))
    domains_config: Dict[str, Any] = config.get("domains", {})

    items: List[RawItem] = []
    seen_urls: set[str] = set()

    # 支持新格式 {"max_results": N, "queries": [...]} 和旧格式 [...]
    def _parse_domain(val: Any) -> tuple[List[str], int]:
        if isinstance(val, dict):
            return val.get("queries", []), int(val.get("max_results", default_max_results))
        return list(val), default_max_results

    total_queries = sum(
        len(_parse_domain(v)[0]) for v in domains_config.values()
    )
    done = 0

    for domain, domain_val in domains_config.items():
        queries, max_results = _parse_domain(domain_val)
        for query in queries:
            done += 1
            try:
                results = _search(api_key, query, search_depth, max_results, days, topic, include_answer)
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

    print(f"[Tavily] 完成：共 {len(items)} 条不重复内容（days={days}）", flush=True)
    return items


def _dynamic_days(configured: Any) -> int:
    """
    动态计算 Tavily days 参数，确保覆盖完整的上一个 ISO 周（Mon–Sun）。

    若配置文件显式设了非 7 的值，直接用配置值（便于调试覆盖）。
    否则按运行日计算：days = today.weekday() + 7，
      周一运行 → 7，周三运行 → 9，周日运行 → 13。
    """
    if configured is not None and int(configured) != 7:
        return int(configured)
    today = date.today()
    return today.weekday() + 7


def _search(
    api_key: str,
    query: str,
    search_depth: str,
    max_results: int,
    days: int,
    topic: str = "general",
    include_answer: bool = False,
) -> List[Dict[str, Any]]:
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "days": days,
        "topic": topic,
        "include_answer": include_answer,
        "include_raw_content": True,
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
    published: str = result.get("published_date") or utc_now_iso()

    # 优先用 raw_content（全文），截断后回落到 content（摘要）
    raw_content: str = normalize_whitespace(result.get("raw_content") or "")
    summary: str = normalize_whitespace(result.get("content") or "")
    if raw_content:
        body = raw_content[:_RAW_CONTENT_LIMIT]
        depth = "full"
    else:
        body = summary
        depth = "summary"

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
        raw_text=body,
        content_depth=depth,
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
