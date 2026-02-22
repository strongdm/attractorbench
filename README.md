# AttractorBench

Benchmark for measuring how well coding agents implement systems from natural language specifications.

Most coding benchmarks test whether an agent can fix a bug or write a function. AttractorBench tests whether an agent can read a 2,000-line system specification and build a conformant implementation from scratch. The specs come from [strongdm/attractor](https://github.com/strongdm/attractor) — a real production project, not synthetic puzzles.

## What It Measures

**Spec-following ability.** Given a detailed NLSpec (natural language specification), can the agent produce a working system that satisfies the Definition of Done checklist?

Scoring is granular, not pass/fail. Each tier has multiple conformance tests grouped by DoD section, so you can see exactly where an agent excels or breaks down: "it nailed the provider adapters but botched streaming and completely missed structured output."

Key properties:
- **Language-agnostic.** Agents choose their own implementation language. The only contract is `make build`, `make test`, and `./bin/conformance <subcommand>`.
- **Deterministic verification.** A mock LLM server returns canned responses — no real API calls, no flakiness.
- **Weighted composite score.** 10% build success + 20% self-test pass rate + 70% conformance tests.
- **Cost-aware.** Track tokens and dollars per unit of compliance, not just raw scores.

## Tiers

| Tier | Name | Spec Lines | Conformance Tests | Agent Timeout | Difficulty |
|------|------|-----------|-------------------|---------------|------------|
| 0 | Smoke Test | ~30 | 4 | 5 min | Easy |
| 1 | Unified LLM SDK | ~2,150 | 10 | 30 min | Hard |
| 2 | Coding Agent Loop | ~1,450 | 6 | 60 min | Hard |
| 3 | Attractor Pipeline | ~2,080 | 11 | 60 min | Hard |

**Tier 0** validates plumbing — your Harbor integration, the mock server, and the scoring pipeline all work before you spend 30 minutes on a real run.

**Tier 1** is the flagship benchmark. It asks the agent to implement a multi-provider LLM client library (OpenAI, Anthropic, Gemini) with streaming, tool calling, structured output, and error handling. Complex enough to differentiate agents, fast enough to iterate on.

**Tiers 2 and 3** build conceptually on Tier 1 (a coding agent loop, then a DOT-based pipeline runner) and test progressively deeper architectural thinking.

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

## Comparing Agents

This is where AttractorBench gets interesting. Run the same tier across multiple agents, then compare.

### Agent/Model Mapping

| Model | Harbor Agent | Notes |
|-------|-------------|-------|
| Claude Opus 4.6 | `claude-code` | ATIF trajectory support. Strong long-context spec reading. |
| GPT-5.3 Codex | `codex` | OpenAI's agentic coding agent. |
| GPT-5.2 | `opencode` | Community agent wrapper for OpenAI models. |
| Gemini 3.1 | `gemini-cli` | Google's native CLI. Long context window advantages. |
| Any model | `openhands` | Model-agnostic agent framework — test different models through the same agent architecture. |
| Any model | `aider` | Git-oriented agent — interesting contrast in approach. |

### Head-to-Head (Tier 1)

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

# Compare
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
```

## Understanding Your Scores

### Composite Score

```
composite = 0.10 * build_success + 0.20 * self_test_pass_rate + 0.70 * conformance_pass_rate
```

The composite score ranges from 0.0 to 1.0. The weighting reflects what matters: conformance with the spec is 70% of the score, the agent's own test suite is 20%, and simply building is 10%.

### Score Interpretation (Tier 1)

| Composite | Interpretation |
|-----------|---------------|
| 0.00 | Agent couldn't build anything, or binary doesn't exist |
| 0.10 | Built successfully but failed all conformance tests |
| 0.30 | Got `client-from-env` and maybe `list-models` working |
| 0.50 | Core completions work, some streaming or tool calling |
| 0.70 | Most conformance tests pass, possibly missing edge cases |
| 0.90+ | Near-complete spec compliance — impressive |

**A score of 0.3-0.4 on Tier 1 is respectable.** Implementing a multi-provider LLM SDK from a 2,000-line spec in 30 minutes is genuinely hard.

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

### Tier 0: Smoke Test (4 conformance tests)
Minimal plumbing validation. Tests: build, client-from-env, list-models, complete.

### Tier 1: Unified LLM SDK (10 conformance tests across 5 sections)
- **Core Infrastructure** — Client construction, model listing, binary existence
- **Generation** — Blocking completions, streaming, structured output
- **Tool Calling** — Tool definitions and execution
- **Provider Adapters** — Anthropic adapter (cross-provider parity)
- **Message & Content Model** — Multimodal message handling
- **Error Handling** — Graceful error surfacing

### Tier 2: Coding Agent Loop (6 conformance tests across 5 sections)
- **Core Loop** — Session creation, agentic processing
- **Tool Execution** — Tool dispatch and routing
- **Event System** — Typed event emission
- **Steering** — Mid-session instruction injection

### Tier 3: Attractor Pipeline (11 conformance tests across 6 sections)
- **DOT Parsing** — Simple, attributed, and conditional graphs
- **Validation** — Missing start nodes, orphan detection, valid graph acceptance
- **Execution Engine** — Linear, conditional, and goal-gated pipelines
- **Node Handlers** — Handler type registry

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

# Compare multiple jobs
uv run attractorbench compare jobs/run-a jobs/run-b jobs/run-c

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
