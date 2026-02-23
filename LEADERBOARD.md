# AttractorBench Leaderboard Snapshot

**As of date:** 2026-02-23

This file is now a **curated summary snapshot**, not an auto-generated full ranking dump.
For the complete historical ledger, see [RUN_LOG.md](RUN_LOG.md).

Comparability policy:
- Breaking benchmark changes are versioned.
- Only runs on the same benchmark version are directly comparable.
- Historical logs are still retained for context and trend analysis.

## Narrative

Current results are from `bench_version=1.0.0` historical runs.
The top composite score observed so far is from `sonnet46-stacked-v2` (0.746), while efficiency leaders are currently Gemini 3.1 preview runs on a lower-score regime.
Treat this as a moving snapshot, not a stable scientific ranking.

## Current Bests

Criteria:
- Best score: highest composite score.
- Best speed: shortest wall time among runs with score > 0.
- Best token efficiency: lowest tokens per score point among runs with score > 0.
- Best dollar efficiency: lowest $ per score point among runs with score > 0.

| Metric | Run | Agent | Model | Value |
|--------|-----|-------|-------|-------|
| Best score | sonnet46-stacked-v2 | claude-code | claude-sonnet-4-6 | 0.746 |
| Best speed | gemini31-stacked-v2 | gemini-cli | gemini-3.1-pro-preview | 1m22s |
| Best token efficiency | gemini31-stacked-v2 | gemini-cli | gemini-3.1-pro-preview | ~153K tokens/point |
| Best dollar efficiency | gemini31-stacked-v2 | gemini-cli | gemini-3.1-pro-preview | ~$0.40/point |

## Snapshot Table (By Score)

| Run | Bench Version | Agent | Model | Effort | Score | Tokens | Time | Cost |
|-----|---------------|-------|-------|--------|------:|-------:|-----:|-----:|
| sonnet46-stacked-v2 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 0.746 | 4.8M | 27m35s | $6.79 |
| sonnet46-stacked-v1 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 0.729 | 26.3M | 39m34s | $11.14 |
| gpt52-codex-stacked-v1 | 1.0.0 | codex | gpt-5.2 | unknown | 0.701 | 5.1M | 18m21s | $9.77 |
| opus46-stacked-v1 | 1.0.0 | claude-code | claude-opus-4-6 | unknown | 0.680 | 16.6M | 33m05s | $15.05 |
| gemini31ct-opencode-v1 | 1.0.0 | opencode | gemini-3.1-pro-preview-customtools | unknown | 0.640 | 6.9M | 20m15s | $14.34 |
| gemini31ct-stacked-v1 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 0.624 | 191K | 15m59s | $0.41 |
| gpt52-codex-stacked-v2 | 1.0.0 | codex | gpt-5.2 | high | 0.596 | 12.1M | 31m28s | $22.53 |
| gemini31-stacked-v3 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview | unknown | 0.559 | 181K | 9m34s | $0.41 |
