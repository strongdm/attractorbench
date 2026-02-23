# AttractorBench Benchmark Enhancements (Sparse Reward + Iteration)

Status: Draft plan (write-up first, implementation later)  
Requested filename date: 2025-02-23  
Written: 2026-02-23

## Context / Problem Statement

AttractorBench is intentionally hard: it asks an agent to read a long natural-language spec (NLSpec) and produce a spec-compliant system from scratch, verified via a deterministic conformance harness.

The downside of “full system from scratch” is a classic **sparse reward** / **cliff failure** dynamic:

- Many runs fail early due to *plumbing* (missing `Makefile`, missing `./bin/conformance`, wrong executable bit, wrong env parsing), producing low scores that do not reflect deeper spec comprehension.
- Progress is often “invisible” unless the agent discovers and repeatedly runs conformance.
- Large, coupled tasks amplify dependency chains: if Layer 1 is incomplete, Layer 2/3 can’t be meaningfully evaluated, so the score distribution collapses toward 0.
- Agents may stop after the first error spiral because the task text does not explicitly enforce an “implement → run → fix → repeat” loop.

This document proposes changes to (1) densify the feedback signal, (2) push agents toward iterative repair, and (3) improve characterization of *where* models fail, without turning the benchmark into a collection of toy unit tests.

## Goals

1. **Increase iteration rate**: make it obvious how to run conformance during the agent run.
2. **Densify reward/feedback**: break “bundle tests” into more atomic checks so partial progress is measurable.
3. **Keep determinism**: preserve the existing mock-server approach and reproducible verifier behavior.
4. **Preserve benchmark intent**: still measure full-spec implementation, not just “read the tests”.
5. **Reduce cold-start friction**: provide a minimal starter scaffold so runs don’t die on trivial wiring.
6. **Enable capability vectors**: optionally provide curriculum/subtier tasks for profiling and ablation.

## Non-Goals

- Add “tries=N nudges” or multi-episode orchestration in the benchmark harness (explicitly excluded by decision).
- Change the upstream NLSpecs themselves.
- Add non-deterministic grading or real API calls.
- Build a perfect “hidden test” system (Harbor tasks are inherently open at runtime); the primary aim is faster iteration + better signal, not secrecy.

## Current Architecture (as of 2026-02-23)

- Tasks are generated from `src/attractorbench/adapter.py` into `tasks/`.
- Each task includes:
  - `instruction.md` (spec + constraints)
  - container `environment/` (Dockerfile, LiteLLM proxy sidecar)
  - `tests/test.sh` verifier script that runs:
    - `make build`
    - `make test`
    - `/tests/conformance/run_conformance.py --tier N`
    - `/tests/score.py` to write `/logs/verifier/reward.json` (+ `reward_details.json`)
- Conformance tests are already section-tagged and summarized into `sections` in `conformance_results.json`, which feeds DoD section scoring.

## Proposed Workstreams (High Level)

1. **Instruction Loop (no orchestration, just explicit guidance)**  
   Add a “Recommended Loop” section to `instruction.md` that explicitly tells agents to run conformance, read results, and continue iterating until timeout.

2. **Quick vs Full Conformance (public feedback loop, same verifier)**  
   Add a `--suite` flag (or equivalent) to the conformance runner:
   - `suite=quick`: fast “smoke” subset for frequent iteration by the agent
   - `suite=full`: current comprehensive suite used by the verifier for scoring

3. **More Atomic Conformance Tests + Runtime-Safe Caching**  
   Refactor conformance checks to:
   - split multi-requirement tests into smaller checks
   - reuse command outputs across checks to avoid runtime blow-ups

4. **Curriculum / Subtier Task Generation (optional mode)**  
   Add an optional generator mode that emits additional “subtier” tasks (per tier, per capability slice) for profiling and debugging:
   - tier1-core-infra, tier1-generation, tier1-streaming, tier1-tool-calling, tier1-structured-output, tier1-errors
   - analogous slices for tiers 2 and 3
   The canonical “full tier” tasks remain.

