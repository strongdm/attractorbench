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

**Latest batch (2026-02-25):** Five new runs including the first GPT-5.3-codex and GPT-5.2 (high effort) trials. GPT-5.3-codex debuts strong at 0.854 mean with the highest full-stack conformance (87.5%) and **perfect T3 conformance** (27/27, 100%) — the first agent to achieve this. Sonnet 4.6 retains the overall lead at 0.870 mean (boosted by a clean tier0 run). Opus 4.6 improved to 0.808 mean, overtaking its v3 result. GPT-5.2 with high reasoning effort scored 0.730 (full-stack 0.560), trailing GPT-5.3-codex significantly.

The overall score leader remains `sonnet46-v3` (0.870 mean), but `gpt53codex-v1` holds the best full-stack score (0.808) and best single-tier conformance (T3: 100%). Sonnet and Opus continue to dominate T2 conformance (89.5% and 84.2% respectively). Gemini remains the fastest and cheapest but trails substantially on conformance.

> **v1.0.0 → v2.0.0 migration:** Scores are not directly comparable across versions.
> v1.0.0 runs had T3 gated (always 0%) and no judge component. v2.0.0 runs typically
> score higher because T3 conformance is now measured.

## Current Bests (bench_version=2.0.0)

Criteria:
- Best score: highest composite score (mean across tasks).
- Best full-stack: highest full-stack composite (excludes tier0).
- Best speed: shortest wall time among runs with score > 0.
- Best token efficiency: lowest tokens per score point.
- Best dollar efficiency: lowest $ per score point.

| Metric | Run | Agent | Model | Value |
|--------|-----|-------|-------|-------|
| Best score | sonnet46-v3 | claude-code | claude-sonnet-4-6 | 0.870 |
| Best full-stack | gpt53codex-v1 | codex | gpt-5.3-codex | 0.808 |
| Best speed | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | 12m26s |
| Best token efficiency | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | 4.1M tokens/point |
| Best dollar efficiency | gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | $8.80/point |

## Snapshot Table (bench_version=2.0.0, Best Per Agent/Model, By Score)

| Run | Agent | Model | Score | T1 | T2 | T3 | Judge | Tokens | Time | Cost |
|-----|-------|-------|------:|---:|---:|---:|------:|-------:|-----:|-----:|
| sonnet46-v3 | claude-code | claude-sonnet-4-6 | 0.870 | 82.3% | 68.4% | 88.9% | 60.0% | 14.9M | 2h07m | $6.41 |
| gpt53codex-v1 | codex | gpt-5.3-codex | 0.854 | 82.3% | 79.0% | 100.0% | 70.0% | - | 16m44s | - |
| opus46-v8 | claude-code | claude-opus-4-6 | 0.808 | 23.5% | 84.2% | 88.9% | 50.0% | - | 38m49s | - |
| gpt52-high-v1 | codex | gpt-5.2 (high) | 0.730 | 23.5% | 57.9% | 92.6% | 50.0% | - | 19m21s | - |
| gemini31ct-v7 | gemini-cli | gemini-3.1-pro-preview-customtools | 0.631 | 20.6% | 31.6% | 22.2% | 50.0% | 3.3M | 27m56s | - |

## Historical Bests (bench_version=1.0.0)

| Run | Agent | Model | Score | T1 | T2 | T3 | Tokens | Time | Cost |
|-----|-------|-------|------:|---:|---:|---:|-------:|-----:|-----:|
| sonnet46-v2 | claude-code | claude-sonnet-4-6 | 0.746 | - | - | 0% | 4.8M | 27m35s | $6.79 |
| sonnet46-v1 | claude-code | claude-sonnet-4-6 | 0.729 | - | - | 0% | 26.3M | 39m34s | $11.14 |
| gpt52-codex-v1 | codex | gpt-5.2 | 0.701 | - | - | 0% | 5.1M | 18m21s | $9.77 |
| opus46-v1 | claude-code | claude-opus-4-6 | 0.680 | - | - | 0% | 16.6M | 33m05s | $15.05 |
| gemini31ct-v1 | gemini-cli | gemini-3.1-pro-preview-customtools | 0.624 | - | - | 0% | 191K | 15m59s | $0.41 |
