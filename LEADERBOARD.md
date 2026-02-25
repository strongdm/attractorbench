# AttractorBench Leaderboard Snapshot

**As of date:** 2026-02-25

This file is a **curated summary snapshot** (manually maintained, see [docs/runbook/](docs/runbook/)).
For the complete historical ledger, see [RUN_LOG.md](RUN_LOG.md).

Comparability policy:
- Breaking benchmark changes are versioned.
- Only runs on the same benchmark version are directly comparable.
- Historical logs are still retained for context and trend analysis.

## Narrative

**Benchmark v2.0.0** introduced two major changes:
1. **T2→T3 gate removed** — T3 conformance now runs unconditionally (was previously skipped when T2's `process_input` test failed, forfeiting 30% of the composite).
2. **LLM-as-judge evaluation** — a new Phase 4 evaluates 5 dimensions (spec coverage, architectural compliance, error handling, test quality, code quality) via GPT-4o judge calls through the LiteLLM proxy.

New scoring formula: `5% build + 5% self-test + 25% T1 + 25% T2 + 25% T3 + 15% judge` (falls back to 30/30/30 without judge).

The top composite score is `sonnet46-v3` (0.870 mean, 0.739 full-stack).
Opus shows the highest per-tier conformance (T2: 89.5%, T3: 92.6%) but lower T1 (23.5%).

> **v1.0.0 → v2.0.0 migration:** Scores are not directly comparable across versions.
> v1.0.0 runs had T3 gated (always 0%) and no judge component. v2.0.0 runs typically
> score higher because T3 conformance is now measured.

## Current Bests (bench_version=2.0.0)

Criteria:
- Best score: highest composite score (mean across tasks).
- Best speed: shortest wall time among runs with score > 0.
- Best token efficiency: lowest tokens per score point.
- Best dollar efficiency: lowest $ per score point.

| Metric | Run | Agent | Model | Value |
|--------|-----|-------|-------|-------|
| Best score | sonnet46-v3 | claude-code | claude-sonnet-4-6 | 0.870 |
| Best speed | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | 12m26s |
| Best token efficiency | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | 4.1M tokens/point |
| Best dollar efficiency | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | $8.80/point |

## Snapshot Table (bench_version=2.0.0, By Score)

| Run | Agent | Model | Score | T1 | T2 | T3 | Judge | Tokens | Time | Cost |
|-----|-------|-------|------:|---:|---:|---:|------:|-------:|-----:|-----:|
| sonnet46-v3 | claude-code | claude-sonnet-4-6 | 0.870 | 82.3% | 68.4% | 88.9% | 60.0% | 14.9M | 2h07m | $6.41 |
| opus46-v3 | claude-code | claude-opus-4-6 | 0.784 | 23.5% | 89.5% | 92.6% | 60.0% | 10.8M | 25m55s | $7.19 |
| gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | 0.624 | 17.6% | 15.8% | 55.6% | 50.0% | 2.5M | 12m26s | $5.49 |

## Historical Bests (bench_version=1.0.0)

| Run | Agent | Model | Score | T1 | T2 | T3 | Tokens | Time | Cost |
|-----|-------|-------|------:|---:|---:|---:|-------:|-----:|-----:|
| sonnet46-v2 | claude-code | claude-sonnet-4-6 | 0.746 | - | - | 0% | 4.8M | 27m35s | $6.79 |
| sonnet46-v1 | claude-code | claude-sonnet-4-6 | 0.729 | - | - | 0% | 26.3M | 39m34s | $11.14 |
| gpt52-codex-v1 | codex | gpt-5.2 | 0.701 | - | - | 0% | 5.1M | 18m21s | $9.77 |
| opus46-v1 | claude-code | claude-opus-4-6 | 0.680 | - | - | 0% | 16.6M | 33m05s | $15.05 |
| gemini31ct-v1 | gemini-cli | gemini-3.1-pro-preview-customtools | 0.624 | - | - | 0% | 191K | 15m59s | $0.41 |
