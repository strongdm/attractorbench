# AttractorBench Run Log

Comprehensive historical run ledger for AttractorBench.

- Historical entries are retained even when benchmark versions evolve.
- From **2026-02-23** onward, every run should record:
  - `bench_version` (for comparability scope)
  - `effort` (for example: `medium`, `high`, `extra_high`)

Comparability policy:
- **Only runs with the same `bench_version` are directly comparable.**
- Breaking benchmark changes are versioned; comparability naturally decays over time.

## bench_version=2.0.0 (2026-02-25)

Changes: T2→T3 gate removed, LLM-as-judge added (15% weight), scoring formula updated.

| Run | Agent | Model | Effort | Tasks | Score | T1 | T2 | T3 | Judge | Tokens | Time | Cost | Date | Notes |
|-----|-------|-------|--------|------:|------:|---:|---:|---:|------:|-------:|-----:|-----:|------|-------|
| gpt53codex-v3 | codex | gpt-5.3-codex | unknown | 2 | 0.833 | 73.5% | 84.2% | 96.3% | 53.3% | - | 22m41s | - | 2026-02-25 | judge upgraded to gpt-5.2 |
| gpt53codex-v1 | codex | gpt-5.3-codex | unknown | 2 | 0.854 | 82.3% | 79.0% | 100.0% | 70.0% | - | 16m44s | - | 2026-02-25 | first GPT-5.3-codex run; perfect T3; gpt-4o judge |
| sonnet46-v3 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.870 | 82.3% | 68.4% | 88.9% | 60.0% | 14.9M | 2h07m | $6.41 | 2026-02-25 | first clean v2.0.0 sonnet run |
| opus46-v8 | claude-code | claude-opus-4-6 | unknown | 2 | 0.808 | 23.5% | 84.2% | 88.9% | 50.0% | - | 38m49s | - | 2026-02-25 | improved over v3 |
| opus46-v3 | claude-code | claude-opus-4-6 | unknown | 2 | 0.784 | 23.5% | 89.5% | 92.6% | 60.0% | 10.8M | 25m55s | $7.19 | 2026-02-25 | first clean v2.0.0 opus run |
| gpt52-high-v3 | codex | gpt-5.2 (high) | high | 2 | 0.750 | 23.5% | 73.7% | 92.6% | 50.0% | - | 22m19s | - | 2026-02-25 | judge upgraded to gpt-5.2 |
| gpt52-high-v1 | codex | gpt-5.2 (high) | high | 2 | 0.730 | 23.5% | 57.9% | 92.6% | 50.0% | - | 19m21s | - | 2026-02-25 | first GPT-5.2 high-effort v2.0.0 run; gpt-4o judge |
| sonnet46-v8 | claude-code | claude-sonnet-4-6 | unknown | 1 | 0.806 | 73.5% | 89.5% | 96.3% | 50.0% | - | 24m41s | - | 2026-02-25 | tier0 RuntimeError (1 trial only); full-stack 0.806 |
| gemini31ct-v7 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.631 | 20.6% | 31.6% | 22.2% | 50.0% | 3.3M | 27m56s | - | 2026-02-25 | slight improvement over v3 |
| gemini31ct-v3 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.624 | 17.6% | 15.8% | 55.6% | 50.0% | 2.5M | 12m26s | $5.49 | 2026-02-25 | first clean v2.0.0 gemini run |
| opus46-v2 | claude-code | claude-opus-4-6 | unknown | 2 | 0.815 | 85.3% | 94.7% | 0.0% | 60.0% | 20.3M | 37m19s | $12.82 | 2026-02-24 | T3 crashed (diags_list null bug) |
| gemini31ct-v2 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.599 | 14.7% | 15.8% | 18.5% | 50.0% | 151K | 11m40s | $0.32 | 2026-02-24 | pre-diags_list fix |
| sonnet46-v1 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.624 | 14.7% | 15.8% | 18.5% | 50.0% | 26.9M | 35m34s | $10.33 | 2026-02-24 | first v2.0.0 run, pre-diags_list fix |

## bench_version=1.0.0 (2026-02-22 to 2026-02-24)

Scoring: 5% build + 5% self-test + 30% T1 + 30% T2 + 30% T3 (T3 always gated to 0%).

| Run | Agent | Model | Effort | Tasks | Score | Tokens | Time | Cost | Date | Notes |
|-----|-------|-------|--------|------:|------:|-------:|-----:|-----:|------|-------|
| sonnet46-v2 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.746 | 4.8M | 27m35s | $6.79 | 2026-02-23 | |
| sonnet46-v1 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.729 | 26.3M | 39m34s | $11.14 | 2026-02-23 | |
| gpt52-codex-v1 | codex | gpt-5.2 | unknown | 2 | 0.701 | 5.1M | 18m21s | $9.77 | 2026-02-23 | |
| opus46-v1 | claude-code | claude-opus-4-6 | unknown | 2 | 0.680 | 16.6M | 33m05s | $15.05 | 2026-02-23 | |
| gemini31ct-opencode-v1 | opencode | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.640 | 6.9M | 20m15s | $14.34 | 2026-02-23 | |
| gemini31ct-v1 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.624 | 191K | 15m59s | $0.41 | 2026-02-23 | tokens underreported (no LiteLLM proxy) |
| gpt52-codex-v2 | codex | gpt-5.2 | high | 2 | 0.596 | 12.1M | 31m28s | $22.53 | 2026-02-23 | |
| gemini31-v3 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.559 | 181K | 9m34s | $0.41 | 2026-02-22 | tokens underreported |
| gpt52codex-codex-v1 | codex | gpt-5.2-codex | unknown | 2 | 0.525 | 6.7M | 18m38s | $12.67 | 2026-02-23 | |
| gemini31-v1 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.450 | 91K | 1m35s | $0.23 | 2026-02-22 | |
| gemini31-v2 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.383 | 58K | 1m22s | $0.15 | 2026-02-22 | |
| gemini25pro-v1 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.450 | 448K | 2m09s | $0.65 | 2026-02-22 | |
| gemini25pro-v3 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.550 | 22.5M | 35m12s | $29.74 | 2026-02-22 | |
| gemini25pro-v2 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.275 | 7.5M | 13m24s | $9.96 | 2026-02-22 | |
