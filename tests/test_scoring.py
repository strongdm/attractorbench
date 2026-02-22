import json
import tempfile
import unittest
from pathlib import Path

from attractorbench.scoring import compare_jobs, load_job_results


def _write_reward(path: Path, *, build: int, self_rate: float, conf_rate: float, composite: float) -> None:
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


class ScoringTests(unittest.TestCase):
    def test_load_job_results_infers_task_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            _write_reward(
                job_dir / "run-1" / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                build=1,
                self_rate=0.9,
                conf_rate=0.8,
                composite=0.83,
            )
            _write_reward(
                job_dir / "run-2" / "tier2-agent-loop" / "logs" / "verifier" / "reward.json",
                build=1,
                self_rate=0.7,
                conf_rate=0.6,
                composite=0.65,
            )

            results = load_job_results(job_dir)

            self.assertEqual({"tier1-unified-llm", "tier2-agent-loop"}, set(results.keys()))

    def test_load_job_results_deduplicates_same_task_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir)
            _write_reward(
                job_dir / "attempt-a" / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                build=1,
                self_rate=1.0,
                conf_rate=1.0,
                composite=1.0,
            )
            _write_reward(
                job_dir / "attempt-b" / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                build=0,
                self_rate=0.1,
                conf_rate=0.2,
                composite=0.2,
            )

            results = load_job_results(job_dir)

            self.assertIn("tier1-unified-llm", results)
            self.assertIn("tier1-unified-llm#2", results)

    def test_compare_jobs_is_sorted_by_job_then_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_b = root / "job-b"
            job_a = root / "job-a"

            _write_reward(
                job_b / "tier2-agent-loop" / "logs" / "verifier" / "reward.json",
                build=1,
                self_rate=0.8,
                conf_rate=0.8,
                composite=0.8,
            )
            _write_reward(
                job_a / "tier1-unified-llm" / "logs" / "verifier" / "reward.json",
                build=1,
                self_rate=0.9,
                conf_rate=0.9,
                composite=0.9,
            )

            rows = compare_jobs([job_b, job_a])

            self.assertEqual("job-a", rows[0]["job"])
            self.assertEqual("tier1-unified-llm", rows[0]["task"])
            self.assertEqual("job-b", rows[1]["job"])
            self.assertEqual("tier2-agent-loop", rows[1]["task"])


if __name__ == "__main__":
    unittest.main()
