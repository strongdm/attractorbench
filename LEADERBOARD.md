# AttractorBench Leaderboard

Results from benchmark runs. Updated as new agents and models are evaluated.

## Summary

| Agent | Model | Tasks | Score | Tokens | Time | Tool Calls | Cost | Tok/Pt | $/Pt |
|-------|-------|------:|------:|-------:|-----:|-----------:|-----:|-------:|-----:|
| claude-code | claude-sonnet-4-6 | 1 | 1.000 | — | 59s | — | — | — | — |
| claude-code | claude-sonnet-4-6 | 3 | 0.577 | 23.9M | 53m51s | 183 | $9.19 | 41.4M | $15.92 |

- **Score** = average composite across tasks (0.0 to 1.0)
- **Tokens** = total prompt + completion tokens across all tasks
- **Cost** = USD computed from token counts using litellm pricing (includes cache discounts)
- **Tok/Pt** and **$/Pt** = tokens and cost divided by composite score (lower is better)

## Per-Tier Breakdown (Sonnet 4.6)

Single attempt per tier, Docker environment, 2026-02-22.

### Tier 0 — Smoke Test

| Metric | Value |
|--------|-------|
| Composite | **1.000** |
| Build | pass |
| Self-Test | 100% |
| Conformance | 6/6 (100%) |
| Time | 59s |

Tier 0 validates plumbing — Harbor integration, mock server, and scoring pipeline all work.

### Tier 1 — Unified LLM SDK

| Metric | Value |
|--------|-------|
| Composite | **0.826** |
| Build | pass |
| Self-Test | 97.6% |
| Conformance | 22/28 (78.6%) |
| Tokens | 6.1M (prompt) + 860 (completion) |
| Cache | 170K creation, 6.1M reads |
| Tool Calls | 48 |
| Time | 16m51s |

Strong performance. Core completions, streaming, tool calling, and provider routing all work. Missed some edge cases in structured output and error handling.

### Tier 2 — Coding Agent Loop

| Metric | Value |
|--------|-------|
| Composite | **0.705** |
| Build | pass |
| Self-Test | 100% |
| Conformance | 12/19 (63.2%) |
| Tokens | 8.5M (prompt) + 1.4K (completion) |
| Cache | 167K creation, 8.5M reads |
| Tool Calls | 71 |
| Time | 20m25s |

Solid agent loop implementation. Core loop, tool execution, and event system work. Gaps in steering, system prompts, and some execution environment tests.

### Tier 3 — Attractor Pipeline

| Metric | Value |
|--------|-------|
| Composite | **0.200** |
| Build | pass |
| Self-Test | 100% |
| Conformance | 0/0 (0%) |
| Tokens | 9.3M (prompt) + 985 (completion) |
| Cache | 186K creation, 9.3M reads |
| Tool Calls | 64 |
| Time | 16m36s |

Built and self-tested successfully but did not wire up the conformance CLI (`./bin/conformance <subcommand>`). The agent wrote internal tests but missed the external CLI contract required for scoring.

## How Metrics Are Collected

The leaderboard reads Harbor's native output files — no extra configuration needed:

1. **Tokens and timing** — extracted from `result.json` per trial
2. **Tool calls and cache breakdown** — extracted from `agent/trajectory.json` (ATIF format)
3. **Cost** — computed from token counts using [litellm](https://github.com/BerryAI/litellm) pricing tables, with proper cache token discounts (cache reads at ~10% of base rate, cache creation at ~125%)

## Reproducing

```bash
# Install
git clone https://github.com/strongdm/attractorbench.git
cd attractorbench && uv sync

# Generate tasks
uv run attractorbench generate --tiers 0,1,2,3 --output-dir tasks

# Run (swap agent/model as needed)
harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --env docker \
  --job-name sonnet46-full

# Score + leaderboard
uv run attractorbench score jobs/sonnet46-full
uv run attractorbench leaderboard jobs/sonnet46-full

# Compare multiple runs
uv run attractorbench leaderboard jobs/sonnet46-full jobs/opus46-full jobs/gpt53-full
```
