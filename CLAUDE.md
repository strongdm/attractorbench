# attractorbench

Benchmark for measuring coding agent compliance with the Attractor NLSpec suite.

## Project Structure

- `specs/` — NLSpec source files from strongdm/attractor (source of truth)
- `src/attractorbench/` — Python package (CLI, tier definitions, adapter, scoring)
- `tasks/` — Generated Harbor-compatible task directories (3 tiers)
- `registry.json` — Harbor dataset registry entry

## Conventions

- Python 3.11+, managed with uv
- CLI via Typer
- Data models via Pydantic
- Harbor task format v1.0: task.toml, instruction.md, environment/Dockerfile, tests/test.sh
- Conformance tests are language-agnostic (exercise implementations via CLI contract)
- test.sh always exits 0; pass/fail communicated via /logs/verifier/reward.json

## Commands

- `attractorbench generate` — Generate Harbor task directories from specs
- `attractorbench score` — Score a completed Harbor job
- `attractorbench compare` — Compare results across runs
- `attractorbench checklist` — List DoD checklists
