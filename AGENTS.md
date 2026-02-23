# attractorbench

Benchmark for measuring coding agent compliance with the Attractor NLSpec suite.

## Project Structure

- `specs/`: NLSpec source files from strongdm/attractor (source of truth)
- `src/attractorbench/`: Python package (CLI, tier definitions, adapter, scoring)
- `tasks/`: Generated Harbor-compatible task directories (4 tiers: 0-3)
- `registry.json`: Harbor dataset registry entry

## Tiers

- **Tier 0**: Smoke Test: 5-min plumbing check (build, mock server, conformance CLI, scoring)
- **Tier 1**: Unified LLM SDK: Multi-provider LLM client (30 min, 10 conformance tests)
- **Tier 2**: Coding Agent Loop: Programmable agent loop library (60 min, 6 tests)
- **Tier 3**: Attractor Pipeline: DOT-based pipeline runner (60 min, 11 tests)

## Copywriting Style

- Ban all emdashes and contrastive negation -- it's not welcome, it's slop (SWIDT?)

## Conventions

- Python 3.11+, managed with [uv](https://docs.astral.sh/uv/); all commands via `uv run`
- `uv sync` to install deps, `uv add` / `uv add --dev` for new packages
- CLI via Typer
- Data models via Pydantic
- Harbor task format v1.0: task.toml, instruction.md, environment/Dockerfile, tests/test.sh
- Conformance tests are language-agnostic (exercise implementations via CLI contract)
- test.sh always exits 0; pass/fail communicated via /logs/verifier/reward.json
- Composite score: 5% build + 5% self-test + 30% T1 + 30% T2 + 30% T3
- LiteLLM proxy sidecar in every task (docker-compose.yaml) for automatic token/cost tracking

## Commands

All commands are run through `uv run`:

- `uv run attractorbench generate`: Generate Harbor task directories from specs
- `uv run attractorbench score`: Score a completed Harbor job
- `uv run attractorbench compare`: Compare results across runs
- `uv run attractorbench leaderboard`: Rank agent+model combinations across runs
- `uv run attractorbench run-log`: Per-job benchmark run history
- `uv run attractorbench checklist`: List DoD checklists
- `uv run pytest tests/ -v`: Run unit tests

## Running

```bash
uv sync  # install dependencies
uv run attractorbench generate --output-dir tasks
harbor run --dataset ./tasks --agent claude-code --model anthropic/claude-opus-4-6 --env docker
uv run attractorbench score jobs/<job-name>
```

## After Each Run

See [docs/runbook/leaderboard.md](docs/runbook/leaderboard.md) for the full curation process.
Short version: `make results` generates ad hoc tables to `results/` (gitignored), then you manually update `RUN_LOG.md` and `LEADERBOARD.md`.
