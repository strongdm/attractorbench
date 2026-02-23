# Gemini Run Instructions — 2026-02-22

## Current State

The stacked full-stack benchmark is working end-to-end. Infrastructure is solid.
Agent quality is the remaining variable.

### What's been done

1. **Stacked task generation** — Tiers 1-3 merged into single `full-stack/` Harbor task.
   - `uv run attractorbench generate --output-dir tasks` produces `tier0-smoke-test/` + `full-stack/`
   - `--individual` flag for backward-compat per-tier directories
   - Instruction size: ~28KB (fits in single base64 chunk)

2. **ARG_MAX fix in gemini_cli.py** — Patched Harbor's installed agent adapter at:
   ```
   ~/.local/share/uv/tools/harbor/lib/python3.12/site-packages/harbor/agents/installed/gemini_cli.py
   ```
   - Chunked base64 file writing (`_chunk_write_commands` method)
   - Stdin pipe invocation: `cat /tmp/.gemini_prompt.md | gemini --yolo --model=... --prompt ''`
   - This is a LOCAL PATCH — will be lost on Harbor reinstall/upgrade

3. **Per-tier scoring** — `score.py` in the task computes:
   ```
   composite = 0.05 * build + 0.05 * self_test + 0.30 * tier1 + 0.30 * tier2 + 0.30 * tier3
   ```
   `reward_details.json` includes `tier{1,2,3}_conformance_*` breakdowns.

4. **Leaderboard** — `attractorbench leaderboard` shows T1/T2/T3 columns.

### Run Results

| Job | Model | Composite | Notes |
|-----|-------|-----------|-------|
| gemini31-stacked-v2 | gemini-3.1-pro-preview | 0.00 | ARG_MAX failure (old patch, 301KB instruction) |
| gemini25pro-stacked-v1 | gemini-2.5-pro | 0.00 | Build failed |
| gemini25pro-stacked-v2 | gemini-2.5-pro | 0.05 | Build OK, agent stripped shebang from bin/conformance |

### gemini25pro-stacked-v2 Failure Analysis

The agent ran 70 steps, 12 minutes, 7.18M tokens — infrastructure worked perfectly.
Score was 0.05 (only build credit) because:

1. **Shebang stripped** — Step 31 replaced `#!/usr/bin/env python3` with `import click`,
   step 32 tried to re-add it but the `replace` tool couldn't find the old string.
   Result: `bin/conformance` → `Exec format error`, zeroing all conformance (90% of score).

2. **Port conflict** — Mock server port 9999 from agent's testing collided with verifier's
   conformance tests. 2/7 self-tests failed.

3. **Tool noise** — ~30 `write_todos` errors (only one in_progress allowed), ~20 `pgrep not found`
   errors. Consumed context window budget without progress.

4. **Incomplete implementation** — Even with shebang fixed, many conformance subcommands
   were skeleton stubs that would have failed.

## Next Steps

### Regenerate tasks (ensures latest stacked verifier + instructions)

```bash
uv run attractorbench generate --output-dir tasks
```

### Re-run gemini-3.1-pro-preview (was using old patch)

```bash
harbor run \
  --path ./tasks \
  --agent gemini-cli \
  --model google/gemini-3.1-pro-preview \
  --env docker \
  --job-name gemini31-stacked-v3
```

### Re-run gemini-2.5-pro (for comparison)

```bash
harbor run \
  --path ./tasks \
  --agent gemini-cli \
  --model google/gemini-2.5-pro \
  --env docker \
  --job-name gemini25pro-stacked-v3
```

### Score and compare

```bash
uv run attractorbench score jobs/gemini31-stacked-v3
uv run attractorbench score jobs/gemini25pro-stacked-v3
uv run attractorbench leaderboard jobs/
```

## Things to Watch For

- **Verify the gemini_cli.py patch is still in place** before running:
  ```bash
  grep "chunk_write_commands" ~/.local/share/uv/tools/harbor/lib/python3.12/site-packages/harbor/agents/installed/gemini_cli.py
  ```
  If missing, the patch was overwritten by a Harbor update. Re-apply from this repo's git history.

- **Stage gating (full-stack)** — Tier 3 conformance is skipped unless Tier 2 passes the core `process_input` test.

- **Instruction size** — Current instruction.md is 28KB. If it grows past ~100KB,
  the chunked approach still works but verify with `wc -c tasks/full-stack/instruction.md`.

- **Agent timeout** — 4 hours (14400s). The gemini25pro v2 run only took 12 minutes.
  Consider whether this is too generous.

## Gemini CLI Reference

- Package: `@google/gemini-cli` (npm, installed via nvm + Node 22)
- Non-interactive mode: `gemini -p "prompt"` or `cat file | gemini -p ""`
- Stdin: `-p` / `--prompt` docs say "Appended to input on stdin (if any)"
- Auto-approve tools: `--yolo` / `-y`
- No `--prompt-file` flag exists — must use stdin pipe for large prompts
