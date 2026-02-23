# AttractorBench Run Log

Comprehensive historical run ledger for AttractorBench.

- Historical entries are retained even when benchmark versions evolve.
- From **2026-02-23** onward, every run should record:
  - `bench_version` (for comparability scope)
  - `effort` (for example: `medium`, `high`, `extra_high`)

Comparability policy:
- **Only runs with the same `bench_version` are directly comparable.**
- Breaking benchmark changes are versioned; comparability naturally decays over time.

| Run | Bench Version | Agent | Model | Effort | Tasks | Score | Tokens | Time | Tool Calls | Cost | Date | Notes |
|-----|---------------|-------|-------|--------|------:|------:|-------:|-----:|-----------:|-----:|------|-------|
| gemini25pro-stacked-v1 | 1.0.0 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.450 | 448K | 2m09s | 19 | $0.65 | 2026-02-22 | historical entry |
| gemini25pro-stacked-v2 | 1.0.0 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.275 | 7.5M | 13m24s | 155 | $9.96 | 2026-02-22 | historical entry |
| gemini25pro-stacked-v3 | 1.0.0 | gemini-cli | gemini-2.5-pro | unknown | 2 | 0.550 | 22.5M | 35m12s | 168 | $29.74 | 2026-02-22 | historical entry |
| gemini30flash-stacked-v1 | 1.0.0 | gemini-cli | gemini-3.0-flash | unknown | 2 | 0.000 | 0 | 7s | -| -| 2026-02-23 | historical entry |
| gemini31-opencode-v1 | 1.0.0 | opencode | gemini-3.1-pro-preview | unknown | 2 | 0.000 | -| 7s | -| -| 2026-02-23 | historical entry |
| gemini31-stacked | 1.0.0 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.450 | 91K | 1m35s | 7 | $0.23 | 2026-02-22 | historical entry |
| gemini31-stacked-v2 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.383 | 58K | 1m22s | 6 | $0.15 | 2026-02-22 | historical entry |
| gemini31-stacked-v3 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview | unknown | 2 | 0.559 | 181K | 9m34s | 53 | $0.41 | 2026-02-22 | historical entry |
| gemini31ct-opencode-v1 | 1.0.0 | opencode | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.640 | 6.9M | 20m15s | 95 | $14.34 | 2026-02-23 | historical entry |
| gemini31ct-stacked-v1 | 1.0.0 | gemini-cli | gemini-3.1-pro-preview-customtools | unknown | 2 | 0.624 | 191K | 15m59s | 80 | $0.41 | 2026-02-23 | historical entry |
| gpt52-codex-stacked-v1 | 1.0.0 | codex | gpt-5.2 | unknown | 2 | 0.701 | 5.1M | 18m21s | 83 | $9.77 | 2026-02-23 | historical entry |
| gpt52-codex-stacked-v2 | 1.0.0 | codex | gpt-5.2 | high | 2 | 0.596 | 12.1M | 31m28s | 147 | $22.53 | 2026-02-23 | effort backfilled from Harbor config |
| gpt52codex-codex-stacked-v1 | 1.0.0 | codex | gpt-5.2-codex | unknown | 2 | 0.525 | 6.7M | 18m38s | 96 | $12.67 | 2026-02-23 | historical entry |
| opus46-stacked-v1 | 1.0.0 | claude-code | claude-opus-4-6 | unknown | 2 | 0.680 | 16.6M | 33m05s | 93 | $15.05 | 2026-02-23 | historical entry |
| sonnet46-opencode-v1 | 1.0.0 | opencode | claude-sonnet-4-6 | unknown | 2 | 0.000 | -| 7s | -| -| 2026-02-23 | historical entry |
| sonnet46-stacked-v1 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.729 | 26.3M | 39m34s | 172 | $11.14 | 2026-02-23 | historical entry |
| sonnet46-stacked-v2 | 1.0.0 | claude-code | claude-sonnet-4-6 | unknown | 2 | 0.746 | 4.8M | 27m35s | 34 | $6.79 | 2026-02-23 | historical entry |
