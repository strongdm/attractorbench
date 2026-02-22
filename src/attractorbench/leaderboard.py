"""Core logic for building and formatting the attractorbench leaderboard."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from litellm import model_cost
from rich.console import Console
from rich.table import Table

from attractorbench.models import Leaderboard, LeaderboardEntry, RunMetadata
from attractorbench.scoring import RewardData, load_job_results

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt_tokens(n: int | None) -> str:
    """Format a token count for display."""
    if n is None:
        return "—"
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.0f}K"
    return f"{n / 1_000_000:.1f}M"


def fmt_time(s: float | None) -> str:
    """Format seconds into a human-readable duration."""
    if s is None:
        return "—"
    s_int = int(s)
    if s_int < 60:
        return f"{s_int}s"
    if s_int < 3600:
        minutes, secs = divmod(s_int, 60)
        return f"{minutes}m{secs:02d}s"
    hours, remainder = divmod(s_int, 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}m"


def fmt_cost(c: float | None) -> str:
    """Format a USD cost for display."""
    if c is None:
        return "—"
    return f"${c:.2f}"


def fmt_ratio(value: float | None, kind: str = "tokens") -> str:
    """Format a per-point ratio (tokens/pt or $/pt)."""
    if value is None:
        return "—"
    if kind == "cost":
        return fmt_cost(value)
    return fmt_tokens(int(value))


# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------


def _resolve_model_name(raw: str) -> str:
    """Strip provider prefix (e.g. 'anthropic/claude-sonnet-4-6' → 'claude-sonnet-4-6')."""
    if "/" in raw:
        return raw.split("/", 1)[1]
    return raw


def _lookup_model_costs(model_name: str) -> dict | None:
    """Look up litellm pricing for *model_name*, trying several key variants."""
    candidates = [
        model_name,                              # claude-sonnet-4-6
        f"anthropic/{model_name}",               # anthropic/claude-sonnet-4-6
        f"anthropic.{model_name}",               # anthropic.claude-sonnet-4-6
    ]
    for key in candidates:
        if key in model_cost:
            return model_cost[key]
    return None


def _compute_cost(
    model_name: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    cache_creation_tokens: int | None = None,
    cache_read_tokens: int | None = None,
) -> float | None:
    """Compute USD cost using litellm pricing tables.

    Anthropic billing model:
    - input_tokens includes cache reads; cache_creation is separate.
    - regular_input = prompt_tokens - cache_read_tokens
    - cost = regular * input_rate + creation * creation_rate
             + reads * read_rate + output * output_rate
    """
    costs = _lookup_model_costs(model_name)
    if costs is None:
        return None

    input_rate = costs.get("input_cost_per_token", 0)
    output_rate = costs.get("output_cost_per_token", 0)
    creation_rate = costs.get("cache_creation_input_token_cost", input_rate)
    read_rate = costs.get("cache_read_input_token_cost", input_rate)

    cr = cache_read_tokens or 0
    cc = cache_creation_tokens or 0
    regular_input = max(0, prompt_tokens - cr)

    return (
        regular_input * input_rate
        + cc * creation_rate
        + cr * read_rate
        + completion_tokens * output_rate
    )


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp, handling trailing Z."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_harbor_metrics(job_dir: Path) -> RunMetadata | None:
    """Extract metrics from Harbor result.json + trajectory.json per trial.

    Scans trial subdirectories for result.json files produced by Harbor.
    Aggregates tokens, wall time, tool calls, and cost across all trials.
    Returns None if no trial result.json files are found.
    """
    trial_results: list[dict] = []

    for child in sorted(job_dir.iterdir()) if job_dir.is_dir() else []:
        rj = child / "result.json"
        if child.is_dir() and rj.is_file():
            try:
                trial_results.append(json.loads(rj.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Skipping unreadable %s: %s", rj, exc)

    if not trial_results:
        return None

    # --- Derive agent / model from the first trial ---
    first = trial_results[0]
    agent_name = (
        first.get("config", {}).get("agent", {}).get("name")
        or first.get("agent_info", {}).get("name", "unknown")
    )
    raw_model = (
        first.get("config", {}).get("agent", {}).get("model_name")
        or first.get("agent_info", {}).get("model_info", {}).get("name", "")
    )
    display_model = _resolve_model_name(raw_model)

    # --- Aggregate across trials ---
    total_prompt = 0
    total_completion = 0
    total_cache_creation = 0
    total_cache_read = 0
    total_wall = 0.0
    total_tool_calls = 0
    has_any_tokens = False

    for trial in trial_results:
        trial_dir = job_dir / trial.get("trial_name", "")

        # -- Tokens from result.json agent_result --
        ar = trial.get("agent_result") or {}
        n_input = ar.get("n_input_tokens")
        n_output = ar.get("n_output_tokens")
        n_cache = ar.get("n_cache_tokens")

        if n_input is not None:
            has_any_tokens = True
            total_prompt += n_input
            total_completion += n_output or 0

        # -- Wall time from agent_execution phase --
        ae = trial.get("agent_execution") or {}
        ae_start = ae.get("started_at")
        ae_end = ae.get("finished_at")
        if ae_start and ae_end:
            dt = (_parse_iso(ae_end) - _parse_iso(ae_start)).total_seconds()
            total_wall += max(0.0, dt)

        # -- Trajectory: cache breakdown + tool calls --
        traj_path = trial_dir / "agent" / "trajectory.json"
        if traj_path.is_file():
            try:
                traj = json.loads(traj_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                traj = {}

            # Tool calls from steps
            for step in traj.get("steps", []):
                if "tool_calls" in step:
                    total_tool_calls += len(step["tool_calls"])

            # Cache breakdown from final_metrics
            fm_extra = (traj.get("final_metrics") or {}).get("extra") or {}
            cc = fm_extra.get("total_cache_creation_input_tokens")
            cr = fm_extra.get("total_cache_read_input_tokens")
            if cc is not None:
                total_cache_creation += cc
            if cr is not None:
                total_cache_read += cr
        elif n_cache is not None and has_any_tokens:
            # No trajectory — treat n_cache_tokens as cache reads (conservative)
            total_cache_read += n_cache

    if not has_any_tokens:
        # No token data at all — still return agent/model + wall time
        return RunMetadata(
            agent=agent_name,
            model=display_model,
            wall_seconds=total_wall if total_wall > 0 else None,
        )

    total_tokens = total_prompt + total_completion
    cost = _compute_cost(
        display_model,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        cache_creation_tokens=total_cache_creation or None,
        cache_read_tokens=total_cache_read or None,
    )

    return RunMetadata(
        agent=agent_name,
        model=display_model,
        total_tokens=total_tokens,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        tool_calls=total_tool_calls or None,
        wall_seconds=total_wall if total_wall > 0 else None,
        cost_usd=round(cost, 4) if cost is not None else None,
    )


def _load_metadata_json(job_dir: Path) -> RunMetadata | None:
    """Load metadata.json sidecar (legacy path)."""
    candidates = [
        job_dir / "metadata.json",
        job_dir / "logs" / "verifier" / "metadata.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return RunMetadata(**data)
            except (json.JSONDecodeError, Exception) as exc:
                logger.debug("Failed to parse metadata at %s: %s", path, exc)
                return None
    return None


def load_run_metadata(job_dir: Path) -> RunMetadata | None:
    """Load run metadata, preferring Harbor native files over metadata.json.

    Resolution order:
    1. Harbor result.json + trajectory.json per trial (richest data)
    2. metadata.json sidecar (legacy / manually written)
    """
    harbor = load_harbor_metrics(job_dir)
    if harbor is not None:
        return harbor

    meta = _load_metadata_json(job_dir)
    if meta is not None:
        return meta

    logger.debug("No metadata found in %s", job_dir)
    return None


# ---------------------------------------------------------------------------
# Leaderboard building
# ---------------------------------------------------------------------------

SORT_COLUMNS = {
    "composite": ("avg_composite", True),   # descending
    "cost": ("cost_usd", False),             # ascending
    "tokens": ("total_tokens", False),       # ascending
    "time": ("wall_seconds", False),         # ascending
    "efficiency": ("tokens_per_point", False),  # ascending
}


def build_leaderboard(job_dirs: list[Path]) -> Leaderboard:
    """Build a leaderboard from one or more job directories."""
    entries: list[LeaderboardEntry] = []

    for job_dir in job_dirs:
        results = load_job_results(job_dir)
        if not results:
            logger.debug("No reward.json files found in %s, skipping", job_dir)
            continue

        metadata = load_run_metadata(job_dir)

        count = len(results)
        rewards = list(results.values())
        build_rate = sum(1 for r in rewards if r.build_success) / count
        avg_self = sum(r.self_test_pass_rate for r in rewards) / count
        avg_conf = sum(r.conformance_pass_rate for r in rewards) / count
        avg_composite = sum(r.composite_score for r in rewards) / count

        agent = metadata.agent if metadata else job_dir.name
        model = metadata.model if metadata else ""
        label = metadata.label if metadata else ""

        total_tokens = metadata.total_tokens if metadata else None
        wall_seconds = metadata.wall_seconds if metadata else None
        tool_calls = metadata.tool_calls if metadata else None
        cost_usd = metadata.cost_usd if metadata else None

        tokens_per_point = None
        if total_tokens is not None and avg_composite > 0:
            tokens_per_point = total_tokens / avg_composite

        cost_per_point = None
        if cost_usd is not None and avg_composite > 0:
            cost_per_point = cost_usd / avg_composite

        entries.append(
            LeaderboardEntry(
                agent=agent,
                model=model,
                label=label,
                tasks_attempted=count,
                build_rate=build_rate,
                avg_self_test=avg_self,
                avg_conformance=avg_conf,
                avg_composite=avg_composite,
                total_tokens=total_tokens,
                wall_seconds=wall_seconds,
                tool_calls=tool_calls,
                cost_usd=cost_usd,
                tokens_per_point=tokens_per_point,
                cost_per_point=cost_per_point,
            )
        )

    return Leaderboard(
        generated_at=datetime.now(timezone.utc).isoformat(),
        entries=entries,
    )


def sort_leaderboard(leaderboard: Leaderboard, sort_by: str = "composite") -> Leaderboard:
    """Return a new Leaderboard with entries sorted by the given column."""
    col, descending = SORT_COLUMNS.get(sort_by, ("avg_composite", True))

    def sort_key(entry: LeaderboardEntry) -> tuple[int, float]:
        value = getattr(entry, col)
        if value is None:
            # Push nulls to the end regardless of sort direction
            return (1, 0.0)
        return (0, value)

    sorted_entries = sorted(leaderboard.entries, key=sort_key, reverse=descending)
    return Leaderboard(generated_at=leaderboard.generated_at, entries=sorted_entries)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_table(leaderboard: Leaderboard, console: Console) -> None:
    """Render the leaderboard as a Rich table."""
    table = Table(title="Leaderboard")
    table.add_column("Agent", style="bold")
    table.add_column("Model")
    table.add_column("Label")
    table.add_column("Tasks", justify="right")
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Tokens", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Tool Calls", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Tok/Pt", justify="right")
    table.add_column("$/Pt", justify="right")

    for e in leaderboard.entries:
        table.add_row(
            e.agent,
            e.model,
            e.label,
            str(e.tasks_attempted),
            f"{e.avg_composite:.3f}",
            fmt_tokens(e.total_tokens),
            fmt_time(e.wall_seconds),
            str(e.tool_calls) if e.tool_calls is not None else "—",
            fmt_cost(e.cost_usd),
            fmt_ratio(e.tokens_per_point, "tokens"),
            fmt_ratio(e.cost_per_point, "cost"),
        )

    console.print(table)


def render_markdown(leaderboard: Leaderboard) -> str:
    """Render the leaderboard as a markdown table string."""
    lines = [
        "| Agent | Model | Label | Tasks | Score | Tokens | Time | Tool Calls | Cost | Tok/Pt | $/Pt |",
        "|-------|-------|-------|------:|------:|-------:|-----:|-----------:|-----:|-------:|-----:|",
    ]
    for e in leaderboard.entries:
        tool_calls_str = str(e.tool_calls) if e.tool_calls is not None else "—"
        lines.append(
            f"| {e.agent} | {e.model} | {e.label} "
            f"| {e.tasks_attempted} | {e.avg_composite:.3f} "
            f"| {fmt_tokens(e.total_tokens)} | {fmt_time(e.wall_seconds)} "
            f"| {tool_calls_str} | {fmt_cost(e.cost_usd)} "
            f"| {fmt_ratio(e.tokens_per_point, 'tokens')} "
            f"| {fmt_ratio(e.cost_per_point, 'cost')} |"
        )
    return "\n".join(lines)
