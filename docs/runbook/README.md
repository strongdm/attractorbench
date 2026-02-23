# Agent Runbooks

Quick-reference index for running AttractorBench with each supported Harbor agent.

## Agent Summary

| Agent | Model(s) | LiteLLM Status | Key Env Var | Best Score | Runbook |
|-------|----------|----------------|-------------|------------|---------|
| claude-code | claude-sonnet-4-6, claude-opus-4-6 | WORKING | `ANTHROPIC_API_KEY` | 0.746 (Sonnet 4.6) | [claude-code.md](claude-code.md) |
| codex | gpt-5.2 | WORKING | `OPENAI_API_KEY` | 0.701 (GPT-5.2) | [codex.md](codex.md) |
| gemini-cli | gemini-3.1-pro-preview, gemini-2.5-pro | FIXED | `GEMINI_API_KEY` | 0.624 (3.1-pro-preview-ct) | [gemini-cli.md](gemini-cli.md) |
| opencode | any (provider-specific keys) | NOT ROUTED | varies | 0.640 (3.1-pro-preview-ct) | [opencode.md](opencode.md) |

## Common Workflow

Every run follows the same four steps:

```bash
# 1. Generate tasks (idempotent)
make generate

# 2. Run with Harbor (pick a target)
make run-sonnet V=1

# 3. (Automatic) Score + update results
#    The Makefile targets chain: generate -> harbor run -> score -> results
```

Or use individual Makefile targets:

| Target | Agent | Model |
|--------|-------|-------|
| `make run-sonnet V=N` | claude-code | anthropic/claude-sonnet-4-6 |
| `make run-opus V=N` | claude-code | anthropic/claude-opus-4-6 |
| `make run-gpt52 V=N` | codex | openai/gpt-5.2 |
| `make run-gemini31 V=N` | gemini-cli | google/gemini-3.1-pro-preview |
| `make run-gemini31ct V=N` | gemini-cli | google/gemini-3.1-pro-preview-customtools |
| `make run-gemini25pro V=N` | gemini-cli | google/gemini-2.5-pro |
| `make run-gemini31ct-opencode V=N` | opencode | google/gemini-3.1-pro-preview-customtools |

Append `EXTRA_ARGS="--n-concurrent 2"` to pass additional flags to Harbor.

## Required Environment Variables

All agents need their respective API keys exported before running:

```bash
export ANTHROPIC_API_KEY=...   # claude-code
export OPENAI_API_KEY=...      # codex
export GEMINI_API_KEY=...      # gemini-cli
export GOOGLE_GENERATIVE_AI_API_KEY=...  # opencode (Google models)
```

## LiteLLM Proxy

The benchmark uses a LiteLLM sidecar in every Docker task to track tokens and costs. The following base URL env vars are injected automatically via docker-compose:

- `OPENAI_BASE_URL=http://litellm:4000/v1` (codex)
- `ANTHROPIC_BASE_URL=http://litellm:4000/anthropic` (claude-code)
- `GOOGLE_GEMINI_BASE_URL=http://litellm:4000/gemini` (gemini-cli)

Agents that respect these env vars route all API traffic through the proxy. See individual runbooks for agent-specific LiteLLM status.
