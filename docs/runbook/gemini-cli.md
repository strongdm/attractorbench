# Gemini CLI Runbook

## Overview

Gemini CLI (`@google/gemini-cli`) is Google's terminal-based coding agent. It requires a local patch to Harbor's adapter for large prompts (ARG_MAX fix) and now routes through LiteLLM for accurate token/cost tracking.

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `GEMINI_API_KEY` | Yes | Google AI API key |
| `GOOGLE_GEMINI_BASE_URL` | Auto | Set by LiteLLM sidecar in docker-compose |

## LiteLLM Status: FIXED

Previously, gemini-cli bypassed the LiteLLM proxy and called Google APIs directly, producing inaccurate token/cost numbers (e.g., 191K tokens vs opencode's 6.9M for the same model). The `@google/genai` SDK respects `GOOGLE_GEMINI_BASE_URL`, which is now set in docker-compose and forwarded by Harbor's gemini_cli adapter.

### What was changed

1. **adapter.py**: Added `GOOGLE_GEMINI_BASE_URL=http://litellm:4000/gemini` to docker-compose service environment.
2. **Harbor gemini_cli.py**: Added `GOOGLE_GEMINI_BASE_URL` to the `auth_vars` list so it's forwarded into the container's exec environment.

## Makefile Targets

```bash
make run-gemini31 V=1      # google/gemini-3.1-pro-preview
make run-gemini31ct V=1    # google/gemini-3.1-pro-preview-customtools
make run-gemini25pro V=1   # google/gemini-2.5-pro
```

## Results

| Model | Best Score | Notes |
|-------|-----------|-------|
| gemini-3.1-pro-preview-customtools | 0.624 | Best Gemini result |
| gemini-3.1-pro-preview | 0.573 | Base model |
| gemini-2.5-pro | 0.05 | Build only, shebang issue |

## Pre-Run Checklist

1. **Verify ARG_MAX patch is in place:**
   ```bash
   grep "chunk_write_commands" ~/.local/share/uv/tools/harbor/lib/python3.12/site-packages/harbor/agents/installed/gemini_cli.py
   ```
   If missing, the patch was overwritten by a Harbor update. The patch chunks base64 file writing and uses stdin pipe invocation for large prompts.

2. **Verify GOOGLE_GEMINI_BASE_URL forwarding:**
   ```bash
   grep "GOOGLE_GEMINI_BASE_URL" ~/.local/share/uv/tools/harbor/lib/python3.12/site-packages/harbor/agents/installed/gemini_cli.py
   ```

3. **Regenerate tasks** to pick up the latest docker-compose env vars:
   ```bash
   make generate
   ```

## Known Issues

- **ARG_MAX**: Harbor's gemini_cli.py needs a local patch for large instructions (>64KB). The patch adds `_chunk_write_commands` and stdin pipe invocation. This is a LOCAL PATCH that will be lost on Harbor reinstall/upgrade.
- **Shebang stripping**: gemini-2.5-pro has been observed stripping `#!/usr/bin/env python3` from `bin/conformance`, causing `Exec format error` and zeroing all conformance scores.
- **Tool noise**: Gemini agents sometimes produce excessive `write_todos` and `pgrep not found` errors that consume context budget.

## Tips

- The `customtools` variant slightly outperforms the base model (0.624 vs 0.573).
- Gemini runs are extremely fast (~12 min) and cheap compared to other agents.
- Non-interactive mode: `gemini -p "prompt"` or `cat file | gemini -p ""`
- Auto-approve tools: `--yolo` / `-y`
