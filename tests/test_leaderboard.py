import json
import tempfile
import unittest
from pathlib import Path

from attractorbench.leaderboard import (
    build_leaderboard,
    fmt_cost,
    fmt_time,
    fmt_tokens,
    fmt_ratio,
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
            # Header + separator + at least one data row
            self.assertGreaterEqual(len(lines), 3)
            # All lines start with |
            for line in lines:
                self.assertTrue(line.startswith("|"))
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


if __name__ == "__main__":
    unittest.main()
