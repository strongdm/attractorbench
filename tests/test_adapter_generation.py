import unittest

from attractorbench.adapter import generate_run_conformance, generate_test_sh
from attractorbench.tiers import TierDef


class AdapterGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tier = TierDef(
            tier=1,
            name="Unified LLM SDK",
            slug="tier1-unified-llm",
            spec_file="unified-llm-spec.md",
            dod_section_number="8",
            agent_timeout=1800,
            verifier_timeout=600,
            sections=[],
        )

    def test_test_sh_tracks_conformance_exit_and_cleanup(self) -> None:
        script = generate_test_sh(self.tier)
        self.assertIn("trap cleanup EXIT", script)
        self.assertIn("CONFORMANCE_EXIT=$?", script)
        self.assertIn("--conformance-exit $CONFORMANCE_EXIT", script)

    def test_run_conformance_uses_safe_boolean_precedence(self) -> None:
        script = generate_run_conformance()
        self.assertIn(
            't.passed = code == 0 and ("text" in resp or "content" in resp or "output" in resp)',
            script,
        )


if __name__ == "__main__":
    unittest.main()
