from __future__ import annotations

import sys
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, as_completed
from pathlib import Path
from typing import List, Tuple

from emergency_intel.collect.adapters import build_adapters
from emergency_intel.collect.manual import load_manual_items
from emergency_intel.collect.tavily_adapter import collect_tavily_items
from emergency_intel.models import RawItem
from emergency_intel.utils import read_json, write_json

_PARALLEL_WORKERS = 5


def collect_items(
    source_registry_path: Path,
    raw_output_path: Path,
    per_source_timeout_seconds: int = 25,
    manual_dir: Path | None = None,
    tavily_api_key: str = "",
) -> Tuple[List[RawItem], List[str], List[dict]]:
    registry = read_json(source_registry_path, default=[])

    # Tavily先跑：优先获取高质量搜索结果，web/playwright慢源内容由Tavily覆盖
    collected: List[RawItem] = []
    errors: List[str] = []
    source_stats: dict[str, dict] = {}

    if tavily_api_key:
        print("[采集] Tavily搜索先行...", flush=True)
        try:
            tavily_items = collect_tavily_items(tavily_api_key)
            collected.extend(tavily_items)
            source_stats["[Tavily搜索]"] = {
                "name": "[Tavily搜索]",
                "source_type": "search",
                "access_method": "tavily",
                "count": len(tavily_items),
                "status": "ok",
            }
            print(f"[采集] Tavily完成：{len(tavily_items)} 条", flush=True)
        except Exception as exc:
            errors.append(f"Tavily: {exc}")
            print(f"[采集] Tavily失败: {exc}", file=sys.stderr, flush=True)

    # 只跑 RSS/API/github_json_feed，web和playwright交给Tavily
    _RSS_METHODS = {"rss", "api", "github_json_feed"}
    adapters = [
        a for a in build_adapters(registry)  # type: ignore[arg-type]
        if str(a.source.get("access_method", "")) in _RSS_METHODS  # type: ignore[attr-defined]
    ]

    source_stats.update({
        str(a.source.get("name", "unknown")): {  # type: ignore[attr-defined]
            "name": str(a.source.get("name", "unknown")),  # type: ignore[attr-defined]
            "source_type": str(a.source.get("source_type", "")),  # type: ignore[attr-defined]
            "access_method": str(a.source.get("access_method", "")),  # type: ignore[attr-defined]
            "count": 0,
            "status": "pending",
        }
        for a in adapters
    })

    total = len(adapters)
    # Overall budget: enough for all sources to run in batches through the worker pool
    overall_timeout = per_source_timeout_seconds * (max(1, total // _PARALLEL_WORKERS) + 2)
    print(
        f"[采集] 开始并行抓取 {total} 个信源 "
        f"(workers={_PARALLEL_WORKERS}, per_source={per_source_timeout_seconds}s, total_budget={overall_timeout}s)...",
        flush=True,
    )

    pool = ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS)
    future_to_name: dict[Future, str] = {
        pool.submit(adapter.fetch): str(adapter.source.get("name", "unknown"))  # type: ignore[attr-defined]
        for adapter in adapters
    }
    done_count = 0
    try:
        for future in as_completed(future_to_name, timeout=overall_timeout):
            name = future_to_name[future]
            done_count += 1
            try:
                items = future.result(timeout=per_source_timeout_seconds)
                collected.extend(items)
                source_stats[name]["count"] = len(items)
                source_stats[name]["status"] = "ok"
                print(f"[采集] ({done_count}/{total}) ✓ {name}: {len(items)} 条", flush=True)
            except TimeoutError:
                errors.append(f"{name}: 超时跳过 (>{per_source_timeout_seconds}s)")
                source_stats[name]["status"] = f"skipped (timeout >{per_source_timeout_seconds}s)"
                print(f"[采集] ({done_count}/{total}) ⏭ {name}: 超时跳过", file=sys.stderr, flush=True)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                source_stats[name]["status"] = f"error: {exc}"
                print(f"[采集] ({done_count}/{total}) ✗ {name}: {exc}", file=sys.stderr, flush=True)
    except TimeoutError:
        remaining = [n for f, n in future_to_name.items() if not f.done()]
        for name in remaining:
            errors.append(f"{name}: 总预算超时跳过 ({overall_timeout}s)")
            source_stats[name]["status"] = f"skipped (total timeout {overall_timeout}s)"
        print(f"[采集] 总预算超时，{len(remaining)} 个信源跳过", flush=True)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Merge manual Grok input for the current week
    if manual_dir is not None:
        manual_items = load_manual_items(manual_dir)
        collected.extend(manual_items)
        if manual_items:
            source_stats["[手动输入]"] = {
                "name": "[手动输入]",
                "source_type": "manual",
                "access_method": "manual",
                "count": len(manual_items),
                "status": "ok",
            }

    print(f"[采集] 完成：共 {len(collected)} 条，{len(errors)} 个错误", flush=True)
    write_json(raw_output_path, [item.to_dict() for item in collected])
    return collected, errors, list(source_stats.values())


def load_raw_items(raw_output_path: Path) -> List[RawItem]:
    payload = read_json(raw_output_path, default=[])
    return [RawItem(**entry) for entry in payload]  # type: ignore[arg-type]
