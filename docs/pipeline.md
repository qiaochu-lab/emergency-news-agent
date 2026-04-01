# Pipeline

## Stages

1. Collect raw items from source adapters
2. Normalize into unified schema
3. Deduplicate by canonical URL, normalized title, and content fingerprint
4. Classify by taxonomy and supporting tags
5. Score by importance and heat
6. Analyze high-signal items through provider abstraction
7. Render weekly Markdown report

## Failure Handling

- Persist stage outputs under `data/`
- Keep stages restartable
- Continue report generation when some sources fail
- Fall back to deterministic analysis when the provider is unavailable
