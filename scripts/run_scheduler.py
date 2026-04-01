from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emergency_intel.config import Settings
from emergency_intel.pipeline import run_weekly_pipeline
from emergency_intel.scheduler import next_run_time


def main() -> int:
    settings = Settings()
    while True:
        now = datetime.now()
        target = next_run_time(now, settings.schedule_weekday, settings.schedule_hour)
        wait_seconds = max(1, int((target - now).total_seconds()))
        print(json.dumps({"next_run": target.isoformat(), "timezone": settings.timezone}, ensure_ascii=False))
        time.sleep(wait_seconds)
        result = run_weekly_pipeline()
        print(json.dumps({"report_path": result["report_path"], "items_selected": result["items_selected"]}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