5. **Starter Scaffold (minimal wiring to avoid trivial early death)**  
   Pre-populate `/workspace` with a minimal, failing-by-default scaffold:
   - `Makefile` exists (targets present, not necessarily passing)
   - `bin/conformance` exists and is executable (stub that fails clearly)
   - optional helper script(s) to run quick conformance

## Workstream 1: Explicit “Recommended Loop” Instructions

### Motivation

If an agent never runs the harness, it has no dense feedback and tends to stop early. Many agents also fail to budget time for “debug and repair” phases.

### Spec of Change

Update generated `instruction.md` (both individual tiers and full-stack) to include a highly explicit loop, e.g.:

1. Implement a minimal end-to-end slice (start with CLI + env parsing).
2. Run quick conformance.
3. Read failures in `conformance_results.json` + logs.
4. Fix one class of failures at a time.
5. Repeat until quick is green, then run full.

Include:

- exact commands to run (`python3 /tests/conformance/run_conformance.py ...`)
- exact paths to inspect (`/logs/verifier/conformance_results.json`, `/logs/verifier/conformance.log`)
- advice to avoid stopping early (“keep going until timeout or all tests pass”)

### Acceptance Criteria

- Every generated task instruction has a visible “Recommended Loop” section.
- Instructions reference quick conformance explicitly.
- Full-stack instructions describe per-layer iteration (Layer 1 → 2 → 3).

### Implementation Notes

Likely changes:

- `src/attractorbench/adapter.py`
  - `generate_instruction()`
  - `generate_stacked_instruction()`

No scoring changes required.

## Workstream 2: Quick vs Full Conformance Suites

### Motivation

The full conformance suite can be slow and noisy during development. Agents benefit from a “tight loop” suite that catches the top failure modes quickly (plumbing, JSON validity, mock routing, basic request/response shapes).

This is a benchmark analogue to “unit tests (fast) vs integration tests (slow)”.

### Spec of Change

Add `--suite` to `/tests/conformance/run_conformance.py`.

- `--suite full` (default for verifier / scoring)
- `--suite quick` (recommended in instructions)
- Additional suites may exist for curriculum subtiers (see Workstream 4)

Suite filtering should be deterministic and transparent:

- Filter by `test.section` and/or `test.name` (stable IDs)
- No random sampling

### Proposed Quick Suites (initial)

The quick suite should be deliberately small and fast, but span the core “wiring”:

- Tier 0 quick:
  - build check
  - binary exists (or at least ensure it doesn’t early-return)
  - `client-from-env`
  - `list-models` JSON parse
  - `complete` JSON parse

- Tier 1 quick:
  - build check
  - `client-from-env`
  - `list-models` JSON array parse
  - `complete` JSON parse + minimal schema (id + content/output)
  - `provider_routing_openai` mock assertion
  - a single streaming “JSON-lines parse” check

- Tier 2 quick:
  - binary exists
  - `session-create`
  - `process-input` returns JSON + mock called
  - one tool dispatch sanity check

- Tier 3 quick:
  - binary exists
  - `parse` on a tiny DOT file (provided inline or generated temp)
  - `validate` on a tiny DOT file

### Acceptance Criteria

- Conformance runner supports `--suite`.
- Verifier continues to score using `full` suite (explicitly set in `tests/test.sh` to avoid ambiguity).
- Instructions point agents at `quick`.

### Implementation Notes

Likely changes:

- `src/attractorbench/adapter.py`
  - `generate_run_conformance()` (add `--suite`, implement filtering)
  - `generate_test_sh()` + `generate_stacked_test_sh()` (pass `--suite full`)

Backward compatibility:

- Old tasks still work if `--suite` defaults to `full` and verifier calls are updated.
- If we ever change defaults (e.g. default=quick), verifier must explicitly request `full`.

## Workstream 3: More Atomic Conformance Tests + Caching

