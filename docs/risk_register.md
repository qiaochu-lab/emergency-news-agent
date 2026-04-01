# Risk Register

## Current Known Risks

### 1. Web source false positives

- Description: Some `web` sources may still yield landing pages, resource pages, or low-value overview content.
- Impact: Low-quality items may enter the scoring and analysis pipeline.
- Mitigation: Continue tightening screening rules and add source-specific extractors for priority sites.

### 2. Report repetition

- Description: When high-signal items are few, multiple sections may overuse the same event.
- Impact: The weekly report can feel repetitive or overly template-driven.
- Mitigation: Strengthen cross-item synthesis and diversify section-writing logic.

### 3. Provider variance

- Description: Different LLM providers may return uneven structure or quality.
- Impact: Report tone and field completeness may fluctuate.
- Mitigation: Use source-type-specific prompts, keep `mock` fallback, and validate key fields before rendering.

### 4. Weak signal reliability

- Description: Forum and social sources can surface useful but unverified signals.
- Impact: Risk of overstating emerging claims.
- Mitigation: Keep forum/social content lower-trust and require corroboration in report wording.
