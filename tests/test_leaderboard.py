import json
import tempfile
import unittest
from pathlib import Path

from attractorbench.leaderboard import (
    _compute_cost,
    _resolve_model_name,
    build_leaderboard,
    fmt_cost,
    fmt_time,
    fmt_tokens,
    fmt_ratio,
    load_harbor_metrics,
    load_run_metadata,
    render_markdown,
    sort_leaderboard,
)
from attractorbench.models import RunMetadata


def _write_reward(path: Path, *, build: int = 1, self_rate: float = 0.9,
                  conf_rate: float = 0.8, composite: float = 0.83) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "build_success": build,
        "self_test_pass_rate": self_rate,
        "self_test_count": 10,
        "conformance_total": 20,
        "conformance_passed": int(conf_rate * 20),
        "conformance_pass_rate": conf_rate,
        "composite_score": composite,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_metadata(path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    defaults = {"agent": "claude-code", "model": "claude-opus-4-6"}
    defaults.update(kwargs)
    path.write_text(json.dumps(defaults), encoding="utf-8")


class TestFmtTokens(unittest.TestCase):
    def test_none(self) -> None:
        self.assertEqual("—", fmt_tokens(None))

    def test_small(self) -> None:
        self.assertEqual("842", fmt_tokens(842))

    def test_thousands(self) -> None:
        self.assertEqual("145K", fmt_tokens(145_200))

    def test_millions(self) -> None:
        self.assertEqual("1.2M", fmt_tokens(1_200_000))

    def test_exact_thousand(self) -> None:
        self.assertEqual("1K", fmt_tokens(1_000))


class TestFmtTime(unittest.TestCase):
    def test_none(self) -> None:
        self.assertEqual("—", fmt_time(None))

    def test_seconds(self) -> None:
        self.assertEqual("42s", fmt_time(42.0))

    def test_minutes(self) -> None:
        self.assertEqual("6m52s", fmt_time(412.0))

    def test_hours(self) -> None:
        self.assertEqual("1h12m", fmt_time(4320.0))


class TestFmtCost(unittest.TestCase):
    def test_none(self) -> None:
        self.assertEqual("—", fmt_cost(None))

    def test_value(self) -> None:
        self.assertEqual("$4.23", fmt_cost(4.23))

    def test_zero(self) -> None:
        self.assertEqual("$0.00", fmt_cost(0.0))


class TestFmtRatio(unittest.TestCase):
    def test_none(self) -> None:
        self.assertEqual("—", fmt_ratio(None))

    def test_tokens(self) -> None:
        self.assertEqual("175K", fmt_ratio(175_000.0, "tokens"))

    def test_cost(self) -> None:
        self.assertEqual("$5.10", fmt_ratio(5.10, "cost"))


class TestLoadRunMetadata(unittest.TestCase):
    def test_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_run_metadata(Path(tmpdir))
            self.assertIsNone(result)

    def test_loads_from_job_dir_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            _write_metadata(
                job_dir / "metadata.json",
                agent="aider", model="gpt-4o", total_tokens=89000,
            )
            result = load_run_metadata(job_dir)
            self.assertIsNotNone(result)
            self.assertEqual("aider", result.agent)
            self.assertEqual("gpt-4o", result.model)
            self.assertEqual(89000, result.total_tokens)

    def test_loads_from_logs_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            _write_metadata(
                job_dir / "logs" / "verifier" / "metadata.json",
                agent="claude-code", model="opus", wall_seconds=300.0,
            )
            result = load_run_metadata(job_dir)
            self.assertIsNotNone(result)
            self.assertEqual(300.0, result.wall_seconds)


class TestBuildLeaderboard(unittest.TestCase):
    def test_single_job_no_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "run-a"
            _write_reward(
                job_dir / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.83,
            )

            lb = build_leaderboard([job_dir])

            self.assertEqual(1, len(lb.entries))
            entry = lb.entries[0]
            self.assertEqual("run-a", entry.agent)  # falls back to dir name
            self.assertEqual("", entry.model)
            self.assertEqual(1, entry.tasks_attempted)
            self.assertAlmostEqual(0.83, entry.avg_composite, places=2)
            # Efficiency columns should be None
            self.assertIsNone(entry.total_tokens)
            self.assertIsNone(entry.wall_seconds)
            self.assertIsNone(entry.cost_usd)
            self.assertIsNone(entry.tokens_per_point)

    def test_single_job_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "run-b"
            _write_reward(
                job_dir / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.83,
            )
            _write_metadata(
                job_dir / "metadata.json",
                agent="claude-code", model="opus-4", total_tokens=145200,
                cost_usd=4.23, wall_seconds=412.5, tool_calls=83,
            )

            lb = build_leaderboard([job_dir])

            entry = lb.entries[0]
            self.assertEqual("claude-code", entry.agent)
            self.assertEqual("opus-4", entry.model)
            self.assertEqual(145200, entry.total_tokens)
            self.assertEqual(83, entry.tool_calls)
            self.assertAlmostEqual(4.23, entry.cost_usd)
            # Derived metrics
            self.assertIsNotNone(entry.tokens_per_point)
            self.assertAlmostEqual(145200 / 0.83, entry.tokens_per_point, places=0)
            self.assertIsNotNone(entry.cost_per_point)

    def test_multiple_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_a = root / "run-a"
            job_b = root / "run-b"

            _write_reward(
                job_a / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.9,
            )
            _write_reward(
                job_b / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.6,
            )

            lb = build_leaderboard([job_a, job_b])
            self.assertEqual(2, len(lb.entries))

    def test_empty_job_dir_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "empty-job"
            job_dir.mkdir()
            lb = build_leaderboard([job_dir])
            self.assertEqual(0, len(lb.entries))


class TestSortLeaderboard(unittest.TestCase):
    def test_sort_composite_descending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_a = root / "low"
            job_b = root / "high"

            _write_reward(
                job_a / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.5,
            )
            _write_reward(
                job_b / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.9,
            )

            lb = build_leaderboard([job_a, job_b])
            lb = sort_leaderboard(lb, "composite")

            self.assertGreater(lb.entries[0].avg_composite, lb.entries[1].avg_composite)

    def test_sort_cost_ascending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_a = root / "cheap"
            job_b = root / "expensive"

            _write_reward(
                job_a / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.8,
            )
            _write_metadata(job_a / "metadata.json", agent="a", model="m", cost_usd=2.0)

            _write_reward(
                job_b / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.8,
            )
            _write_metadata(job_b / "metadata.json", agent="b", model="m", cost_usd=8.0)

            lb = build_leaderboard([job_a, job_b])
            lb = sort_leaderboard(lb, "cost")

            self.assertLess(lb.entries[0].cost_usd, lb.entries[1].cost_usd)

    def test_nulls_sorted_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_a = root / "has-cost"
            job_b = root / "no-cost"

            _write_reward(
                job_a / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.8,
            )
            _write_metadata(job_a / "metadata.json", agent="a", model="m", cost_usd=5.0)

            _write_reward(
                job_b / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.9,
            )

            lb = build_leaderboard([job_a, job_b])
            lb = sort_leaderboard(lb, "cost")

            # Entry with actual cost should come first, null-cost at end
            self.assertIsNotNone(lb.entries[0].cost_usd)
            self.assertIsNone(lb.entries[1].cost_usd)


class TestRenderMarkdown(unittest.TestCase):
    def test_produces_valid_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "run-a"
            _write_reward(
                job_dir / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.83,
            )
            _write_metadata(
                job_dir / "metadata.json",
                agent="claude-code", model="opus-4",
                total_tokens=145200, cost_usd=4.23,
                wall_seconds=412.0, tool_calls=83,
            )

            lb = build_leaderboard([job_dir])
            md = render_markdown(lb)

            lines = md.strip().split("\n")
            # Title header + blank + description + blank + table header + separator + data row
            self.assertGreaterEqual(len(lines), 7)
            # Title line present
            self.assertTrue(lines[0].startswith("# "))
            # Table lines start and end with |
            table_lines = [l for l in lines if l.startswith("|")]
            self.assertGreaterEqual(len(table_lines), 3)
            for line in table_lines:
                self.assertTrue(line.endswith("|"))
            # Check content appears
            self.assertIn("claude-code", md)
            self.assertIn("opus-4", md)
            self.assertIn("145K", md)
            self.assertIn("$4.23", md)

    def test_dashes_for_missing_efficiency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "run-a"
            _write_reward(
                job_dir / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                composite=0.83,
            )

            lb = build_leaderboard([job_dir])
            md = render_markdown(lb)

            self.assertIn("—", md)


# ---------------------------------------------------------------------------
# Harbor metrics helpers
# ---------------------------------------------------------------------------

def _make_trial_result(
    trial_name: str = "tier1-unified-llm__abc123",
    agent_name: str = "claude-code",
    model_name: str = "anthropic/claude-sonnet-4-6",
    n_input_tokens: int | None = 1_000_000,
    n_cache_tokens: int | None = 900_000,
    n_output_tokens: int | None = 5_000,
    exec_start: str = "2026-02-22T08:00:00Z",
    exec_end: str = "2026-02-22T08:10:00Z",
) -> dict:
    return {
        "trial_name": trial_name,
        "config": {
            "agent": {"name": agent_name, "model_name": model_name},
        },
        "agent_info": {
            "name": agent_name,
            "model_info": {"name": model_name.split("/")[-1], "provider": "anthropic"},
        },
        "agent_result": {
            "n_input_tokens": n_input_tokens,
            "n_cache_tokens": n_cache_tokens,
            "n_output_tokens": n_output_tokens,
            "cost_usd": None,
        },
        "agent_execution": {
            "started_at": exec_start,
            "finished_at": exec_end,
        },
    }


def _make_trajectory(
    total_prompt: int = 1_000_000,
    total_completion: int = 5_000,
    total_cached: int = 900_000,
    cache_creation: int = 50_000,
    cache_read: int = 900_000,
    tool_call_counts: list[int] | None = None,
) -> dict:
    """Build a minimal ATIF trajectory with final_metrics and tool call steps."""
    steps = []
    for i, tc_count in enumerate(tool_call_counts or [3, 2]):
        steps.append({
            "step_id": i + 1,
            "source": "agent",
            "tool_calls": [{"name": f"tool_{j}"} for j in range(tc_count)],
        })
    return {
        "schema_version": "ATIF-v1.2",
        "agent": {"name": "claude-code", "version": "2.0", "model_name": "claude-sonnet-4-6"},
        "steps": steps,
        "final_metrics": {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_cached_tokens": total_cached,
            "extra": {
                "total_cache_creation_input_tokens": cache_creation,
                "total_cache_read_input_tokens": cache_read,
            },
        },
    }


def _write_trial(job_dir: Path, result: dict, trajectory: dict | None = None) -> None:
    """Write a trial's result.json (and optionally trajectory.json) under job_dir."""
    trial_name = result["trial_name"]
    trial_dir = job_dir / trial_name
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    if trajectory is not None:
        agent_dir = trial_dir / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")


class TestResolveModelName(unittest.TestCase):
    def test_strips_provider(self) -> None:
        self.assertEqual("claude-sonnet-4-6", _resolve_model_name("anthropic/claude-sonnet-4-6"))

    def test_no_prefix(self) -> None:
        self.assertEqual("gpt-4o", _resolve_model_name("gpt-4o"))


class TestComputeCost(unittest.TestCase):
    def test_known_model(self) -> None:
        cost = _compute_cost(
            "claude-sonnet-4-6",
            prompt_tokens=1_000_000,
            completion_tokens=5_000,
            cache_creation_tokens=50_000,
            cache_read_tokens=900_000,
        )
        self.assertIsNotNone(cost)
        self.assertGreater(cost, 0.0)

        # Verify the math:
        # regular_input = 1_000_000 - 900_000 = 100_000
        # cost = 100_000 * 3e-6 + 50_000 * 3.75e-6 + 900_000 * 3e-7 + 5_000 * 1.5e-5
        expected = (100_000 * 3e-6) + (50_000 * 3.75e-6) + (900_000 * 3e-7) + (5_000 * 1.5e-5)
        self.assertAlmostEqual(cost, expected, places=6)

    def test_unknown_model_returns_none(self) -> None:
        cost = _compute_cost(
            "nonexistent-model-xyz",
            prompt_tokens=1000,
            completion_tokens=100,
        )
        self.assertIsNone(cost)

    def test_no_cache_tokens(self) -> None:
        cost = _compute_cost(
            "claude-sonnet-4-6",
            prompt_tokens=10_000,
            completion_tokens=1_000,
        )
        # All prompt tokens billed at regular rate
        expected = 10_000 * 3e-6 + 1_000 * 1.5e-5
        self.assertAlmostEqual(cost, expected, places=6)


class TestLoadHarborMetrics(unittest.TestCase):
    def test_returns_none_for_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(load_harbor_metrics(Path(tmpdir)))

    def test_single_trial_with_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            result = _make_trial_result()
            traj = _make_trajectory(tool_call_counts=[3, 2, 5])
            _write_trial(job_dir, result, traj)

            meta = load_harbor_metrics(job_dir)
            self.assertIsNotNone(meta)
            self.assertEqual("claude-code", meta.agent)
            self.assertEqual("claude-sonnet-4-6", meta.model)
            self.assertEqual(1_000_000 + 5_000, meta.total_tokens)
            self.assertEqual(10, meta.tool_calls)  # 3+2+5
            self.assertAlmostEqual(600.0, meta.wall_seconds)  # 10 minutes
            self.assertIsNotNone(meta.cost_usd)

    def test_single_trial_without_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            result = _make_trial_result(n_cache_tokens=800_000)
            _write_trial(job_dir, result, trajectory=None)

            meta = load_harbor_metrics(job_dir)
            self.assertIsNotNone(meta)
            self.assertEqual(1_000_000 + 5_000, meta.total_tokens)
            # Without trajectory, tool_calls should be None
            self.assertIsNone(meta.tool_calls)
            # Cost should still be computed (cache_read from n_cache_tokens)
            self.assertIsNotNone(meta.cost_usd)

    def test_aggregation_across_trials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            r1 = _make_trial_result(
                trial_name="tier1__aaa",
                n_input_tokens=500_000, n_output_tokens=2_000, n_cache_tokens=400_000,
                exec_start="2026-02-22T08:00:00Z", exec_end="2026-02-22T08:05:00Z",
            )
            r2 = _make_trial_result(
                trial_name="tier2__bbb",
                n_input_tokens=300_000, n_output_tokens=1_000, n_cache_tokens=200_000,
                exec_start="2026-02-22T09:00:00Z", exec_end="2026-02-22T09:10:00Z",
            )
            t1 = _make_trajectory(
                total_prompt=500_000, total_completion=2_000,
                cache_creation=30_000, cache_read=400_000,
                tool_call_counts=[4, 3],
            )
            t2 = _make_trajectory(
                total_prompt=300_000, total_completion=1_000,
                cache_creation=20_000, cache_read=200_000,
                tool_call_counts=[5],
            )
            _write_trial(job_dir, r1, t1)
            _write_trial(job_dir, r2, t2)

            meta = load_harbor_metrics(job_dir)
            self.assertEqual(500_000 + 2_000 + 300_000 + 1_000, meta.total_tokens)
            self.assertEqual(4 + 3 + 5, meta.tool_calls)
            self.assertAlmostEqual(300.0 + 600.0, meta.wall_seconds)

    def test_trial_with_null_tokens(self) -> None:
        """Trials with null token counts (e.g. tier0) should not break aggregation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            result = _make_trial_result(
                n_input_tokens=None, n_output_tokens=None, n_cache_tokens=None,
            )
            _write_trial(job_dir, result)

            meta = load_harbor_metrics(job_dir)
            self.assertIsNotNone(meta)
            self.assertEqual("claude-code", meta.agent)
            # No token data → tokens should be None
            self.assertIsNone(meta.total_tokens)
            # Wall time should still work
            self.assertAlmostEqual(600.0, meta.wall_seconds)


class TestLoadRunMetadataHarborPriority(unittest.TestCase):
    def test_harbor_preferred_over_metadata_json(self) -> None:
        """When both Harbor result.json and metadata.json exist, Harbor wins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            # Write Harbor trial
            result = _make_trial_result(n_input_tokens=2_000_000, n_output_tokens=10_000)
            _write_trial(job_dir, result)
            # Write legacy metadata.json with different values
            _write_metadata(
                job_dir / "metadata.json",
                agent="old-agent", model="old-model", total_tokens=999,
            )

            meta = load_run_metadata(job_dir)
            # Should get Harbor values, not metadata.json
            self.assertEqual("claude-code", meta.agent)
            self.assertEqual("claude-sonnet-4-6", meta.model)
            self.assertEqual(2_000_000 + 10_000, meta.total_tokens)

    def test_falls_back_to_metadata_json(self) -> None:
        """When no Harbor files exist, fall back to metadata.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            _write_metadata(
                job_dir / "metadata.json",
                agent="aider", model="gpt-4o", total_tokens=50000,
            )
            meta = load_run_metadata(job_dir)
            self.assertEqual("aider", meta.agent)
            self.assertEqual(50000, meta.total_tokens)


if __name__ == "__main__":
    unittest.main()
