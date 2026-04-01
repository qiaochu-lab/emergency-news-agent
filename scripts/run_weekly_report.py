from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emergency_intel.pipeline import run_weekly_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the weekly intelligence report")
    parser.add_argument("--use-mock-data", action="store_true", help="Use built-in sample items instead of live collection")
    parser.add_argument(
        "--source-registry",
        type=Path,
        help="Optional path to a source registry JSON file for live collection",
    )
    args = parser.parse_args()
    result = run_weekly_pipeline(use_mock_data=args.use_mock_data, source_registry_path=args.source_registry)
    print(json.dumps({k: v for k, v in result.items() if k != "report_markdown" and k != "report"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
