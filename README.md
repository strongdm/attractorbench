# AttractorBench

Benchmark for measuring how well coding agents implement systems from natural language specifications.

Most coding benchmarks test whether an agent can fix a bug or write a function. AttractorBench tests whether an agent can read a 2,000-line system specification and build a conformant implementation from scratch. The specs come from [strongdm/attractor](https://github.com/strongdm/attractor) — a real production project, not synthetic puzzles.

## What It Measures

**Spec-following ability.** Given a detailed NLSpec (natural language specification), can the agent produce a working system that satisfies the Definition of Done checklist?

Scoring is granular, not pass/fail. Each tier has multiple conformance tests grouped by DoD section, so you can see exactly where an agent excels or breaks down: "it nailed the provider adapters but botched streaming and completely missed structured output."

Key properties:
- **Language-agnostic.** Agents choose their own implementation language. The only contract is `make build`, `make test`, and `./bin/conformance <subcommand>`.
- **Deterministic verification.** A mock LLM server returns canned responses — no real API calls, no flakiness.
- **Weighted composite score.** 5% build + 5% self-test + 30% T1 + 30% T2 + 30% T3 conformance.
- **Cost-aware.** Track tokens and dollars per unit of compliance, not just raw scores.

## Tiers

| Tier | Name | Spec Lines | Conformance Tests | DoD Items | Coverage | Agent Timeout | Difficulty |
|------|------|-----------|-------------------|-----------|----------|---------------|------------|
| 0 | Smoke Test | ~30 | 6 | 6 | 100% | 5 min | Easy |
| 1 | Unified LLM SDK | ~2,150 | 28 | 78 | 36% | 2 hours | Hard |
| 2 | Coding Agent Loop | ~1,450 | 20 | 71 | 28% | 2 hours | Hard |
| 3 | Attractor Pipeline | ~2,080 | 28 | 89 | 31% | 2 hours | Hard |

**Tier 0** validates plumbing — your Harbor integration, the mock server, and the scoring pipeline all work before you spend 30 minutes on a real run.

**Tier 1** is the flagship benchmark. It asks the agent to implement a multi-provider LLM client library (OpenAI, Anthropic, Gemini) with streaming, tool calling, structured output, and error handling. Complex enough to differentiate agents, fast enough to iterate on.

**Tiers 2 and 3** build conceptually on Tier 1 (a coding agent loop, then a DOT-based pipeline runner) and test progressively deeper architectural thinking.

## Leaderboard

See [LEADERBOARD.md](LEADERBOARD.md) for current rankings and [RUN_LOG.md](RUN_LOG.md) for run history.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — manages all Python dependencies; no manual `pip install` needed
- [Harbor](https://github.com/harbor-ai/harbor) installed and configured
- Docker (or a Harbor-supported cloud environment)

### 1. Clone and install

```bash
git clone https://github.com/strongdm/attractorbench.git
cd attractorbench
uv sync   # installs all dependencies into a local .venv
```

### 2. Generate task directories

The conformance tests, mock server, and scoring harness are generated locally from `src/attractorbench/adapter.py` — they are not checked into the repo to avoid eval contamination. You must run this step before using Harbor.

```bash
uv run attractorbench generate --output-dir tasks
```

### 3. Run with Harbor

```bash
harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --env docker \
  --job-name sonnet46-full
```

### 4. Score and view results

```bash
uv run attractorbench score jobs/sonnet46-full
uv run attractorbench leaderboard jobs/sonnet46-full
```

## Running Evals

### Overview

Each eval run follows four steps: **generate** tasks, **run** with Harbor, **score** results, **view** leaderboard. The leaderboard automatically extracts tokens, wall time, tool calls, and cost from Harbor's output files — no manual metadata needed.

### Agent/Model Mapping

| Model | Harbor Agent | Notes |
|-------|-------------|-------|
| Claude Opus 4.6 | `claude-code` | ATIF trajectory support. Strong long-context spec reading. |
| Claude Sonnet 4.6 | `claude-code` | Faster, cheaper. Good baseline. |
| GPT-5.3 Codex | `codex` | OpenAI's agentic coding agent. |
| GPT-5.2 | `opencode` | Community agent wrapper for OpenAI models. |
| Gemini 3.1 | `gemini-cli` | Google's native CLI. Long context window advantages. |
| Any model | `openhands` | Model-agnostic agent framework. |
| Any model | `aider` | Git-oriented agent — interesting contrast in approach. |

### Running a Single Agent

```bash
# 1. Generate tasks (once per benchmark version)
uv run attractorbench generate --output-dir tasks

# 2. Run the full-stack eval
harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env docker \
  --job-name opus46-full

# 3. Score + leaderboard
uv run attractorbench score jobs/opus46-full
uv run attractorbench leaderboard jobs/opus46-full
```

### Running Multiple Agents

To compare agents head-to-head, run each against the same tasks and then combine on the leaderboard.

```bash
# Generate once
uv run attractorbench generate --output-dir tasks

# Run each agent (these can run in parallel on separate machines)
harbor run --dataset ./tasks --agent claude-code \
  --model anthropic/claude-opus-4-6 --env docker --job-name opus46-full

harbor run --dataset ./tasks --agent claude-code \
  --model anthropic/claude-sonnet-4-6 --env docker --job-name sonnet46-full

harbor run --dataset ./tasks --agent codex \
  --model openai/gpt-5.3 --env docker --job-name gpt53-full

harbor run --dataset ./tasks --agent gemini-cli \
  --model google/gemini-3.1 --env docker --job-name gemini31-full

# Compare all runs on a single leaderboard
uv run attractorbench leaderboard jobs/opus46-full jobs/sonnet46-full \
  jobs/gpt53-full jobs/gemini31-full

# Or just glob all jobs
uv run attractorbench leaderboard jobs/*

# Sort by cost efficiency
uv run attractorbench leaderboard jobs/* --sort cost

# Per-task detail
uv run attractorbench compare jobs/opus46-full jobs/sonnet46-full
```

### Running with Daytona (Cloud)

For parallel execution across tiers, use a cloud environment:

```bash
harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env daytona \
  --n-concurrent 4 \
  --job-name opus46-full
```

### Efficiency Metrics

The leaderboard automatically extracts efficiency metrics from Harbor's native output:

- **Tokens** — from `result.json` per trial (`agent_result.n_input_tokens` + `n_output_tokens`)
- **Time** — wall clock seconds from the agent execution phase
- **Tool Calls** — counted from `agent/trajectory.json` steps (ATIF format)
- **Cost** — computed from token counts using litellm pricing tables, including cache token discounts

No extra configuration needed. If an agent produces ATIF trajectories (like `claude-code`), you get full cache-aware cost breakdowns. Otherwise, cost is estimated from result.json token counts.

Leaderboard columns: Agent, Model, Label, Tasks, Score, Tokens, Time, Tool Calls, Cost, Tok/Pt, $/Pt.

## Understanding Your Scores

### Composite Score

```
composite = 0.05 * build + 0.05 * self_test + 0.30 * T1 + 0.30 * T2 + 0.30 * T3
```

The composite score ranges from 0.0 to 1.0. The weighting heavily favors conformance (90% across three tiers) — the spec-following tests we control. Self-test credit (5%) requires a real test runner (pytest, go test, jest, etc.) and penalizes suites with fewer than 5 tests. A no-op Makefile scores at most 10%.

### Score Interpretation (Tier 1)

| Composite | Interpretation |
|-----------|---------------|
| 0.00 | Agent couldn't build anything, or binary doesn't exist |
| 0.10 | Built successfully but failed all conformance tests |
| 0.25 | Got `client-from-env` and maybe `list-models` working |
| 0.40 | Core completions work, basic schema validation passes |
| 0.55 | Streaming, tool calling, and provider routing work |
| 0.70 | Most conformance tests pass, mock server actually called |
| 0.85+ | Near-complete spec compliance — impressive |

**A score of 0.3-0.4 on Tier 1 is respectable.** Implementing a multi-provider LLM SDK from a 2,000-line spec in 30 minutes is genuinely hard.

### Coverage Honesty

Conformance tests sample approximately 30-35% of DoD items across tiers. The following spec sections remain untestable via CLI conformance and are not covered:

- **Tier 1:** Reasoning tokens, prompt caching, parity matrices (internal implementation details)
- **Tier 2:** Tool output truncation, reasoning effort tuning, subagent orchestration (require runtime inspection)
- **Tier 3:** Human-in-the-loop gates, model stylesheets, node transforms (require interactive or visual verification)

Scores reflect tested behavior only. An agent scoring 0.85 has demonstrated strong compliance on the testable surface, but may still have gaps in untested areas.

### Per-Section DoD Scores

The `reward.json` includes per-section scores (`dod_core_infra`, `dod_generation`, `dod_tool_calling`, etc.) that reveal where an agent excels or struggles. Use these for deeper analysis:

```bash
# View the raw reward.json
cat jobs/<job-name>/trials/*/verifier/reward.json | python3 -m json.tool

# Or use the checklist command to see what each section covers
uv run attractorbench checklist --tier 1
```

### Cost Efficiency

The leaderboard computes two derived efficiency metrics:

- **Tok/Pt** (tokens per point) — Total tokens / composite score. Lower is more efficient.
- **$/Pt** (cost per point) — Total cost USD / composite score. The practical metric.

"Agent X scores 0.6 at $2.40/run; Agent Y scores 0.7 at $18/run" is a more useful comparison than raw scores alone.

## The Specs

Each tier's spec is a complete NLSpec document from the Attractor project:

### Tier 0: Smoke Test (6 conformance tests)
Minimal plumbing validation. Tests: build, client-from-env, list-models, complete, missing-key error, schema check.

### Tier 1: Unified LLM SDK (28 conformance tests across 6 sections)
- **Core Infrastructure** — Client construction, model listing, provider routing, missing-key errors
- **Generation** — Blocking completions, streaming (delta+terminal), structured output, usage fields, response IDs
- **Tool Calling** — Tool definitions, name matching, argument validation
- **Provider Adapters** — OpenAI, Anthropic, and Gemini routing; cross-provider tool calls and streaming
- **Message & Content Model** — Text-only, multimodal, and tool-result-roundtrip messages
- **Error Handling** — Invalid requests, rate limits, auth errors

### Tier 2: Coding Agent Loop (20 conformance tests across 7 sections)
- **Core Loop** — Session creation with ID fields, agentic processing with LLM calls, natural completion
- **Tool Execution** — Tool dispatch with result fields, unknown tools, malformed args, shell and file tools
- **Event System** — Typed events, lifecycle markers, minimum count
- **Steering** — Mid-session injection with acknowledgment
- **System Prompts** — System message presence in mock requests
- **Error Handling** — Graceful connection failure
- **Execution Environment** — Shell commands and file operations

### Tier 3: Attractor Pipeline (28 conformance tests across 8 sections)
- **DOT Parsing** — Simple, attributed, conditional, chained, commented, subgraph, and default-inherited graphs
- **Validation** — Missing start/exit nodes, bad edge refs, orphan detection, missing prompts
- **Execution Engine** — Linear, conditional, and goal-gated pipelines; status fields, terminal stopping, branch selection
- **Goal Gate** — Goal gate enforcement and failure handling
- **Node Handlers** — Handler type registry with required types
- **Retry Logic** — Max retries enforcement
- **State/Context** — Execution context and trace
- **Condition Expressions** — Parsed condition attributes

## Harbor Registry

Once published, users can reference attractorbench directly from Harbor without cloning:

```bash
harbor run --dataset attractorbench@1.0 --agent claude-code --model anthropic/claude-opus-4-6
```

To use a local checkout instead:

```bash
harbor run --dataset ./tasks --agent claude-code --model anthropic/claude-opus-4-6
```

## Reproducibility and Eval Contamination

The mock LLM server returns deterministic canned responses. Two runs of the same agent should produce near-identical conformance scores — any variance comes from agent non-determinism (temperature, tool-use ordering).

**On contamination:** The NLSpec source files (`specs/`) are intentionally public — the benchmark measures whether an agent can follow a real spec, and having seen the spec in training is analogous to a developer reading the design doc before starting. The conformance tests, mock server, and scoring harness are generated locally (not checked into the repo) so they stay out of training data. For leaderboard evaluations, the generator in `adapter.py` makes it straightforward to produce fresh conformance variants with different mock responses or test subsets.

For published results, we recommend:

- **n_attempts: 3** with mean and standard deviation reporting
- Pin the agent version (e.g., `claude-code@1.0.20`)
- Record the Harbor version and environment type
- Note the model's training data cutoff relative to the benchmark version
- Export ATIF trajectories for full reproducibility: `harbor traces export <job>`

## CLI Reference

```bash
# Generate Harbor task directories
uv run attractorbench generate --output-dir tasks

# Score a completed job
uv run attractorbench score jobs/<job-name>

# Compare multiple jobs (per-task detail)
uv run attractorbench compare jobs/run-a jobs/run-b jobs/run-c

# Leaderboard — rank agent+model combos with efficiency metrics
uv run attractorbench leaderboard jobs/run-a jobs/run-b jobs/run-c
uv run attractorbench leaderboard jobs/* --sort cost      # sort by cost (ascending)
uv run attractorbench leaderboard jobs/* --sort tokens    # sort by token usage
uv run attractorbench leaderboard jobs/* --sort time      # sort by wall time
uv run attractorbench leaderboard jobs/* --sort efficiency # sort by tokens/point
uv run attractorbench leaderboard jobs/* --markdown       # markdown table output
uv run attractorbench leaderboard jobs/* --json           # JSON output

# View DoD checklists
uv run attractorbench checklist           # all tiers
uv run attractorbench checklist --tier 1  # just Tier 1
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. All commands are run via `uv run` which automatically uses the project's virtual environment.

```bash
# Install dependencies (creates .venv/ automatically)
uv sync

# Run tests
uv run pytest tests/ -v

# Add a dependency
uv add <package>         # runtime
uv add --dev <package>   # dev only

# Generate and inspect tasks
uv run attractorbench generate --output-dir tasks
ls tasks/full-stack/
```

## License

See [LICENSE](LICENSE).
