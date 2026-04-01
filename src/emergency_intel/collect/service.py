from __future__ import annotations

import sys
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, as_completed
from pathlib import Path
from typing import List, Tuple

from emergency_intel.collect.adapters import build_adapters
from emergency_intel.models import RawItem
from emergency_intel.utils import read_json, write_json

_PARALLEL_WORKERS = 5


def collect_items(
    source_registry_path: Path,
    raw_output_path: Path,
    per_source_timeout_seconds: int = 25,
) -> Tuple[List[RawItem], List[str]]:
    registry = read_json(source_registry_path, default=[])
    adapters = build_adapters(registry)  # type: ignore[arg-type]
    collected: List[RawItem] = []
    errors: List[str] = []

    total = len(adapters)
    overall_timeout = per_source_timeout_seconds * 6  # generous budget for all sources
    print(
        f"[采集] 开始并行抓取 {total} 个信源 "
        f"(workers={_PARALLEL_WORKERS}, per_source={per_source_timeout_seconds}s, total_budget={overall_timeout}s)...",
        flush=True,
    )

    with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as pool:
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
                    items = future.result()  # future is already done — no extra timeout needed
                    collected.extend(items)
                    print(f"[采集] ({done_count}/{total}) ✓ {name}: {len(items)} 条", flush=True)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
                    print(f"[采集] ({done_count}/{total}) ✗ {name}: {exc}", file=sys.stderr, flush=True)
        except TimeoutError:
            # Some sources never completed within the overall budget
            remaining = [n for f, n in future_to_name.items() if not f.done()]
            for name in remaining:
                errors.append(f"{name}: overall budget exceeded ({overall_timeout}s)")
            print(f"[采集] 总预算超时，{len(remaining)} 个信源未响应", flush=True)

    print(f"[采集] 完成：共 {len(collected)} 条，{len(errors)} 个错误", flush=True)
    write_json(raw_output_path, [item.to_dict() for item in collected])
    return collected, errors


def load_raw_items(raw_output_path: Path) -> List[RawItem]:
    payload = read_json(raw_output_path, default=[])
    return [RawItem(**entry) for entry in payload]  # type: ignore[arg-type]
