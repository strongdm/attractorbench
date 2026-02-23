# Claude Code Runbook

## Overview

Claude Code is Anthropic's CLI coding agent. It is the most reliable agent tested so far, with the highest composite score.

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `ANTHROPIC_BASE_URL` | Auto | Set by LiteLLM sidecar in docker-compose |

## LiteLLM Status: WORKING

Claude Code automatically respects `ANTHROPIC_BASE_URL`. All API traffic routes through the LiteLLM proxy, giving accurate token counts and cost tracking.

## Makefile Targets

```bash
make run-sonnet V=1    # anthropic/claude-sonnet-4-6
make run-opus V=1      # anthropic/claude-opus-4-6
```

## Results

| Model | Best Score | Tokens | Cost | Notes |
|-------|-----------|--------|------|-------|
| claude-sonnet-4-6 | 0.746 | 3.2M | $10.26 | Most reliable overall |
| claude-opus-4-6 | 0.685 | 3.2M | $49.72 | Higher cost, comparable score |

## Tips

- Sonnet 4.6 is faster and cheaper than Opus with comparable or better scores on this benchmark.
- Claude Code produces ATIF trajectories, enabling full cache-aware cost breakdowns.
- No special patches or workarounds needed — works out of the box with Harbor.
