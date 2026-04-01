# Emergency Intelligence Weekly Report System

An MVP pipeline for producing weekly Markdown intelligence reports covering AI, drones, communications, and emergency response.

## What this repo does

- Collects items from news, official announcements, and papers
- Normalizes them into a single schema
- Deduplicates overlapping coverage
- Classifies by taxonomy
- Scores by importance and heat
- Generates structured analysis through a provider abstraction
- Renders a weekly Markdown report for decision-makers

## Quick start

```bash
python3 -m unittest discover -s tests
python3 scripts/run_collect_once.py
python3 scripts/run_collect_once.py --source-registry data/source_registry_live_quick.json --output data/raw/live_quick_items.json
python3 scripts/run_weekly_report.py --use-mock-data
python3 scripts/audit_raw_items.py
```

Generated outputs land in `outputs/weekly/`.

## Project management

For a product-manager view of the project, see `docs/pm_project_management.md`.

## Configuration

The app supports both shell environment variables and a repo-local `.env` file.

1. Copy `.env.example` to `.env`
2. Fill in your model provider and API key
3. Run the scripts normally

Example:

```bash
cp .env.example .env
```

Supported settings:

- `EI_PROVIDER`: `mock` or `openai_compatible`
- `EI_MODEL`: model name for the provider
- `EI_API_BASE`: OpenAI-compatible `/chat/completions` base URL
- `EI_API_KEY`: API key for the configured provider
- `EI_X_BEARER_TOKEN`: bearer token for X API sources
- `EI_X_API_KEY` / `EI_X_API_SECRET`: optional X app credentials for future user-context flows
- `EI_ANALYSIS_MIN_SCORE`: minimum final score for LLM analysis, default `6.0`
- `EI_COLLECT_TIMEOUT_SECONDS`: per-source collection timeout, default `20`
- `EI_ENRICH_TIMEOUT_SECONDS`: per-item full-text enrichment timeout, default `15`
- `EI_SCHEDULE_WEEKDAY`: weekday for scheduler, default `MON`
- `EI_SCHEDULE_HOUR`: hour for scheduler, default `9`
- `EI_TIMEZONE`: informational timezone label, default `Asia/Shanghai`

Example for Zhipu GLM:

```dotenv
EI_PROVIDER=openai_compatible
EI_API_BASE=https://open.bigmodel.cn/api/paas/v4/chat/completions
EI_API_KEY=your_new_key_here
EI_X_BEARER_TOKEN=your_x_bearer_token_here
EI_MODEL=glm-4.6
```

## Repository layout

- `docs/`: business rules and source guidance
- `data/`: intermediate pipeline artifacts
- `outputs/weekly/`: rendered weekly reports
- `src/emergency_intel/`: application package
- `scripts/`: manual and scheduled entrypoints
- `tests/`: lightweight unit and integration tests
