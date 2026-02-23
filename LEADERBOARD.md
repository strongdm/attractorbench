# AttractorBench Leaderboard Snapshot

**As of date:** 2026-02-23

This file is a **curated summary snapshot** (manually maintained, see [docs/runbook/](docs/runbook/)).
For the complete historical ledger, see [RUN_LOG.md](RUN_LOG.md).

Comparability policy:
- Breaking benchmark changes are versioned.
- Only runs on the same benchmark version are directly comparable.
- Historical logs are still retained for context and trend analysis.

## Narrative

All results are from `bench_version=1.0.0`.
The top composite score is `sonnet46-stacked-v2` (0.746).
Treat this as a moving snapshot; the ranking will stabilize after more burn-in runs.

> **Data quality note:** All `gemini-cli` runs prior to 2026-02-23 bypassed the LiteLLM proxy
> (`GOOGLE_GEMINI_BASE_URL` was not set), so their token counts and costs are drastically
> underreported (e.g., 191K tokens for gemini-cli vs 6.9M for opencode on the same model).
> Scores and wall times are unaffected. Efficiency metrics for these runs are marked with
> a dagger (&dagger;) and excluded from "Current Bests." See [docs/runbook/gemini-cli.md](docs/runbook/gemini-cli.md).

## Current Bests

Criteria:
- Best score: highest composite score.
- Best speed: shortest wall time among runs with score > 0.
- Best token efficiency: lowest tokens per score point among runs with **reliable** token data.
- Best dollar efficiency: lowest $ per score point among runs with **reliable** cost data.

| Metric | Run | Agent | Model | Value |
|--------|-----|-------|-------|-------|
| Best score | sonnet46-stacked-v2 | claude-code | claude-sonnet-4-6 | 0.746 |
| Best speed | gemini31-stacked-v3 | gemini-cli | gemini-3.1-pro-preview | 9m34s |
| Best token efficiency | sonnet46-stacked-v2 | claude-code | claude-sonnet-4-6 | ~6.4M tokens/point |
| Best dollar efficiency | sonnet46-stacked-v2 | claude-code | claude-sonnet-4-6 | ~$9.10/point |

## Snapshot Table (By Score)

| Run | Bench Version | Agent | Model | Effort | Score | Tokens | Time | Cost |
|-----|---------------|-------|-------|--------|------:|-------:|-----:|-----:|
| sonnet46-stacked-v2 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 0.746 | 4.8M | 27m35s | $6.79 |
| sonnet46-stacked-v1 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 0.729 | 26.3M | 39m34s | $11.14 |
| gpt52-codex-stacked-v1 | 1.0.0 | codex | gpt-5.2 | unknown | 0.701 | 5.1M | 18m21s | $9.77 |
| opus46-stacked-v1 | 1.0.0 | claude-code | claude-opus-4-6 | unknown | 0.680 | 16.6M | 33m05s | $15.05 |
| gemini31ct-opencode-v1 | 1.0.0 | opencode | gemini-3.1-pro-preview-customtools | unknown | 0.640 | 6.9M | 20m15s | $14.34 |
| gemini31ct-stacked-v1 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 0.624 | 191K &dagger; | 15m59s | $0.41 &dagger; |
| gpt52-codex-stacked-v2 | 1.0.0 | codex | gpt-5.2 | high | 0.596 | 12.1M | 31m28s | $22.53 |
| gemini31-stacked-v3 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview | unknown | 0.559 | 181K &dagger; | 9m34s | $0.41 &dagger; |

&dagger; Underreported: gemini-cli bypassed LiteLLM proxy. Actual token/cost likely 10-30x higher.