### Motivation

“Bundle tests” hide progress. Example: a single streaming test might validate:

- exit code
- JSON-lines framing
- event ordering
- delta accumulation
- terminal event

If any subpiece fails, the whole test fails, creating sparse feedback.

Also, adding atomic checks naively can explode runtime if each check re-runs the same CLI subcommand.

### Spec of Change

1. Split large checks into multiple small checks, each with:
   - a narrow contract
   - a clear, actionable error message
2. Add caching for expensive subprocess calls:
   - run `./bin/conformance stream` once per input
   - reuse parsed lines/events across multiple checks
3. Maintain (or improve) section tagging so section pass rates remain meaningful.

### Design: Conformance Call Cache

Add a helper in conformance runner:

- Cache key: `(subcommand, stdin_hash, env_hash)`
- Cache value: `(exit_code, stdout, stderr, duration)`

Then tests become “checks over cached outputs” rather than repeated executions.

### Example Atomicization (Tier 1 Streaming)

Instead of 1–2 streaming tests, make:

- `stream_exit_zero`
- `stream_outputs_lines`
- `stream_lines_are_json`
- `stream_has_delta_event`
- `stream_has_terminal_event`
- `stream_delta_text_non_empty`

All should share the same cached `stream` call.

### Acceptance Criteria

- Full suite has more tests but does not blow verifier runtime (target: keep conformance under ~1–2 minutes).
- `conformance_results.json` becomes more diagnostic (more failing tests, smaller error scopes).
- Quick suite stays very fast (<10–20s).

### Implementation Notes

Likely changes:

- `src/attractorbench/adapter.py`
  - `generate_run_conformance()` tier test functions:
    - factor out shared inputs
    - introduce cached command runner
    - split tests

Be conservative about test explosion; prefer atomic checks only where they fix major bundling and ambiguity.

## Workstream 4: Curriculum / Subtier Task Generation (Optional)

### Motivation

Even with denser conformance, the full Tier 1+ tasks remain “coupled systems.” For characterization, it is useful to run smaller slices:

- to profile where a model breaks (e.g., streaming vs structured output)
- to do ablations (e.g., does the model fail before tool-calling?)
- to reduce variance and make small improvements measurable

### Spec of Change

Add an optional generator mode that produces additional tasks per tier, where:

- Each task references the full spec (no spec edits)
- The task’s conformance suite is restricted to a capability slice
- The task’s DoD checklist is restricted to relevant sections
- Timeouts are reduced (these are smaller tasks)

These tasks are *additive*; the canonical tier tasks remain the primary benchmark.

### Proposed Subtier Map (Initial)

Tier 1 (Unified LLM SDK):

- `tier1-core-infra` → section `core_infra`
- `tier1-generation` → section `generation` (blocking complete + response schema)
- `tier1-streaming` → streaming checks
- `tier1-tool-calling` → tool calling loop
- `tier1-structured-output` → `generate-object` + schema validation
- `tier1-error-handling` → auth + rate limit + invalid request behavior

Tier 2 (Coding Agent Loop):

- `tier2-core-loop` → `session-create`, `process-input`, LLM called
- `tier2-tool-execution` → `tool-dispatch` correctness
- `tier2-events` → event stream shape + minimum events
- `tier2-steering` → steering injection acknowledgement

Tier 3 (Attractor Pipeline):

- `tier3-parse-validate` → DOT parse + validation diagnostics
- `tier3-run` → run a minimal pipeline end-to-end
- `tier3-handlers` → handler registry and handler-specific behavior

### CLI / Generator Surface

Options (choose one; decide during implementation):

Option A (recommended): Add `--curriculum` to `attractorbench generate`

- default: existing behavior (tiers 0–3 and full-stack)
- `--curriculum`: also generate subtier tasks (in addition to base tasks)

Option B: Add `--tasks` selector instead of `--tiers`

- more flexible but higher churn

### Acceptance Criteria

