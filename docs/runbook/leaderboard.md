# Leaderboard Curation Runbook

How to update `LEADERBOARD.md` and `RUN_LOG.md` after benchmark runs.

## The Three-File System

| File | Purpose | Committed? |
|------|---------|------------|
| `results/leaderboard.md`, `results/run_log.md` | Ad hoc CLI output (`make results`) | No (gitignored) |
| `RUN_LOG.md` | Complete historical ledger, every run ever | Yes |
| `LEADERBOARD.md` | Curated snapshot: narrative + bests + top runs | Yes |

The flow: run `make results` to generate raw tables, then use them as input when manually updating the two committed files.

## After Each Run

```bash
# 1. Score the job
uv run attractorbench score jobs/<job-name>

# 2. Generate ad hoc tables from all local jobs
make results

# 3. Manually update RUN_LOG.md and LEADERBOARD.md (see below)
```

`make results` does NOT auto-update the committed files. It writes to `results/*.md` so you can review before curating.

## Updating RUN_LOG.md

Every scored run gets a row in `RUN_LOG.md`. No filtering, no judgment.

Required fields per row:
- `Run` (job name)
- `Bench Version` (from task metadata)
- `Agent`, `Model`, `Effort`
- `Tasks` (number of task directories scored)
- `Score` (composite)
- `Tokens`, `Time`, `Tool Calls`, `Cost`
- `Date`
- `Notes` (data quality flags, backfill annotations, etc.)

Copy the row from `results/run_log.md` and append it to `RUN_LOG.md`. Failed runs (score 0.000) still get recorded.

## Updating LEADERBOARD.md

LEADERBOARD.md is curated. Not every run belongs here. The file has three sections:

### Narrative

A few sentences summarizing the current state: top score, notable trends, known issues. Update when something meaningful changes (new top score, new agent, data quality fix).

### Current Bests

Four metrics, each showing the single best run:

| Metric | Criteria |
|--------|----------|
| Best score | Highest composite, any run |
| Best speed | Shortest wall time among runs with score > 0 |
| Best token efficiency | Lowest tokens/point among runs with **reliable** token data |
| Best dollar efficiency | Lowest $/point among runs with **reliable** cost data |

Efficiency metrics require reliable data. If a run's tokens or cost are known to be wrong, exclude it from efficiency bests (it can still win on score or speed).

### Snapshot Table

The top runs, sorted by score descending. Guidelines:

- Include the best run per agent+model combination
- Include notable second runs if they show interesting variance
- Drop runs that are strictly dominated (same agent+model, lower score, no unique insight)
- Keep the table to roughly 8-12 rows

## Data Quality Checks

Before adding a run to the leaderboard, verify:

1. **Token counts are plausible.** Compare to other runs at similar scores and times. A 15-minute run producing 191K tokens when a comparable run shows 6.9M is a red flag.

2. **LiteLLM proxy was active.** Check `LEADERBOARD.md` for known agent-specific issues. As of 2026-02-23:
   - `claude-code`, `codex`: LiteLLM working, data reliable
   - `gemini-cli`: LiteLLM fixed (was bypassed pre-fix, see [gemini-cli.md](gemini-cli.md))
   - `opencode`: Native tracking, does not use LiteLLM proxy

3. **Score of 0.000 with 0 tokens and < 30s time** usually means the agent failed to start (Docker issue, auth failure, etc.). Record in RUN_LOG.md but do not add to LEADERBOARD.md.

4. **Benchmark version matches.** Only compare runs on the same `bench_version`.

## Flagging Unreliable Data

When a run has valid scores but unreliable efficiency data:

- Mark the affected cells with a dagger: `191K &dagger;`
- Add a footnote: `&dagger; Underreported -- [reason]. Actual likely Nx higher.`
- Exclude the run from efficiency bests
- Keep it in the snapshot table (its score is still valid)

## Example: Adding a New Run

```
# 1. Score
uv run attractorbench score jobs/opus46-v3

# 2. Generate tables
make results

# 3. Append to RUN_LOG.md
#    Copy the new row from results/run_log.md

# 4. Check: does this run change the leaderboard?
#    - New top score? Update narrative + bests + snapshot table.
#    - Better than existing run for same agent+model? Replace in snapshot table.
#    - Worse than existing run, nothing new? Skip LEADERBOARD.md, it's already in RUN_LOG.md.

# 5. Commit
git add LEADERBOARD.md RUN_LOG.md
git commit -m "Add opus46-v3 results (score: 0.XXX)"
```
