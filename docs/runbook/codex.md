# Codex Runbook

## Overview

Codex is OpenAI's coding agent, accessed via Harbor's `codex` adapter.

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_BASE_URL` | Auto | Set by LiteLLM sidecar in docker-compose |

## LiteLLM Status: WORKING

Codex respects `OPENAI_BASE_URL`. All API traffic routes through the LiteLLM proxy, giving accurate token counts and cost tracking.

## Makefile Targets

```bash
make run-gpt52 V=1    # openai/gpt-5.2
```

## Results

| Model | Best Score | Tokens | Cost | Notes |
|-------|-----------|--------|------|-------|
| gpt-5.2 | 0.701 | 1.2M | $16.13 | Default reasoning effort |
| gpt-5.2 (effort=high) | 0.622 | 1.5M | $19.76 | Higher effort, lower score |
| gpt-5.2-codex | 0.538 | 970K | $12.66 | Codex-specific model |

## Tips

- Default reasoning effort outperforms `effort=high` on this benchmark.
- `gpt-5.2` (standard) outperforms `gpt-5.2-codex` on this benchmark.
- Cost is moderate; token counts are lower than Claude but per-token pricing is higher.
