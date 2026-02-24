import unittest

from attractorbench.adapter import (
    generate_docker_compose,
    generate_dockerfile,
    generate_fullstack_score_py,
    generate_harvest_litellm,
    generate_instruction,
    generate_litellm_config,
    generate_llm_judge_py,
    generate_mock_server,
    generate_run_conformance,
    generate_score_py,
    generate_fullstack_test_sh,
    generate_task_toml,
    generate_test_sh,
)
from attractorbench.tiers import load_fullstack_tier
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
        self.assertIn("--suite full", script)

    def test_instruction_has_recommended_loop(self) -> None:
        instruction = generate_instruction(self.tier)
        self.assertIn("Recommended Loop", instruction)
        self.assertIn("--suite quick", instruction)
        self.assertIn("/logs/verifier/conformance_results.json", instruction)

    # --- Mock server tests ---

    def test_mock_server_has_request_log(self) -> None:
        server = generate_mock_server()
        self.assertIn("REQUEST_LOG", server)
        self.assertIn("_log_request", server)

    def test_mock_server_has_requests_endpoint(self) -> None:
        server = generate_mock_server()
        self.assertIn('"/requests"', server)
        self.assertIn('"/requests/reset"', server)

    def test_mock_server_logs_get_and_post(self) -> None:
        server = generate_mock_server()
        # Both do_GET and do_POST should call _log_request
        self.assertIn("def do_GET(self):", server)
        self.assertIn("def do_POST(self):", server)
        # _log_request should be called in both methods
        lines = server.split("\n")
        in_get = False
        in_post = False
        get_logs = False
        post_logs = False
        for line in lines:
            if "def do_GET" in line:
                in_get = True
                in_post = False
            elif "def do_POST" in line:
                in_post = True
                in_get = False
            elif line.strip().startswith("def ") and "do_GET" not in line and "do_POST" not in line:
                in_get = False
                in_post = False
            if in_get and "_log_request" in line:
                get_logs = True
            if in_post and "_log_request" in line:
                post_logs = True
        self.assertTrue(get_logs, "do_GET should call _log_request")
        self.assertTrue(post_logs, "do_POST should call _log_request")

    # --- Conformance runner tests ---

    def test_conformance_runner_has_assert_mock_called(self) -> None:
        runner = generate_run_conformance()
        self.assertIn("def assert_mock_called(", runner)
        self.assertIn("def get_mock_requests(", runner)
        self.assertIn("def reset_mock_requests(", runner)

    def test_conformance_runner_has_schema_validation(self) -> None:
        runner = generate_run_conformance()
        # Check that tests verify specific fields, not just "is a dict"
        self.assertIn('"id" in resp', runner)
        self.assertIn('"output" in resp', runner)

    def test_conformance_runner_uses_mock_assertions(self) -> None:
        runner = generate_run_conformance()
        self.assertIn("assert_mock_called(", runner)
        self.assertIn("reset_mock_requests()", runner)

    def test_conformance_runner_has_suite_arg(self) -> None:
        runner = generate_run_conformance()
        self.assertIn('parser.add_argument("--suite"', runner)
        self.assertIn("SUITES_BY_TIER", runner)
        self.assertIn("tier1_quick_tests", runner)

    def test_conformance_runner_has_runtime_cache(self) -> None:
        runner = generate_run_conformance()
        self.assertIn("RUN_CMD_CACHE", runner)
        self.assertIn("hashlib.sha1", runner)

    def test_conformance_runner_has_atomic_stream_checks(self) -> None:
        runner = generate_run_conformance()
        self.assertIn("stream_exit_zero", runner)
        self.assertIn("stream_lines_are_json", runner)

    # --- Score.py tests ---

    def test_score_py_has_min_self_tests(self) -> None:
        score = generate_score_py()
        self.assertIn("MIN_SELF_TESTS", score)

    def test_score_py_zero_tests_zero_credit(self) -> None:
        score = generate_score_py()
        # Verify the anti-gaming fix: zero tests = 0/1, not 1/1
        self.assertIn("self_passed, self_total = 0, 1", score)
        self.assertNotIn("self_passed, self_total = 1, 1", score)

    def test_score_py_detects_test_runner(self) -> None:
        score = generate_score_py()
        self.assertIn("def detect_test_runner(", score)
        self.assertIn("TEST_RUNNER_PATTERNS", score)

    def test_score_py_has_coverage_penalty(self) -> None:
        score = generate_score_py()
        self.assertIn("coverage_factor", score)
        self.assertIn("self_total / MIN_SELF_TESTS", score)

    def test_score_py_new_weights(self) -> None:
        score = generate_score_py()
        # New weights: 10% build, 10% self-test, 80% conformance
        self.assertIn("0.10 * build_success", score)
        self.assertIn("0.10 * self_test_pass_rate", score)
        self.assertIn("0.80 * conf_pass_rate", score)
        # Should NOT have old 20%/70% weights
        self.assertNotIn("0.20 * self_test_pass_rate", score)
        self.assertNotIn("0.70 * conf_pass_rate", score)


    # --- LiteLLM sidecar tests ---

    def test_docker_compose_has_litellm_service(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("litellm:", compose)
        self.assertIn("ghcr.io/berriai/litellm:main-latest", compose)

    def test_docker_compose_has_depends_on(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("depends_on:", compose)
        self.assertIn("condition: service_healthy", compose)

    def test_docker_compose_has_healthcheck(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("healthcheck:", compose)
        self.assertIn("localhost:4000/health", compose)

    def test_docker_compose_has_volume_mount(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("litellm-logs:/logs/litellm", compose)

    def test_docker_compose_has_api_key_env_vars(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("OPENAI_API_KEY=${OPENAI_API_KEY:-}", compose)
        self.assertIn("ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}", compose)
        self.assertIn("GEMINI_API_KEY=${GEMINI_API_KEY:-}", compose)

    def test_docker_compose_has_base_url_env_vars(self) -> None:
        compose = generate_docker_compose()
        self.assertIn("OPENAI_BASE_URL=http://litellm:4000/v1", compose)
        self.assertIn("ANTHROPIC_BASE_URL=http://litellm:4000/anthropic", compose)
        self.assertIn("GOOGLE_GEMINI_BASE_URL=http://litellm:4000/gemini", compose)

    def test_litellm_config_has_wildcard_model(self) -> None:
        config = generate_litellm_config()
        self.assertIn('model_name: "*"', config)
        self.assertIn('model: "*"', config)

    def test_litellm_config_has_json_logs(self) -> None:
        config = generate_litellm_config()
        self.assertIn("json_logs: true", config)

    def test_harvest_litellm_reads_proxy_log(self) -> None:
        script = generate_harvest_litellm()
        self.assertIn("/logs/litellm/proxy.log", script)

    def test_harvest_litellm_writes_metadata(self) -> None:
        script = generate_harvest_litellm()
        self.assertIn("/logs/verifier/metadata.json", script)

    def test_harvest_litellm_aggregates_tokens(self) -> None:
        script = generate_harvest_litellm()
        self.assertIn("total_tokens", script)
        self.assertIn("prompt_tokens", script)
        self.assertIn("completion_tokens", script)

    def test_test_sh_has_harvest_step(self) -> None:
        script = generate_test_sh(self.tier)
        # Harvest should appear before Phase 1 Build
        harvest_pos = script.find("Phase 0: Harvest LiteLLM")
        build_pos = script.find("Phase 1: Build")
        self.assertGreater(harvest_pos, -1, "Phase 0 harvest not found in test.sh")
        self.assertGreater(build_pos, harvest_pos, "Harvest must come before Build")
        self.assertIn("harvest_litellm.py", script)

    def test_task_toml_allows_internet(self) -> None:
        toml = generate_task_toml(self.tier)
        self.assertIn("allow_internet = true", toml)
        self.assertNotIn("allow_internet = false", toml)

    def test_dockerfile_has_tests_dir(self) -> None:
        dockerfile = generate_dockerfile(self.tier)
        self.assertIn("/tests", dockerfile)
        self.assertIn("COPY starter/ /workspace/", dockerfile)
        # Harbor uploads tests at verify time - no COPY needed
        self.assertNotIn("COPY tests/", dockerfile)

    def test_fullstack_test_sh_uses_full_suite(self) -> None:
        fullstack = load_fullstack_tier()
        script = generate_fullstack_test_sh(fullstack)
        self.assertIn("--tier 1", script)
        self.assertIn("--suite full", script)

    # --- Gate removal tests ---

    def test_fullstack_test_sh_no_gate(self) -> None:
        fullstack = load_fullstack_tier()
        script = generate_fullstack_test_sh(fullstack)
        self.assertNotIn("T2_CAN_ADVANCE", script)
        self.assertNotIn("skipped_due_to_tier2", script)
        # T3 runs unconditionally
        self.assertIn("Phase 3c: Tier 3 Conformance", script)
        self.assertIn("--tier 3", script)

    # --- LLM Judge tests ---

    def test_fullstack_test_sh_has_phase4_judge(self) -> None:
        fullstack = load_fullstack_tier()
        script = generate_fullstack_test_sh(fullstack)
        self.assertIn("Phase 4: LLM Judge", script)
        self.assertIn("llm_judge.py", script)
        self.assertIn("JUDGE_MODEL", script)
        self.assertIn("non-fatal", script)

    def test_fullstack_test_sh_passes_llm_judge_to_score(self) -> None:
        fullstack = load_fullstack_tier()
        script = generate_fullstack_test_sh(fullstack)
        self.assertIn("--llm-judge", script)
        self.assertIn("LLM_JUDGE_FLAG", script)

    def test_llm_judge_py_has_dimensions(self) -> None:
        judge = generate_llm_judge_py()
        self.assertIn("spec_coverage", judge)
        self.assertIn("architectural_compliance", judge)
        self.assertIn("error_handling", judge)
        self.assertIn("test_quality", judge)
        self.assertIn("code_quality", judge)

    def test_llm_judge_py_has_variance_control(self) -> None:
        judge = generate_llm_judge_py()
        self.assertIn("CALLS_PER_DIMENSION = 3", judge)
        self.assertIn("GLOBAL_BUDGET", judge)
        self.assertIn("stddev", judge)

    def test_llm_judge_py_has_json_response_format(self) -> None:
        judge = generate_llm_judge_py()
        self.assertIn("json_object", judge)
        self.assertIn("temperature", judge)

    def test_llm_judge_py_uses_urllib(self) -> None:
        judge = generate_llm_judge_py()
        self.assertIn("import urllib.request", judge)
        self.assertNotIn("import requests", judge)
        self.assertNotIn("import openai", judge)

    # --- Updated score formula tests ---

    def test_fullstack_score_py_has_judge_arg(self) -> None:
        score = generate_fullstack_score_py()
        self.assertIn("--llm-judge", score)

    def test_fullstack_score_py_has_judge_formula(self) -> None:
        score = generate_fullstack_score_py()
        self.assertIn("0.25 * t1_rate", score)
        self.assertIn("0.25 * t2_rate", score)
        self.assertIn("0.25 * t3_rate", score)
        self.assertIn("0.15 * judge_score", score)

    def test_fullstack_score_py_has_fallback_formula(self) -> None:
        score = generate_fullstack_score_py()
        # Fallback (no judge) should use 30/30/30
        self.assertIn("0.30 * t1_rate", score)
        self.assertIn("0.30 * t2_rate", score)
        self.assertIn("0.30 * t3_rate", score)

    def test_fullstack_score_py_writes_judge_fields(self) -> None:
        score = generate_fullstack_score_py()
        self.assertIn("llm_judge_score", score)
        self.assertIn("llm_judge_stddev", score)
        self.assertIn("llm_judge_model", score)


if __name__ == "__main__":
    unittest.main()