- Curriculum generation is opt-in and does not change default outputs.
- Subtier slugs appear as separate tasks under `tasks/`.
- Each subtier’s verifier runs `run_conformance.py --tier N --suite <slice>`.
- Leaderboard continues to work (it already key’s off reward files; no strict slug list).

### Implementation Notes

This likely requires introducing a new abstraction in Python:

- `TierDef` (existing) stays as “spec + DoD parsing”
- Add `TaskDef` or `TaskVariantDef`:
  - `tier_number` (0–3)
  - `slug`, `name`
  - `suite` (e.g., `core_infra`, `quick`, `full`)
  - `dod_section_filter` (list of section keys)
  - timeouts

Then:

- generator emits base tasks from `TierDef` with `suite=full`
- generator emits subtier tasks from `TaskVariantDef`

## Workstream 5: Starter Scaffold

### Motivation

Too many runs die to trivial issues:

- missing Makefile targets
- missing executable bit on `./bin/conformance`
- missing directories

This is “benchmark tax” unrelated to the spec-following signal we want.

Also, conformance currently early-returns if `./bin/conformance` is missing; a stub allows conformance to run further and produce more actionable failures.

### Spec of Change

Pre-populate `/workspace` with a minimal scaffold at container start:

- `Makefile` exists with `build` + `test` targets (may fail by default or be no-op; decide carefully)
- `bin/conformance` exists and is executable, but returns non-zero with a helpful message
- Optional: `bin/run-conformance-quick` helper that runs the quick suite (tier-aware)

Key property: the scaffold should not make meaningful conformance pass “for free”.

### Implementation Approach

During task generation:

- create `starter/` directory in the generated task
- modify task Dockerfile to `COPY starter/ /workspace/`

### Acceptance Criteria

- On a brand new run, `/workspace/Makefile` and `/workspace/bin/conformance` exist.
- Conformance runner does not early-return on missing binary.
- No tier’s full conformance passes with scaffold alone.

### Notes on Scoring Impact

The scaffold may slightly increase “surface” progress (more tests run, clearer logs) without inflating true compliance.

If scaffold causes build/test to pass by default, adjust:

- scoring weights (if necessary), or
- conformance suite to include “real” checks beyond build success

## Rollout / Versioning

1. Implement Workstreams 1–3 first (instruction + suites + atomicization). These are highest leverage and lowest structural churn.
2. Add scaffold (Workstream 5) next; validate it doesn’t inflate scores meaningfully.
3. Add curriculum mode (Workstream 4) last; treat as experimental until it stabilizes.

Consider bumping benchmark version (`src/attractorbench/__init__.py`) once behavior changes affect comparability.

## Test Plan (Repo-Level)

Update/add unit tests to cover:

- conformance runner includes `--suite` parsing
- `generate_test_sh()` passes `--suite full`
- `generate_instruction()` includes “Recommended Loop” block
- scaffold files are generated and Dockerfile copies them (if implemented)
- curriculum mode produces expected slugs (if implemented)

Likely affected test files:

- `tests/test_adapter_generation.py`
- `tests/test_tiers_and_cli.py`

## Success Metrics

Quantitative:

- Reduced fraction of runs with “binary missing” early abort.
- More informative `conformance_results.json` (more granular fails).
- Higher “iteration rate” proxies (more tool calls / more conformance invocations during runs).
- Better separation in partial scores (less mass at 0.0–0.1).

Qualitative:

- When a run fails, `conformance_results.json` makes it obvious what to fix next.
- Agents more often keep trying until timeout rather than stopping after the first failure.

## Open Questions / Decisions Needed Before Implementation

1. Should `--suite` default be `full` (safe, conservative) or `quick` (agent-friendly)?
2. How much scaffold is acceptable without changing benchmark meaning?
3. Should curriculum tasks be included in LEADERBOARD.md by default, or tracked separately?
4. Where to cap conformance runtime if atomicization increases test count?

