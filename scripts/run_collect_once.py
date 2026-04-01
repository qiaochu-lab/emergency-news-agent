from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emergency_intel.collect.service import collect_items
from emergency_intel.config import DATA_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect raw items once")
    parser.add_argument(
        "--source-registry",
        type=Path,
        default=DATA_DIR / "source_registry.json",
        help="Path to a source registry JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "raw" / "items.json",
        help="Path to write collected raw items",
    )
    args = parser.parse_args()

    items, errors = collect_items(args.source_registry, args.output)
    print(json.dumps({"items_collected": len(items), "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
