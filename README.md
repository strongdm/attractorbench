# AttractorBench

Benchmark for measuring how well coding agents implement systems from natural language specifications.

Most coding benchmarks test whether an agent can fix a bug or write a function. AttractorBench tests whether an agent can read a 2,000-line system specification and build a conformant implementation from scratch. The specs come from [strongdm/attractor](https://github.com/strongdm/attractor), a real production project with real production complexity.

> [!IMPORTANT]
> **NOTE (02-23-2026):** We are still tuning AttractorBench and do not regard current scores/totals as **valid for ranking** until we complete additional burn-in runs to characterize run-to-run variability.

## What It Measures

**Spec-following ability.** Given a detailed NLSpec (natural language specification), can the agent produce a working system that satisfies the Definition of Done (DoD) checklist?

Scoring is granular. Each tier has multiple conformance tests grouped by DoD section, so you can see exactly where an agent excels or breaks down: "it nailed the provider adapters but botched streaming and completely missed structured output."

Key properties:
- **Language-agnostic.** Agents choose their own implementation language. The only contract is `make build`, `make test`, and `./bin/conformance <subcommand>`.
- **Deterministic verifier.** A mock LLM server returns canned responses (no real API calls). Agents can still be non-deterministic.
- **Weighted composite score.** Main task: 5% build + 5% self-test + 30% each for T1/T2/T3 conformance. Single-tier: 10% build + 10% self-test + 80% conformance.
- **Cost-aware.** Track tokens and dollars per unit of compliance alongside raw scores.

## Tiers

| Tier | Name | Spec Lines | Conformance Tests | DoD Items | Coverage | Agent Timeout | Difficulty |
|------|------|-----------|-------------------|-----------|----------|---------------|------------|
| 0 | Smoke Test | ~30 | 7 | 6 | 100% | 5 min | Easy |
| 1 | Unified LLM SDK | ~2,150 | 35 | 115 | 30% | 2 hours | Hard |
| 2 | Coding Agent Loop | ~1,450 | 20 | 104 | 19% | 2 hours | Hard |
| 3 | Attractor Pipeline | ~2,080 | 28 | 98 | 29% | 2 hours | Hard |

**Tier 0** validates plumbing: your Harbor integration, the mock server, and the scoring pipeline all work before you spend 30 minutes on a real run.

**Tier 1** is the flagship benchmark. It asks the agent to implement a multi-provider LLM client library (OpenAI, Anthropic, Gemini) with streaming, tool calling, structured output, and error handling. Complex enough to differentiate agents, fast enough to iterate on.

**Tiers 2 and 3** build conceptually on Tier 1 (a coding agent loop, then a DOT-based pipeline runner) and test progressively deeper architectural thinking.

## Leaderboard

See [LEADERBOARD.md](LEADERBOARD.md) for the current curated snapshot and [RUN_LOG.md](RUN_LOG.md) for the complete historical ledger.
Both files are manually curated; see [docs/runbook/leaderboard.md](docs/runbook/leaderboard.md) for the update process.

## Versioning and Comparability

- Breaking benchmark changes are versioned from this point onward.
- Comparability decays across versions; only runs on the same benchmark version are directly comparable.
- Historical run logs are still retained for context and trend tracking.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/): manages all Python dependencies; no manual `pip install` needed
- [Harbor](https://github.com/harbor-ai/harbor) installed and configured
- Docker (or a Harbor-supported cloud environment)

### 1. Clone and install

```bash
git clone https://github.com/strongdm/attractorbench.git
cd attractorbench
uv sync   # installs all dependencies into a local .venv
```

### 2. Generate task directories

The conformance tests, mock server, and scoring harness are generated locally from `src/attractorbench/adapter.py` and are intentionally excluded from the repo to avoid eval contamination. You must run this step before using Harbor.

```bash
uv run attractorbench generate --output-dir tasks
# Optional: add curriculum subtier tasks
uv run attractorbench generate --output-dir tasks --curriculum
```

### 3. Run with Harbor

```bash
harbor run \
  --path ./tasks \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --env docker \
  --job-name sonnet46-full
```

### 4. Score and view results

```bash
uv run attractorbench score jobs/sonnet46-full
uv run attractorbench run-log jobs/sonnet46-full
# Optional ad hoc analysis (does not auto-update LEADERBOARD.md):
uv run attractorbench leaderboard jobs/sonnet46-full
```

## Running Evals

### Overview

Each eval run follows four steps: **generate** tasks, **run** with Harbor, **score** results, **update run log/snapshot docs**.
Use CLI leaderboard output for ad hoc analysis, but maintain `LEADERBOARD.md` and `RUN_LOG.md` as curated repository artifacts.

### Harbor Agents (Typical)

| Harbor Agent | Notes |
|-------------|-------|
| `claude-code` | Anthropic-focused coding agent. Emits ATIF trajectories (better cache/cost breakdown when available). |
| `codex` | OpenAI coding agent. Some configs expose an effort setting (for example OpenAI `reasoning_effort`). |
| `gemini-cli` | Google's CLI agent. |
| `opencode` | Multi-model wrapper agent; exact model support depends on your Harbor setup. |
| `openhands` | Model-agnostic agent framework. |
| `aider` | Git-oriented agent (useful contrast in workflow). |

See [docs/runbook/](docs/runbook/) for per-agent setup guides, environment variables, LiteLLM status, and tips.

### Running Multiple Agents

To compare agents head-to-head, run each against the same tasks and then combine on the leaderboard.

```bash
# Run each agent (these can run in parallel on separate machines)
harbor run --path ./tasks --agent claude-code \
  --model anthropic/claude-opus-4-6 --env docker --job-name opus46-full

harbor run --path ./tasks --agent claude-code \
  --model anthropic/claude-sonnet-4-6 --env docker --job-name sonnet46-full

harbor run --path ./tasks --agent codex \
  --model openai/gpt-5.2 --env docker --job-name gpt52-full

harbor run --path ./tasks --agent gemini-cli \
  --model google/gemini-3.1-pro-preview --env docker --job-name gemini31-full

# Compare all runs ad hoc
uv run attractorbench leaderboard jobs/opus46-full jobs/sonnet46-full \
  jobs/gpt52-full jobs/gemini31-full

# Or just glob all jobs
uv run attractorbench leaderboard jobs/*

# Sort by cost efficiency (ad hoc analysis)
uv run attractorbench leaderboard jobs/* --sort cost
uv run attractorbench leaderboard jobs/* --include-curriculum

# Per-task detail
uv run attractorbench compare jobs/opus46-full jobs/sonnet46-full
```

### Running with Daytona (Cloud)

For parallel execution across tiers, use a cloud environment:

```bash
harbor run \
  --path ./tasks \
  --agent claude-code \
  --model anthropic/claude-opus-4-6 \
  --env daytona \
  --n-concurrent 4 \
  --job-name opus46-full
```

### Efficiency Metrics

Ad hoc CLI leaderboard output can extract efficiency metrics from Harbor's native output:

- **Tokens**: from `result.json` per trial (`agent_result.n_input_tokens` + `n_output_tokens`)
- **Time**: wall clock seconds from the agent execution phase
- **Tool Calls**: counted from `agent/trajectory.json` steps (ATIF format)
- **Cost**: computed from token counts using litellm pricing tables, including cache token discounts

No extra configuration needed. If an agent produces ATIF trajectories (like `claude-code`), you get full cache-aware cost breakdowns. Otherwise, cost is estimated from result.json token counts.

## Understanding Your Scores

### Composite Score

```
# Main task (tiers 1-3 combined)
composite = 0.05 * build + 0.05 * self_test + 0.30 * T1 + 0.30 * T2 + 0.30 * T3

# Single-tier tasks (tier0/tier1/tier2/tier3)
composite = 0.10 * build + 0.10 * self_test + 0.80 * conformance
```

The composite score ranges from 0.0 to 1.0. The weighting heavily favors conformance (90% on the main task; 80% on single-tier), i.e. the spec-following tests we control. Self-test credit (5% main; 10% single-tier) requires a real test runner (pytest, go test, jest, etc.) and penalizes suites with fewer than 5 tests. A no-op Makefile can still earn the build weight, but almost all of the score comes from self-tests + conformance.

### Score Interpretation (Tier 1)

| Composite | Interpretation |
|-----------|---------------|
| 0.00 | Agent couldn't build anything, or binary doesn't exist |
| 0.10 | Built successfully but failed all conformance tests |
| 0.25 | Got `client-from-env` and maybe `list-models` working |
| 0.40 | Core completions work, basic schema validation passes |
| 0.55 | Streaming, tool calling, and provider routing work |
| 0.70 | Most conformance tests pass, mock server actually called |
| 0.85+ | Near-complete spec compliance |

**A score of 0.3-0.4 on Tier 1 is respectable.** Implementing a multi-provider LLM SDK from a 2,000-line spec in 30 minutes is genuinely hard.

### Coverage Honesty

Conformance tests sample about ~30% of DoD items (varies by tier). The following spec sections remain untestable via CLI conformance and are not covered:

- **Tier 1:** Reasoning tokens, prompt caching, parity matrices (internal implementation details)
- **Tier 2:** Tool output truncation, reasoning effort tuning, subagent orchestration (require runtime inspection)
- **Tier 3:** Human-in-the-loop gates, model stylesheets, node transforms (require interactive or visual verification)

Scores reflect tested behavior only. An agent scoring 0.85 has demonstrated strong compliance on the testable surface, but may still have gaps in untested areas.

### Per-Section DoD Scores

Per-section DoD scores are written to `reward_details.json` (next to Harbor's single-key `reward.json`) as `dod_core_infra`, `dod_generation`, `dod_tool_calling`, etc. Use these for deeper analysis:

```bash
# Find and view a reward_details.json
python3 -m json.tool "$(find jobs/<job-name> -name reward_details.json -print | head -n 1)"

# Or use the checklist command to see what each section covers
uv run attractorbench checklist --tier 1
```

### Cost Efficiency

The CLI leaderboard computes two derived efficiency metrics:

- **Tok/Pt** (tokens per point): Total tokens / composite score. Lower is more efficient.
- **$/Pt** (cost per point): Total cost USD / composite score. The practical metric.

"Agent X scores 0.6 at $2.40/run; Agent Y scores 0.7 at $18/run" is a more useful comparison than raw scores alone.

## The Specs

Tier 1-3 specs are vendored from the upstream Attractor project (`strongdm/attractor`) and pinned by commit for reproducibility. See [specs/UPSTREAM.json](specs/UPSTREAM.json) for the current commit.
To refresh to the latest upstream `main`, run:

```bash
make specs-update
```

Updating specs is a benchmark change; bump the benchmark version when you do this.

### Tier 0: Smoke Test (7 conformance tests)
Minimal plumbing validation. Tests: build, binary exists, client-from-env, list-models, complete, missing-key error, schema check.

### Tier 1: Unified LLM SDK (35 conformance tests across 6 sections)
- **Core Infrastructure**: Client construction, model listing, provider routing, missing-key errors
- **Generation**: Blocking completions, streaming (delta+terminal), structured output, usage fields, response IDs
- **Tool Calling**: Tool definitions, name matching, argument validation
- **Provider Adapters**: OpenAI, Anthropic, and Gemini routing; cross-provider tool calls and streaming
- **Message & Content Model**: Text-only, multimodal, and tool-result-roundtrip messages
- **Error Handling**: Invalid requests, rate limits, auth errors

### Tier 2: Coding Agent Loop (20 conformance tests across 7 sections)
- **Core Loop**: Session creation with ID fields, agentic processing with LLM calls, natural completion
- **Tool Execution**: Tool dispatch with result fields, unknown tools, malformed args, shell and file tools
- **Event System**: Typed events, lifecycle markers, minimum count
- **Steering**: Mid-session injection with acknowledgment
- **System Prompts**: System message presence in mock requests
- **Error Handling**: Graceful connection failure
- **Execution Environment**: Shell commands and file operations

### Tier 3: Attractor Pipeline (28 conformance tests across 8 sections)
- **DOT Parsing**: Simple, attributed, conditional, chained, commented, subgraph, and default-inherited graphs
- **Validation**: Missing start/exit nodes, bad edge refs, orphan detection, missing prompts
- **Execution Engine**: Linear, conditional, and goal-gated pipelines; status fields, terminal stopping, branch selection
- **Goal Gate**: Goal gate enforcement and failure handling
- **Node Handlers**: Handler type registry with required types
- **Retry Logic**: Max retries enforcement
- **State/Context**: Execution context and trace
- **Condition Expressions**: Parsed condition attributes

## Harbor Registry

Once published, users can reference attractorbench directly from Harbor without cloning:

```bash
harbor run --dataset attractorbench@<bench_version> --agent claude-code --model anthropic/claude-opus-4-6
```

To use a local checkout instead:

```bash
harbor run --path ./tasks --agent claude-code --model anthropic/claude-opus-4-6
```

## Reproducibility and Eval Contamination

The mock LLM server returns deterministic canned responses. Two runs of the same agent should produce near-identical conformance scores:any variance comes from agent non-determinism (temperature, tool-use ordering).

**On contamination:** The NLSpec source files (`specs/`) are intentionally public:the benchmark measures whether an agent can follow a real spec, and having seen the spec in training is analogous to a developer reading the design doc before starting. The conformance tests, mock server, and scoring harness are generated locally (not checked into the repo) so they stay out of training data. For leaderboard evaluations, the generator in `adapter.py` makes it straightforward to produce fresh conformance variants with different mock responses or test subsets.

For published results, we recommend:

- **n_attempts: 3** with mean and standard deviation reporting
- Pin the agent version (e.g., `claude-code@1.0.20`)
- Record the Harbor version and environment type
- Note the model's training data cutoff relative to the benchmark version
- Export ATIF trajectories for full reproducibility: `harbor traces export --path jobs/<job-name>`

## Run Artifact Policy

- Commit `LEADERBOARD.md` and `RUN_LOG.md` only. See [docs/runbook/leaderboard.md](docs/runbook/leaderboard.md) for the curation process.
- Do not commit raw Harbor run artifacts under `jobs/` (agent transcripts, tool logs, verifier logs, trial outputs, etc.).
- The repository keeps `jobs/.gitkeep` so the directory exists locally, while run contents remain ignored.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. All commands are run via `uv run` which automatically uses the project's virtual environment.

```bash
uv add <package>         # add a runtime dependency
uv add --dev <package>   # add a dev dependency
uv run pytest tests/ -v  # run tests
```

## License

See [LICENSE](LICENSE).
