from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emergency_intel.audit import audit_raw_item
from emergency_intel.collect.service import load_raw_items


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit raw items and label likely full text vs summary/landing page")
    parser.add_argument("path", nargs="?", default="data/raw/items.json", help="Path to the raw items JSON file")
    args = parser.parse_args()

    items = load_raw_items(Path(args.path))
    audited = [audit_raw_item(item) for item in items]
    print(json.dumps(audited, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
