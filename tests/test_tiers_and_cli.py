import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from attractorbench.cli import app
from attractorbench.tiers import load_tiers


class TierLoadingTests(unittest.TestCase):
    def test_load_tiers_default_returns_all_tiers(self) -> None:
        tiers = load_tiers()
        self.assertEqual([0, 1, 2, 3], [tier.tier for tier in tiers])
        self.assertTrue(all(tier.total_items > 0 for tier in tiers))

    def test_load_tiers_rejects_unknown_tiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown tier"):
            load_tiers([4])

    def test_load_tiers_preserves_order_and_deduplicates(self) -> None:
        tiers = load_tiers([3, 1, 3])
        self.assertEqual([3, 1], [tier.tier for tier in tiers])


class CliTierValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_generate_rejects_non_numeric_tier_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.runner.invoke(app, ["generate", "--tiers", "abc", "--output-dir", tmpdir])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid tier value", result.output)

    def test_generate_rejects_unknown_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.runner.invoke(app, ["generate", "--tiers", "4", "--output-dir", tmpdir])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Unknown tier", result.output)

    def test_generate_accepts_valid_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "generated"
            result = self.runner.invoke(app, ["generate", "--tiers", "1", "--output-dir", str(out_dir)])

            self.assertEqual(result.exit_code, 0)
            self.assertTrue((out_dir / "tier1-unified-llm" / "task.toml").exists())


if __name__ == "__main__":
    unittest.main()
