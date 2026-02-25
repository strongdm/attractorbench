"""Pydantic models for attractorbench leaderboard data."""

from __future__ import annotations

from pydantic import BaseModel


class RunMetadata(BaseModel):
    """Run-level metadata: source TBD (sidecar file, Harbor API, etc.)."""

    agent: str  # e.g. "claude-code", "aider"
    model: str  # e.g. "claude-opus-4-6", "gpt-4o"
    label: str = ""  # optional disambiguator
    bench_version: str = ""  # benchmark version for comparability
    effort: str = ""  # e.g. medium/high/extra_high
    total_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tool_calls: int | None = None
    wall_seconds: float | None = None
    cost_usd: float | None = None


class LeaderboardEntry(BaseModel):
    """One row on the leaderboard: an agent+model run across task(s)."""

    agent: str
    model: str
    label: str = ""
    # Score metrics (from reward.json)
    tasks_attempted: int
    build_rate: float
    avg_self_test: float
    avg_conformance: float
    avg_composite: float
    # Efficiency metrics (nullable: source TBD)
    total_tokens: int | None = None
    wall_seconds: float | None = None
    tool_calls: int | None = None
    cost_usd: float | None = None
    # Per-tier conformance rates (populated for main task)
    tier1_conformance: float | None = None
    tier2_conformance: float | None = None
    tier3_conformance: float | None = None
    # LLM judge score (populated when judge ran successfully)
    llm_judge_score: float | None = None
    # Derived (computed if inputs available)
    tokens_per_point: float | None = None  # total_tokens / avg_composite
    cost_per_point: float | None = None  # cost_usd / avg_composite


class RunLogEntry(BaseModel):
    """One row in the run log: a single job directory's totals."""

    job_name: str  # directory name, e.g. "gemini31-full"
    bench_version: str = ""
    agent: str
    model: str
    effort: str = ""
    tasks: int
    avg_composite: float
    total_tokens: int | None = None
    wall_seconds: float | None = None
    tool_calls: int | None = None
    cost_usd: float | None = None
    date: str = ""  # ISO date, extracted from first trial's started_at


class Leaderboard(BaseModel):
    """Full leaderboard state."""

    generated_at: str  # ISO timestamp
    entries: list[LeaderboardEntry]
