"""Scoring and metrics computation for attractorbench."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TierConformance:
    """Per-tier conformance breakdown (for main task)."""

    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0


@dataclass
class RewardData:
    """Parsed reward.json from a single task trial."""

    build_success: int = 0
    self_test_pass_rate: float = 0.0
    self_test_count: int = 0
    conformance_total: int = 0
    conformance_passed: int = 0
    conformance_pass_rate: float = 0.0
    dod_scores: dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0
    # Per-tier conformance breakdowns (populated for main task)
    tier1_conformance: TierConformance | None = None
    tier2_conformance: TierConformance | None = None
    tier3_conformance: TierConformance | None = None
    # LLM judge results (populated when judge ran successfully)
    llm_judge_score: float | None = None
    llm_judge_stddev: float | None = None
    llm_judge_model: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> RewardData:
        # Prefer reward_details.json (full breakdown) over reward.json (Harbor single-key)
        details_path = path.parent / "reward_details.json"
        if details_path.exists():
            data = json.loads(details_path.read_text(encoding="utf-8"))
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
        dod = {k: v for k, v in data.items() if k.startswith("dod_")}

        # Parse per-tier conformance breakdowns if present
        tier_breakdowns: dict[int, TierConformance] = {}
        for tier_num in (1, 2, 3):
            total_key = f"tier{tier_num}_conformance_total"
            if total_key in data:
                tier_breakdowns[tier_num] = TierConformance(
                    total=data.get(total_key, 0),
                    passed=data.get(f"tier{tier_num}_conformance_passed", 0),
                    pass_rate=data.get(f"tier{tier_num}_conformance_pass_rate", 0.0),
                )

        return cls(
            build_success=data.get("build_success", 0),
            self_test_pass_rate=data.get("self_test_pass_rate", 0.0),
            self_test_count=data.get("self_test_count", 0),
            conformance_total=data.get("conformance_total", 0),
            conformance_passed=data.get("conformance_passed", 0),
            conformance_pass_rate=data.get("conformance_pass_rate", 0.0),
            dod_scores=dod,
            composite_score=data.get("composite_score", 0.0),
            tier1_conformance=tier_breakdowns.get(1),
            tier2_conformance=tier_breakdowns.get(2),
            tier3_conformance=tier_breakdowns.get(3),
            llm_judge_score=data.get("llm_judge_score"),
            llm_judge_stddev=data.get("llm_judge_stddev"),
            llm_judge_model=data.get("llm_judge_model"),
        )


@dataclass
class DerivedMetrics:
    """Derived metrics computed from reward + Harbor trial metadata."""

    tokens_per_compliance: float | None = None
    cost_per_compliance: float | None = None
    time_seconds: float | None = None
    compliance_efficiency: float | None = None


def compute_derived(
    reward: RewardData,
    total_tokens: int | None = None,
    cost_usd: float | None = None,
    wall_clock_seconds: float | None = None,
) -> DerivedMetrics:
    """Compute derived metrics from reward data and trial metadata."""
    metrics = DerivedMetrics()
    score = reward.composite_score

    if score > 0:
        if total_tokens is not None:
            metrics.tokens_per_compliance = total_tokens / score
        if cost_usd is not None:
            metrics.cost_per_compliance = cost_usd / score

    if wall_clock_seconds is not None:
        metrics.time_seconds = wall_clock_seconds
        if score > 0 and cost_usd is not None and cost_usd > 0:
            time_hours = wall_clock_seconds / 3600
            if time_hours > 0:
                metrics.compliance_efficiency = score / (cost_usd * time_hours)

    return metrics


def load_job_results(job_dir: Path) -> dict[str, RewardData]:
    """Load all reward.json files from a Harbor job directory."""
    if not job_dir.exists() or not job_dir.is_dir():
        raise FileNotFoundError(f"Job directory not found: {job_dir}")

    results: dict[str, RewardData] = {}
    for reward_file in sorted(job_dir.rglob("reward.json")):
        task_name = _infer_task_name(reward_file, job_dir)
        dedup_suffix = 2
        base_name = task_name
        while task_name in results:
            task_name = f"{base_name}#{dedup_suffix}"
            dedup_suffix += 1
        results[task_name] = RewardData.from_file(reward_file)
    return results


def compare_jobs(job_dirs: list[Path]) -> list[dict[str, Any]]:
    """Compare results across multiple Harbor job directories."""
    rows: list[dict[str, Any]] = []
    for job_dir in sorted(job_dirs, key=lambda path: path.name):
        results = load_job_results(job_dir)
        for task_name, reward in sorted(results.items()):
            rows.append({
                "job": job_dir.name,
                "task": task_name,
                "build_success": reward.build_success,
                "self_test_pass_rate": reward.self_test_pass_rate,
                "conformance_pass_rate": reward.conformance_pass_rate,
                "composite_score": reward.composite_score,
            })
    return rows


_TASK_SLUG_RE = re.compile(r"^(tier\d+-[a-z0-9-]+|main|full-stack)$")


def _infer_task_name(reward_file: Path, job_dir: Path) -> str:
    rel_parts = reward_file.relative_to(job_dir).parts

    for part in rel_parts:
        if _TASK_SLUG_RE.match(part):
            return part

    if "tasks" in rel_parts:
        idx = rel_parts.index("tasks")
        if idx + 1 < len(rel_parts):
            return rel_parts[idx + 1]

    if len(rel_parts) >= 3 and rel_parts[-3:-1] == ("logs", "verifier"):
        prefix = rel_parts[:-3]
        if prefix:
            return "/".join(prefix)

    if len(rel_parts) > 1:
        return "/".join(rel_parts[:-1])

    return reward_file.stem
