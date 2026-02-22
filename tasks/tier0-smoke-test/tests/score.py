#!/usr/bin/env python3
"""In-container score aggregation for attractorbench.

Reads build/selftest/conformance results and produces reward.json.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def count_test_results(log_path: str) -> tuple[int, int]:
    """Parse a test log to estimate pass/total counts."""
    path = Path(log_path)
    if not path.exists():
        return 0, 0

    text = path.read_text()

    # pytest style: "X passed, Y failed"
    m = re.search(r"(\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", text)
    failed = int(m.group(1)) if m else 0

    # go test style: "ok" / "FAIL"
    ok_count = len(re.findall(r"^ok\s", text, re.MULTILINE))
    fail_count = len(re.findall(r"^FAIL\s", text, re.MULTILINE))
    if ok_count + fail_count > passed + failed:
        passed = ok_count
        failed = fail_count

    # npm test / jest: "Tests: X passed, Y failed"
    m = re.search(r"Tests:\s+(\d+)\s+passed", text)
    if m:
        passed = max(passed, int(m.group(1)))
    m = re.search(r"Tests:\s+.*?(\d+)\s+failed", text)
    if m:
        failed = max(failed, int(m.group(1)))

    total = passed + failed
    return passed, max(total, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-exit", type=int, required=True)
    parser.add_argument("--selftest-exit", type=int, required=True)
    parser.add_argument("--conformance-exit", type=int, required=True)
    parser.add_argument("--selftest-log", type=str, default="")
    parser.add_argument("--conformance", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    build_success = 1 if args.build_exit == 0 else 0

    # Self-test
    self_passed, self_total = 0, 0
    if args.selftest_exit == 0:
        self_passed, self_total = count_test_results(args.selftest_log)
        if self_total == 0:
            self_passed, self_total = 1, 1  # build+test passed, count as 1/1
    elif args.selftest_log:
        self_passed, self_total = count_test_results(args.selftest_log)

    self_test_pass_rate = self_passed / max(self_total, 1)

    # Conformance
    conf_path = Path(args.conformance)
    conformance_results = {}
    if conf_path.exists():
        try:
            conformance_results = json.loads(conf_path.read_text())
        except (json.JSONDecodeError, ValueError):
            pass

    tests = conformance_results.get("tests", [])
    conf_total = len(tests)
    conf_passed = sum(1 for t in tests if t.get("passed", False))
    conf_pass_rate = conf_passed / max(conf_total, 1)

    # DoD section scores from conformance
    dod_scores = {}
    sections = conformance_results.get("sections", {})
    for section_key, section_data in sections.items():
        sec_total = section_data.get("total", 0)
        sec_passed = section_data.get("passed", 0)
        dod_scores[f"dod_{section_key}"] = sec_passed / max(sec_total, 1)

    # Composite score: weighted average
    # 10% build, 20% self-test, 70% conformance
    composite = (
        0.10 * build_success
        + 0.20 * self_test_pass_rate
        + 0.70 * conf_pass_rate
    )

    reward = {
        "build_success": build_success,
        "self_test_pass_rate": round(self_test_pass_rate, 4),
        "self_test_count": self_total,
        "conformance_exit": args.conformance_exit,
        "conformance_total": conf_total,
        "conformance_passed": conf_passed,
        "conformance_pass_rate": round(conf_pass_rate, 4),
        **{k: round(v, 4) for k, v in dod_scores.items()},
        "composite_score": round(composite, 4),
    }

    Path(args.output).write_text(json.dumps(reward, indent=2))
    print(json.dumps(reward, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
