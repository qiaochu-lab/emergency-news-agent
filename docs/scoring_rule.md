# Scoring Rule

## Purpose

Rank items for weekly analyst attention using transparent rules before any LLM step.

## Importance Score

Base range: `0-10`

Signals that increase importance:

- Official policy, procurement, regulation, or standard release
- Deployment in real emergency or defense-adjacent setting
- Major funding, acquisition, or ecosystem partnership
- Breakthrough research with operational relevance
- Cross-domain implications across AI, drones, communications, and emergency response

Suggested scoring guide:

- `8-10`: strategic significance
- `5-7`: operational relevance
- `2-4`: useful background
- `0-1`: low intelligence value

## Heat Score

Base range: `0-10`

Signals that increase heat:

- Multiple credible outlets covering the same event
- High recency within the report week
- Follow-on developments or strong public attention
- Repeated mentions across domains

## Final Score

`final_score = importance_score * 0.7 + heat_score * 0.3`

## Default Escalation Rules

- `final_score >= 8`: must appear in Top Signals
- `final_score >= 6`: eligible for LLM analysis
- `final_score < 6`: include only if needed for context
