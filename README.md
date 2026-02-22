# AttractorBench

Benchmark for measuring how well coding agents implement systems from natural language specifications.

Most coding benchmarks test whether an agent can fix a bug or write a function. AttractorBench tests whether an agent can read a 2,000-line system specification and build a conformant implementation from scratch. The specs come from [strongdm/attractor](https://github.com/strongdm/attractor) — a real production project, not synthetic puzzles.

## What It Measures

**Spec-following ability.** Given a detailed NLSpec (natural language specification), can the agent produce a working system that satisfies the Definition of Done checklist?

Scoring is granular, not pass/fail. Each tier has multiple conformance tests grouped by DoD section, so you can see exactly where an agent excels or breaks down: "it nailed the provider adapters but botched streaming and completely missed structured output."

Key properties:
- **Language-agnostic.** Agents choose their own implementation language. The only contract is `make build`, `make test`, and `./bin/conformance <subcommand>`.
- **Deterministic verification.** A mock LLM server returns canned responses — no real API calls, no flakiness.
- **Weighted composite score.** 10% build success + 10% self-test pass rate + 80% conformance tests.
- **Cost-aware.** Track tokens and dollars per unit of compliance, not just raw scores.

## Tiers

| Tier | Name | Spec Lines | Conformance Tests | DoD Items | Coverage | Agent Timeout | Difficulty |
|------|------|-----------|-------------------|-----------|----------|---------------|------------|
| 0 | Smoke Test | ~30 | 6 | 6 | 100% | 5 min | Easy |
| 1 | Unified LLM SDK | ~2,150 | 28 | 78 | 36% | 30 min | Hard |
| 2 | Coding Agent Loop | ~1,450 | 20 | 71 | 28% | 60 min | Hard |
| 3 | Attractor Pipeline | ~2,080 | 28 | 89 | 31% | 60 min | Hard |

**Tier 0** validates plumbing — your Harbor integration, the mock server, and the scoring pipeline all work before you spend 30 minutes on a real run.

**Tier 1** is the flagship benchmark. It asks the agent to implement a multi-provider LLM client library (OpenAI, Anthropic, Gemini) with streaming, tool calling, structured output, and error handling. Complex enough to differentiate agents, fast enough to iterate on.

**Tiers 2 and 3** build conceptually on Tier 1 (a coding agent loop, then a DOT-based pipeline runner) and test progressively deeper architectural thinking.

## Leaderboard

Results from initial benchmark runs (2026-02-22). Single attempt per tier, Docker environment.

| Agent | Model | Tier | Build | Self-Test | Conformance | Composite |
|-------|-------|------|-------|-----------|-------------|-----------|
| claude-code | claude-sonnet-4-6 | 0 — Smoke Test | pass | 100% | 6/6 (100%) | **1.000** |
| claude-code | claude-sonnet-4-6 | 1 — Unified LLM SDK | pass | 97.6% | 22/28 (78.6%) | **0.826** |
| claude-code | claude-sonnet-4-6 | 2 — Agent Loop | pass | 100% | 12/19 (63.2%) | **0.705** |
| claude-code | claude-sonnet-4-6 | 3 — Attractor Pipeline | pass | 100% | 0/0 (0%) | **0.200** |

Sonnet 4.6 builds reliably across all tiers and writes strong self-tests. Conformance drops with spec complexity — Tier 1 (78.6%) and Tier 2 (63.2%) show solid spec-following, while Tier 3 built and self-tested but didn't wire up the conformance CLI.

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
# Recommended first run: just Tier 0 to validate plumbing
uv run attractorbench generate --tiers 0 --output-dir tasks

# Or generate everything
uv run attractorbench generate --tiers 0,1,2,3 --output-dir tasks
```

### 3. Run with Harbor

```bash
# Smoke test — validates the whole pipeline in ~5 minutes
harbor run \
  --dataset ./tasks/tier0-smoke-test \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env docker

# Tier 1 — the main event (~30 min per agent)
harbor run \
  --dataset ./tasks/tier1-unified-llm \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env docker \
  --job-name opus46-tier1
```

### 4. Score results

```bash
uv run attractorbench score jobs/opus46-tier1
```

## Running an Eval: Step-by-Step

This is the complete procedure for benchmarking one agent+model combination.

### Agent/Model Mapping

Pick your agent harness and model. Each agent has a Harbor adapter that handles prompt formatting, tool routing, and context management.

| Model | Harbor Agent | Notes |
|-------|-------------|-------|
| Claude Opus 4.6 | `claude-code` | ATIF trajectory support. Strong long-context spec reading. |
| GPT-5.3 Codex | `codex` | OpenAI's agentic coding agent. |
| GPT-5.2 | `opencode` | Community agent wrapper for OpenAI models. |
| Gemini 3.1 | `gemini-cli` | Google's native CLI. Long context window advantages. |
| Any model | `openhands` | Model-agnostic agent framework — test different models through the same agent architecture. |
| Any model | `aider` | Git-oriented agent — interesting contrast in approach. |

### Step 1: Generate tasks

Generate once per benchmark version. Regenerate if you update `adapter.py` or the specs.

```bash
# Tier 0 first to validate plumbing
uv run attractorbench generate --tiers 0 --output-dir tasks

# Then generate the tier(s) you want to eval
uv run attractorbench generate --tiers 1 --output-dir tasks

# Or everything at once
uv run attractorbench generate --tiers 0,1,2,3 --output-dir tasks
```

### Step 2: Run the smoke test

Always run Tier 0 first. It validates your Harbor install, Docker environment, and the scoring pipeline in under 5 minutes. If Tier 0 fails, debug that before spending 30-60 minutes on a real tier.

```bash
harbor run \
  --dataset ./tasks/tier0-smoke-test \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env docker

# Verify it scored correctly
uv run attractorbench score jobs/<tier0-job-name>
```

### Step 3: Run the real eval

```bash
# Single tier (recommended starting point)
harbor run \
  --dataset ./tasks/tier1-unified-llm \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env docker \
  --job-name opus46-tier1

# All tiers in parallel
harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env daytona \
  --n-concurrent 4 \
  --job-name opus46-full
```

### Step 4: Score

```bash
uv run attractorbench score jobs/opus46-tier1
```

This reads `reward.json` from the job directory and prints per-task and summary scores.

### Step 5: Efficiency metrics (automatic via LiteLLM sidecar)

Every generated task includes a **LiteLLM proxy sidecar** that automatically intercepts the agent's real LLM API calls during the agent phase, logs token usage and cost, and writes `metadata.json` for the leaderboard.

**How it works:**

1. Harbor starts `docker-compose.yaml` which includes a `litellm` sidecar service alongside the `main` container.
2. The `main` container's `OPENAI_BASE_URL` and `ANTHROPIC_BASE_URL` environment variables point to the LiteLLM proxy (`http://litellm:4000/...`).
3. The proxy forwards all requests to the real provider APIs while logging usage to a shared volume.
4. During the verifier phase, `harvest_litellm.py` reads the proxy log and writes `/logs/verifier/metadata.json`.
5. The leaderboard picks up the metadata automatically.

**API keys:** The LiteLLM sidecar reads API keys from the host environment via docker-compose variable substitution (`${OPENAI_API_KEY:-}`, `${ANTHROPIC_API_KEY:-}`, `${GEMINI_API_KEY:-}`). Make sure your keys are set in the environment where Harbor starts the compose.

**Troubleshooting:** If the litellm sidecar fails to start, check that your API keys are set and that the `ghcr.io/berriai/litellm:main-latest` image can be pulled. The harvest step is non-fatal — if it fails, the leaderboard still works (efficiency columns show `—`).

You can also manually provide or override `metadata.json` if needed:

```bash
cat > jobs/opus46-tier1/metadata.json << 'EOF'
{
  "agent": "claude-code",
  "model": "claude-opus-4-6",
  "total_tokens": 145200,
  "prompt_tokens": 98000,
  "completion_tokens": 47200,
  "cost_usd": 4.23
}
EOF
```

### Step 6: Build the leaderboard

```bash
# Single run
uv run attractorbench leaderboard jobs/opus46-tier1

# Multiple runs — compare agents head-to-head
uv run attractorbench leaderboard jobs/opus46-t1 jobs/gpt53-codex-t1 jobs/gemini31-t1

# Sort by cost efficiency instead of score
uv run attractorbench leaderboard jobs/* --sort cost

# Export as markdown for a report
uv run attractorbench leaderboard jobs/* --markdown

# Export as JSON for programmatic use
uv run attractorbench leaderboard jobs/* --json
```

Leaderboard columns: Agent, Model, Label, Tasks, Score, Tokens, Time, Tool Calls, Cost, Tokens/Point, $/Point.

## Comparing Agents

### Head-to-Head (Tier 1)

Run the same tier across multiple agents, then compare on the leaderboard.

```bash
# Generate once
uv run attractorbench generate --tiers 1 --output-dir tasks

# Run each agent
harbor run --dataset ./tasks/tier1-unified-llm --agent claude-code \
  --model anthropic/claude-opus-4-6 --job-name opus46-t1

harbor run --dataset ./tasks/tier1-unified-llm --agent codex \
  --model openai/gpt-5.3 --job-name gpt53-codex-t1

harbor run --dataset ./tasks/tier1-unified-llm --agent gemini-cli \
  --model google/gemini-3.1 --job-name gemini31-t1

# Score + compare
uv run attractorbench leaderboard jobs/opus46-t1 jobs/gpt53-codex-t1 jobs/gemini31-t1

# Detailed per-task comparison
uv run attractorbench compare jobs/opus46-t1 jobs/gpt53-codex-t1 jobs/gemini31-t1
```

### Full Suite (All Tiers)

```bash
uv run attractorbench generate --tiers 0,1,2,3 --output-dir tasks

harbor run \
  --dataset ./tasks \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env daytona \
  --n-concurrent 4 \
  --job-name opus46-full

uv run attractorbench score jobs/opus46-full
uv run attractorbench leaderboard jobs/opus46-full
```

## Understanding Your Scores

### Composite Score

```
composite = 0.10 * build_success + 0.10 * self_test_pass_rate + 0.80 * conformance_pass_rate
```

The composite score ranges from 0.0 to 1.0. The weighting heavily favors conformance (80%) — the spec-following tests we control. Self-test credit (10%) requires a real test runner (pytest, go test, jest, etc.) and penalizes suites with fewer than 5 tests. A no-op Makefile scores at most 10%.

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

If your Harbor setup captures token counts and costs (via ATIF trajectories), attractorbench can compute derived metrics:

- **tokens_per_compliance** — Total tokens / composite score. Lower is more efficient.
- **cost_per_compliance** — Total cost USD / composite score. The practical metric.
- **compliance_efficiency** — Composite score / (cost * time). Best overall efficiency metric.

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
uv run attractorbench generate --tiers 0,1,2,3 --output-dir tasks

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
uv run attractorbench generate --tiers 0,1 --output-dir tasks
ls tasks/tier0-smoke-test/
ls tasks/tier1-unified-llm/
```

## License

See [LICENSE](LICENSE).
