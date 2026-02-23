# OpenCode Runbook

## Overview

OpenCode is a multi-model wrapper agent that can target various LLM providers. It's useful for running models that don't have a dedicated Harbor agent.

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | For Google models | OpenCode's key name for Google AI |
| `OPENAI_API_KEY` | For OpenAI models | Standard OpenAI key |
| `ANTHROPIC_API_KEY` | For Anthropic models | Standard Anthropic key |

## LiteLLM Status: NOT ROUTED

OpenCode calls provider APIs directly and does not use the LiteLLM proxy base URL env vars. However, it has its own native token tracking that reports accurate numbers via Harbor's `result.json`.

Token/cost data comes from OpenCode's own reporting rather than the LiteLLM proxy logs.

## Makefile Targets

```bash
make run-gemini31ct-opencode V=1    # google/gemini-3.1-pro-preview-customtools
```

## Results

| Model | Best Score | Tokens | Notes |
|-------|-----------|--------|-------|
| gemini-3.1-pro-preview-customtools | 0.640 | 6.9M | Best opencode result |

## Known Issues

- **Missing API keys**: If the correct env var isn't set, OpenCode runs complete in ~7 seconds with 0.000 score and no tokens. This looks like a successful but empty run. Double-check that the appropriate API key is exported.
- **Key naming**: Google models need `GOOGLE_GENERATIVE_AI_API_KEY` (the `GEMINI_API_KEY` var is ignored).

## Tips

- Useful for A/B testing the same model across different agent frameworks (e.g., gemini-3.1-pro-preview-customtools via opencode vs gemini-cli).
- Native token tracking means LiteLLM proxy bypass doesn't lose cost data.
- If a run completes suspiciously fast (~7s) with score 0.000, check your API keys first.
