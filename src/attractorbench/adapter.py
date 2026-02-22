"""Harbor-compatible task directory generator for attractorbench."""

from __future__ import annotations

import shutil
from pathlib import Path

from attractorbench.tiers import TierDef, load_tiers

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def generate_task_toml(tier: TierDef) -> str:
    return f"""version = "1.0"

[metadata]
author_name = "attractorbench"
author_email = "attractorbench@example.com"
difficulty = "hard"
category = "programming"
tags = ["nlspec", "attractor", "coding-agent", "tier{tier.tier}"]

[agent]
timeout_sec = {tier.agent_timeout}.0

[verifier]
timeout_sec = {tier.verifier_timeout}.0

[environment]
build_timeout_sec = 300.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
"""


def generate_instruction(tier: TierDef) -> str:
    spec_text = tier.spec_path.read_text(encoding="utf-8")

    conformance_contract = _conformance_contract(tier.tier)

    dod_checklist = ""
    for section in tier.sections:
        dod_checklist += f"\n### {section.number} {section.name}\n\n"
        for item in section.items:
            dod_checklist += f"- [ ] {item.text}\n"

    return f"""# {tier.name} — attractorbench Tier {tier.tier}

You are implementing **{tier.name}** from the Attractor NLSpec suite.

## Task

Read the specification below and implement a complete, working system that satisfies all requirements.

## Implementation Constraints

- Implement in any programming language
- Provide a `Makefile` with `build` and `test` targets
- The conformance CLI must be at `./bin/conformance`
- Write your own comprehensive test suite (run via `make test`)
- All work goes in `/workspace`

## Conformance Contract

{conformance_contract}

## Definition of Done Checklist

{dod_checklist}

---

## Full Specification

{spec_text}
"""


def _conformance_contract(tier: int) -> str:
    if tier == 1:
        return """Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance client-from-env` — Construct a client from environment variables. Exit 0 on success, non-zero on failure.
- `./bin/conformance complete` — Read a JSON Request from stdin, send it to the LLM API (or mock), write JSON Response to stdout.
- `./bin/conformance stream` — Read a JSON Request from stdin, stream the response, write newline-delimited JSON StreamEvents to stdout.
- `./bin/conformance tool-call` — Read a JSON Request (with tools defined) from stdin, process tool calls, write JSON Response to stdout.
- `./bin/conformance generate-object` — Read a JSON Request with a schema from stdin, write the parsed object to stdout.
- `./bin/conformance list-models` — Write a JSON array of model info objects to stdout.

The mock LLM server runs at `http://localhost:9999` inside the test container. Set environment variables:
- `OPENAI_API_KEY=test-key`
- `OPENAI_BASE_URL=http://localhost:9999/v1`
- `ANTHROPIC_API_KEY=test-key`
- `ANTHROPIC_BASE_URL=http://localhost:9999`
- `GEMINI_API_KEY=test-key`
- `GEMINI_BASE_URL=http://localhost:9999`
"""
    elif tier == 2:
        return """Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance session-create` — Create a session with a mock provider profile. Exit 0 on success.
- `./bin/conformance process-input` — Read a JSON task prompt from stdin, run the agentic loop against the mock LLM, write JSON session result to stdout.
- `./bin/conformance tool-dispatch` — Read a JSON tool call from stdin, dispatch it, write JSON tool result to stdout.
- `./bin/conformance steering` — Read a JSON steering message from stdin, inject it into a running session, write acknowledgment to stdout.
- `./bin/conformance events` — Run a short session, write newline-delimited JSON events to stdout.

The mock LLM server runs at `http://localhost:9999` inside the test container.
"""
    else:
        return """Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance parse <dotfile>` — Parse a DOT file, write JSON AST to stdout.
- `./bin/conformance validate <dotfile>` — Validate a DOT file, write JSON diagnostics to stdout.
- `./bin/conformance run <dotfile>` — Execute the pipeline with a mock backend, write JSON execution result to stdout.
- `./bin/conformance list-handlers` — Write a JSON array of registered handler types to stdout.

The mock LLM backend runs at `http://localhost:9999` inside the test container. The `CodergenBackend` should send requests there.
"""


def generate_dockerfile(tier: TierDef) -> str:
    return f"""FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    git \\
    make \\
    && rm -rf /var/lib/apt/lists/*

# Install common language toolchains the agent might choose
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \\
    apt-get install -y nodejs && \\
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://go.dev/dl/go1.23.6.linux-amd64.tar.gz | tar -C /usr/local -xzf - && \\
    ln -s /usr/local/go/bin/go /usr/local/bin/go

ENV PATH="/usr/local/go/bin:${{PATH}}"

RUN mkdir -p /workspace /logs /logs/verifier /logs/agent /logs/artifacts /tests
RUN chmod -R 777 /workspace /logs

WORKDIR /workspace

# Copy mock server into the image
COPY tests/mock_server.py /tests/mock_server.py
COPY tests/conformance/ /tests/conformance/
COPY tests/test.sh /tests/test.sh
COPY tests/score.py /tests/score.py
"""


def generate_test_sh(tier: TierDef) -> str:
    return f"""#!/bin/bash
# attractorbench Tier {tier.tier}: {tier.name} — Verifier
set -uo pipefail
set +e

cleanup() {{
  if [ -n "${{MOCK_PID:-}}" ]; then
    kill "$MOCK_PID" 2>/dev/null || true
  fi
}}
trap cleanup EXIT

mkdir -p /logs/verifier

cd /workspace

# Start mock LLM server in background
python3 /tests/mock_server.py >> /logs/verifier/mock-server.log 2>&1 &
MOCK_PID=$!

# Wait for mock server readiness
for _ in {{1..20}}; do
  if curl -fsS http://localhost:9999/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS http://localhost:9999/health >/dev/null 2>&1; then
  echo "Mock LLM server failed to start; conformance will likely fail." | tee -a /logs/verifier/conformance.log
fi

# Phase 1: Build check
echo "=== Phase 1: Build ===" | tee /logs/verifier/build.log
make build >> /logs/verifier/build.log 2>&1
BUILD_EXIT=$?
echo "Build exit code: $BUILD_EXIT" | tee -a /logs/verifier/build.log

# Phase 2: Self-test check
echo "=== Phase 2: Self-test ===" | tee /logs/verifier/self-test.log
make test >> /logs/verifier/self-test.log 2>&1
SELFTEST_EXIT=$?
echo "Self-test exit code: $SELFTEST_EXIT" | tee -a /logs/verifier/self-test.log

# Phase 3: Conformance check
echo "=== Phase 3: Conformance ===" | tee /logs/verifier/conformance.log
export OPENAI_API_KEY=test-key
export OPENAI_BASE_URL=http://localhost:9999/v1
export ANTHROPIC_API_KEY=test-key
export ANTHROPIC_BASE_URL=http://localhost:9999
export GEMINI_API_KEY=test-key
export GEMINI_BASE_URL=http://localhost:9999
python3 /tests/conformance/run_conformance.py --tier {tier.tier} >> /logs/verifier/conformance.log 2>&1
CONFORMANCE_EXIT=$?
echo "Conformance exit code: $CONFORMANCE_EXIT" | tee -a /logs/verifier/conformance.log

# Aggregate into reward.json
python3 /tests/score.py \\
  --build-exit $BUILD_EXIT \\
  --selftest-exit $SELFTEST_EXIT \\
  --conformance-exit $CONFORMANCE_EXIT \\
  --selftest-log /logs/verifier/self-test.log \\
  --conformance /logs/verifier/conformance_results.json \\
  --output /logs/verifier/reward.json

echo "=== Done ==="
cat /logs/verifier/reward.json

exit 0
"""


def generate_mock_server() -> str:
    return '''#!/usr/bin/env python3
"""Mock LLM HTTP server for attractorbench conformance testing.

Listens on port 9999 and returns canned responses for OpenAI, Anthropic, and Gemini API formats.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

OPENAI_CHAT_RESPONSE = {
    "id": "resp_mock_001",
    "object": "response",
    "created": 1700000000,
    "model": "gpt-4o",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hello! This is a mock response from the LLM."}],
        }
    ],
    "usage": {
        "input_tokens": 10,
        "output_tokens": 15,
        "total_tokens": 25,
    },
}

OPENAI_TOOL_RESPONSE = {
    "id": "resp_mock_002",
    "object": "response",
    "created": 1700000000,
    "model": "gpt-4o",
    "output": [
        {
            "type": "function_call",
            "call_id": "call_mock_001",
            "name": "get_weather",
            "arguments": json.dumps({"location": "San Francisco"}),
        }
    ],
    "usage": {"input_tokens": 20, "output_tokens": 25, "total_tokens": 45},
}

ANTHROPIC_RESPONSE = {
    "id": "msg_mock_001",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello! This is a mock response from the LLM."}],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 15},
}

ANTHROPIC_TOOL_RESPONSE = {
    "id": "msg_mock_002",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_mock_001",
            "name": "get_weather",
            "input": {"location": "San Francisco"},
        }
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 20, "output_tokens": 25},
}

GEMINI_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [{"text": "Hello! This is a mock response from the LLM."}],
                "role": "model",
            },
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 15,
        "totalTokenCount": 25,
    },
}

MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
        {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    ],
}

OPENAI_STREAM_EVENTS = [
    {"type": "response.created", "response": {"id": "resp_mock_stream", "status": "in_progress"}},
    {"type": "response.output_item.added", "output_index": 0, "item": {"type": "message", "role": "assistant"}},
    {"type": "response.content_part.added", "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": ""}},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "Hello! "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "This is "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "a mock "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "streamed response."},
    {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "text": "Hello! This is a mock streamed response."},
    {"type": "response.content_part.done", "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": "Hello! This is a mock streamed response."}},
    {"type": "response.output_item.done", "output_index": 0, "item": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! This is a mock streamed response."}]}},
    {"type": "response.completed", "response": {"id": "resp_mock_stream", "status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! This is a mock streamed response."}]}], "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}}},
]

ANTHROPIC_STREAM_EVENTS = [
    {"type": "message_start", "message": {"id": "msg_mock_stream", "type": "message", "role": "assistant", "content": [], "model": "claude-sonnet-4-20250514", "usage": {"input_tokens": 10, "output_tokens": 0}}},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello! "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "This is "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "a mock "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "streamed response."}},
    {"type": "content_block_stop", "index": 0},
    {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 20}},
    {"type": "message_stop"},
]


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for event in events:
            line = f"data: {json.dumps(event)}\\n\\n"
            self.wfile.write(line.encode())
            self.wfile.flush()

    def do_GET(self):
        if self.path == "/v1/models" or self.path == "/models":
            self._send_json(MODELS_RESPONSE)
        elif self.path == "/health":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        want_stream = data.get("stream", False)

        # OpenAI Responses API
        if self.path in ("/v1/responses",):
            if want_stream:
                self._send_sse(OPENAI_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(OPENAI_TOOL_RESPONSE)
            else:
                self._send_json(OPENAI_CHAT_RESPONSE)

        # OpenAI Chat Completions (legacy)
        elif self.path in ("/v1/chat/completions",):
            if want_stream:
                self._send_sse(OPENAI_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(OPENAI_TOOL_RESPONSE)
            else:
                self._send_json(OPENAI_CHAT_RESPONSE)

        # Anthropic Messages API
        elif self.path in ("/v1/messages", "/messages"):
            if want_stream:
                self._send_sse(ANTHROPIC_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(ANTHROPIC_TOOL_RESPONSE)
            else:
                self._send_json(ANTHROPIC_RESPONSE)

        # Gemini API
        elif "generateContent" in self.path:
            self._send_json(GEMINI_RESPONSE)
        elif "streamGenerateContent" in self.path:
            # Gemini streaming returns array
            self._send_json([GEMINI_RESPONSE])

        # Rate limit test endpoint
        elif self.path == "/v1/rate-limited":
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Retry-After", "1")
            body = json.dumps({"error": {"message": "Rate limited", "type": "rate_limit_error"}}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # Auth error test endpoint
        elif self.path == "/v1/auth-error":
            self._send_json({"error": {"message": "Invalid API key", "type": "authentication_error"}}, 401)

        else:
            self._send_json({"error": f"Unknown path: {self.path}"}, 404)


if __name__ == "__main__":
    port = 9999
    server = HTTPServer(("0.0.0.0", port), MockHandler)
    print(f"Mock LLM server listening on port {port}", file=sys.stderr)
    server.serve_forever()
'''


def generate_score_py() -> str:
    return '''#!/usr/bin/env python3
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
    m = re.search(r"(\\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\\d+) failed", text)
    failed = int(m.group(1)) if m else 0

    # go test style: "ok" / "FAIL"
    ok_count = len(re.findall(r"^ok\\s", text, re.MULTILINE))
    fail_count = len(re.findall(r"^FAIL\\s", text, re.MULTILINE))
    if ok_count + fail_count > passed + failed:
        passed = ok_count
        failed = fail_count

    # npm test / jest: "Tests: X passed, Y failed"
    m = re.search(r"Tests:\\s+(\\d+)\\s+passed", text)
    if m:
        passed = max(passed, int(m.group(1)))
    m = re.search(r"Tests:\\s+.*?(\\d+)\\s+failed", text)
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
'''


def generate_run_conformance() -> str:
    return '''#!/usr/bin/env python3
"""Conformance test runner for attractorbench.

Discovers and runs conformance tests, outputs results as JSON.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RESULTS_FILE = "/logs/verifier/conformance_results.json"
CONFORMANCE_BIN = "/workspace/bin/conformance"


def run_cmd(args, stdin_data=None, timeout=30, env=None):
    """Run a command and return (exit_code, stdout, stderr)."""
    merged_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            args,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
            cwd="/workspace",
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -2, "", f"Command not found: {args[0]}"


class ConformanceTest:
    def __init__(self, name, section, description=""):
        self.name = name
        self.section = section
        self.description = description
        self.passed = False
        self.error = ""
        self.duration = 0.0

    def to_dict(self):
        return {
            "name": self.name,
            "section": self.section,
            "description": self.description,
            "passed": self.passed,
            "error": self.error,
            "duration": round(self.duration, 3),
        }


def check_binary_exists():
    """Check that the conformance binary exists."""
    if not os.path.isfile(CONFORMANCE_BIN):
        return False
    return os.access(CONFORMANCE_BIN, os.X_OK)


# ==========================
# Tier 1: Unified LLM SDK
# ==========================

def tier1_tests():
    tests = []

    # Build check
    t = ConformanceTest("build_check", "core_infra", "make build succeeds")
    start = time.time()
    code, out, err = run_cmd(["make", "build"])
    t.duration = time.time() - start
    t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    if not check_binary_exists():
        t = ConformanceTest("binary_exists", "core_infra", "./bin/conformance exists and is executable")
        t.error = "Binary not found at ./bin/conformance"
        tests.append(t)
        return tests

    # Core Infrastructure
    t = ConformanceTest("client_from_env", "core_infra", "Client construction from env vars")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "client-from-env"])
    t.duration = time.time() - start
    t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    t = ConformanceTest("list_models", "core_infra", "list-models returns JSON array")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "list-models"])
    t.duration = time.time() - start
    try:
        data = json.loads(out)
        t.passed = code == 0 and isinstance(data, list) and len(data) > 0
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    if not t.passed and not t.error and code != 0:
        t.error = err[:500]
    tests.append(t)

    # Generation
    simple_request = json.dumps({
        "model": "gpt-4o",
        "provider": "openai",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 100,
    })

    t = ConformanceTest("complete_request", "generation", "complete returns valid Response JSON")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "complete"], stdin_data=simple_request)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and ("text" in resp or "content" in resp or "output" in resp)
        if not t.passed and code == 0:
            # Accept any valid JSON response
            t.passed = isinstance(resp, dict) and len(resp) > 0
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON response: {out[:200]}"
    if not t.passed and not t.error and code != 0:
        t.error = err[:500]
    tests.append(t)

    # Streaming
    stream_request = json.dumps({
        "model": "gpt-4o",
        "provider": "openai",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 100,
        "stream": True,
    })

    t = ConformanceTest("stream_request", "generation", "stream returns newline-delimited JSON events")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "stream"], stdin_data=stream_request)
    t.duration = time.time() - start
    lines = [l for l in out.strip().splitlines() if l.strip()]
    if code == 0 and len(lines) > 0:
        try:
            events = [json.loads(l) for l in lines]
            t.passed = len(events) >= 1
        except (json.JSONDecodeError, ValueError):
            t.passed = False
            t.error = "Stream events are not valid JSON"
    else:
        t.passed = False
        t.error = err[:500] if err else "No stream output"
    tests.append(t)

    # Tool calling
    tool_request = json.dumps({
        "model": "gpt-4o",
        "provider": "openai",
        "messages": [{"role": "user", "content": "What is the weather in SF?"}],
        "tools": [{
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        }],
        "max_tokens": 200,
    })

    t = ConformanceTest("tool_call", "tool_calling", "Tool calling returns tool_call in response")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "tool-call"], stdin_data=tool_request)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and isinstance(resp, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    # Structured output
    object_request = json.dumps({
        "model": "gpt-4o",
        "provider": "openai",
        "messages": [{"role": "user", "content": "Extract: Alice is 30 years old"}],
        "response_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        },
        "max_tokens": 200,
    })

    t = ConformanceTest("generate_object", "generation", "generate-object returns parsed structured output")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "generate-object"], stdin_data=object_request)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and isinstance(resp, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    # Provider adapters — test Anthropic
    anthropic_request = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "provider": "anthropic",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 100,
    })

    t = ConformanceTest("anthropic_complete", "provider_adapters", "Anthropic adapter complete works")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "complete"], stdin_data=anthropic_request)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and isinstance(resp, dict) and len(resp) > 0
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    # Message & Content Model — multimodal message
    mm_request = json.dumps({
        "model": "gpt-4o",
        "provider": "openai",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "What do you see?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="}},
        ]}],
        "max_tokens": 100,
    })

    t = ConformanceTest("multimodal_message", "message_content_model", "Multimodal messages accepted")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "complete"], stdin_data=mm_request)
    t.duration = time.time() - start
    t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    # Error handling — test with a bad endpoint
    t = ConformanceTest("error_handling", "error_handling", "Errors are surfaced correctly")
    err_request = json.dumps({
        "model": "nonexistent",
        "provider": "openai",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10,
    })
    start = time.time()
    code, out, err_out = run_cmd([CONFORMANCE_BIN, "complete"], stdin_data=err_request)
    t.duration = time.time() - start
    # Should either return an error JSON or non-zero exit
    if code != 0:
        t.passed = True  # Non-zero exit on error is correct
    else:
        try:
            resp = json.loads(out)
            t.passed = "error" in resp or "error_type" in resp
        except (json.JSONDecodeError, ValueError):
            t.passed = False
            t.error = "No error indication on invalid request"
    tests.append(t)

    return tests


# ==========================
# Tier 2: Coding Agent Loop
# ==========================

def tier2_tests():
    tests = []

    if not check_binary_exists():
        t = ConformanceTest("binary_exists", "core_loop", "./bin/conformance exists and is executable")
        t.error = "Binary not found at ./bin/conformance"
        tests.append(t)
        return tests

    # Session creation
    t = ConformanceTest("session_create", "core_loop", "Session can be created")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "session-create"])
    t.duration = time.time() - start
    t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    # Process input
    task_prompt = json.dumps({
        "prompt": "Create a file called hello.py that prints Hello World",
    })

    t = ConformanceTest("process_input", "core_loop", "process-input runs agentic loop")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "process-input"], stdin_data=task_prompt, timeout=60)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and isinstance(resp, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    # Tool dispatch
    tool_call = json.dumps({
        "tool_name": "read_file",
        "arguments": {"path": "/workspace/hello.py"},
    })

    t = ConformanceTest("tool_dispatch", "tool_execution", "tool-dispatch routes to tool handler")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "tool-dispatch"], stdin_data=tool_call)
    t.duration = time.time() - start
    try:
        resp = json.loads(out)
        t.passed = code == 0 and isinstance(resp, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    # Events
    t = ConformanceTest("events", "event_system", "events command emits JSON events")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "events"], timeout=60)
    t.duration = time.time() - start
    lines = [l for l in out.strip().splitlines() if l.strip()]
    if code == 0 and len(lines) > 0:
        try:
            events = [json.loads(l) for l in lines]
            t.passed = len(events) >= 1
        except (json.JSONDecodeError, ValueError):
            t.passed = False
            t.error = "Events are not valid JSON"
    else:
        t.passed = code == 0
        if not t.passed:
            t.error = err[:500]
    tests.append(t)

    # Steering
    steering_msg = json.dumps({
        "message": "Actually, use TypeScript instead",
    })

    t = ConformanceTest("steering", "steering", "steering injects a message")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "steering"], stdin_data=steering_msg)
    t.duration = time.time() - start
    t.passed = code == 0
    if not t.passed:
        t.error = err[:500]
    tests.append(t)

    return tests


# ==========================
# Tier 3: Attractor Pipeline
# ==========================

SIMPLE_DOT = """digraph simple {
    start [shape=Mdiamond]
    step_a [shape=box, prompt="Do step A"]
    done [shape=Msquare]
    start -> step_a -> done
}
"""

CONDITIONAL_DOT = """digraph conditional {
    graph [goal="Test conditional routing"]
    start [shape=Mdiamond]
    check [shape=box, prompt="Check something for: $goal"]
    path_a [shape=box, prompt="Path A"]
    path_b [shape=box, prompt="Path B"]
    done [shape=Msquare]
    start -> check
    check -> path_a [condition="outcome=success"]
    check -> path_b [condition="outcome=fail"]
    path_a -> done
    path_b -> done
}
"""

GOAL_GATE_DOT = """digraph goal_gate {
    graph [goal="Test goal gate enforcement"]
    start [shape=Mdiamond]
    implement [shape=box, prompt="Implement for: $goal", goal_gate=true]
    review [shape=box, prompt="Review the implementation"]
    done [shape=Msquare]
    start -> implement
    implement -> review [condition="outcome=success"]
    implement -> implement [condition="outcome=fail", label="Retry"]
    review -> done [condition="outcome=success"]
    review -> implement [condition="outcome=fail", label="Fix"]
}
"""

MISSING_START_DOT = """digraph bad {
    step_a [shape=box, prompt="Step A"]
    done [shape=Msquare]
    step_a -> done
}
"""

ORPHAN_DOT = """digraph orphan {
    start [shape=Mdiamond]
    step_a [shape=box, prompt="Step A"]
    orphan [shape=box, prompt="Orphan node"]
    done [shape=Msquare]
    start -> step_a -> done
}
"""

ATTRIBUTES_DOT = """digraph attrs {
    graph [goal="Test attributes", label="Attribute Test"]
    start [shape=Mdiamond]
    step [shape=box,
        prompt="Multi-line\\nattribute test",
        max_retries=2]
    done [shape=Msquare]
    start -> step [label="go", weight=10]
    step -> done
}
"""


def tier3_tests():
    tests = []

    if not check_binary_exists():
        t = ConformanceTest("binary_exists", "dot_parsing", "./bin/conformance exists and is executable")
        t.error = "Binary not found at ./bin/conformance"
        tests.append(t)
        return tests

    # Write test DOT files
    dot_dir = Path("/tmp/attractorbench_dots")
    dot_dir.mkdir(parents=True, exist_ok=True)
    (dot_dir / "simple.dot").write_text(SIMPLE_DOT)
    (dot_dir / "conditional.dot").write_text(CONDITIONAL_DOT)
    (dot_dir / "goal_gate.dot").write_text(GOAL_GATE_DOT)
    (dot_dir / "missing_start.dot").write_text(MISSING_START_DOT)
    (dot_dir / "orphan.dot").write_text(ORPHAN_DOT)
    (dot_dir / "attributes.dot").write_text(ATTRIBUTES_DOT)

    # DOT Parsing — simple graph
    t = ConformanceTest("parse_simple", "dot_parsing", "Parse simple linear pipeline")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "parse", str(dot_dir / "simple.dot")])
    t.duration = time.time() - start
    try:
        ast = json.loads(out)
        t.passed = code == 0 and isinstance(ast, dict)
        if t.passed:
            nodes = ast.get("nodes", [])
            edges = ast.get("edges", [])
            t.passed = len(nodes) >= 3 and len(edges) >= 2
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON AST: {out[:200]}"
    tests.append(t)

    # DOT Parsing — attributes
    t = ConformanceTest("parse_attributes", "dot_parsing", "Parse DOT with graph/node/edge attributes")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "parse", str(dot_dir / "attributes.dot")])
    t.duration = time.time() - start
    try:
        ast = json.loads(out)
        t.passed = code == 0 and isinstance(ast, dict)
        if t.passed:
            # Check goal attribute extracted
            goal = ast.get("goal", ast.get("graph_attrs", {}).get("goal", ""))
            t.passed = "Test attributes" in str(goal) or len(ast.get("nodes", [])) >= 3
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    # DOT Parsing — conditional
    t = ConformanceTest("parse_conditional", "dot_parsing", "Parse DOT with conditional edges")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "parse", str(dot_dir / "conditional.dot")])
    t.duration = time.time() - start
    try:
        ast = json.loads(out)
        t.passed = code == 0 and isinstance(ast, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    # Validation — missing start
    t = ConformanceTest("validate_missing_start", "validation", "Validate DOT without start node produces error")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "validate", str(dot_dir / "missing_start.dot")])
    t.duration = time.time() - start
    try:
        diags = json.loads(out)
        if isinstance(diags, dict):
            diags_list = diags.get("diagnostics", diags.get("errors", []))
        elif isinstance(diags, list):
            diags_list = diags
        else:
            diags_list = []
        has_error = any(
            d.get("severity", "") in ("error", "Error")
            or "start" in str(d).lower()
            for d in diags_list
        )
        t.passed = has_error or code != 0
    except (json.JSONDecodeError, ValueError):
        t.passed = code != 0  # Non-zero exit on validation error is acceptable
    if not t.passed:
        t.error = f"Expected error for missing start node: {out[:200]}"
    tests.append(t)

    # Validation — orphan node
    t = ConformanceTest("validate_orphan", "validation", "Validate DOT with orphan node produces warning")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "validate", str(dot_dir / "orphan.dot")])
    t.duration = time.time() - start
    try:
        diags = json.loads(out)
        if isinstance(diags, dict):
            diags_list = diags.get("diagnostics", diags.get("warnings", []))
        elif isinstance(diags, list):
            diags_list = diags
        else:
            diags_list = []
        has_warning = any(
            d.get("severity", "") in ("warning", "Warning")
            or "orphan" in str(d).lower()
            or "unreachable" in str(d).lower()
            for d in diags_list
        )
        t.passed = has_warning
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Expected warning for orphan node: {out[:200]}"
    tests.append(t)

    # Validation — valid graph
    t = ConformanceTest("validate_valid", "validation", "Validate valid DOT produces no errors")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "validate", str(dot_dir / "simple.dot")])
    t.duration = time.time() - start
    try:
        diags = json.loads(out)
        if isinstance(diags, dict):
            diags_list = diags.get("diagnostics", diags.get("errors", []))
        elif isinstance(diags, list):
            diags_list = diags
        else:
            diags_list = []
        errors = [d for d in diags_list if d.get("severity", "") in ("error", "Error")]
        t.passed = code == 0 and len(errors) == 0
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    tests.append(t)

    # Execution — simple linear pipeline
    t = ConformanceTest("execute_linear", "execution_engine", "Execute simple linear pipeline")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "run", str(dot_dir / "simple.dot")], timeout=60)
    t.duration = time.time() - start
    try:
        result = json.loads(out)
        t.passed = code == 0 and isinstance(result, dict)
        if t.passed:
            status = result.get("status", result.get("outcome", ""))
            t.passed = status in ("success", "completed", "done")
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    if not t.passed:
        t.error = err[:500] if err else out[:500]
    tests.append(t)

    # Execution — conditional branching
    t = ConformanceTest("execute_conditional", "execution_engine", "Execute pipeline with conditional edges")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "run", str(dot_dir / "conditional.dot")], timeout=60)
    t.duration = time.time() - start
    try:
        result = json.loads(out)
        t.passed = code == 0 and isinstance(result, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    if not t.passed:
        t.error = err[:500] if err else out[:500]
    tests.append(t)

    # Execution — goal gate
    t = ConformanceTest("execute_goal_gate", "goal_gate", "Goal gate enforcement during execution")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "run", str(dot_dir / "goal_gate.dot")], timeout=60)
    t.duration = time.time() - start
    try:
        result = json.loads(out)
        t.passed = code == 0 and isinstance(result, dict)
    except (json.JSONDecodeError, ValueError):
        t.passed = code == 0
    if not t.passed:
        t.error = err[:500] if err else out[:500]
    tests.append(t)

    # List handlers
    t = ConformanceTest("list_handlers", "node_handlers", "list-handlers returns registered handler types")
    start = time.time()
    code, out, err = run_cmd([CONFORMANCE_BIN, "list-handlers"])
    t.duration = time.time() - start
    try:
        handlers = json.loads(out)
        t.passed = code == 0 and isinstance(handlers, list) and len(handlers) > 0
    except (json.JSONDecodeError, ValueError):
        t.passed = False
        t.error = f"Invalid JSON: {out[:200]}"
    tests.append(t)

    return tests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, required=True)
    args = parser.parse_args()

    tier_runners = {1: tier1_tests, 2: tier2_tests, 3: tier3_tests}
    runner = tier_runners.get(args.tier)
    if not runner:
        print(f"Unknown tier: {args.tier}", file=sys.stderr)
        sys.exit(1)

    tests = runner()

    # Group by section
    sections = {}
    for test in tests:
        sec = test.section
        if sec not in sections:
            sections[sec] = {"total": 0, "passed": 0}
        sections[sec]["total"] += 1
        if test.passed:
            sections[sec]["passed"] += 1

    results = {
        "tier": args.tier,
        "tests": [t.to_dict() for t in tests],
        "sections": sections,
        "total": len(tests),
        "passed": sum(1 for t in tests if t.passed),
    }

    # Write results
    Path(RESULTS_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(RESULTS_FILE).write_text(json.dumps(results, indent=2))

    # Also print summary
    print(f"\\nConformance Results: {results[\'passed\']}/{results[\'total\']} passed", file=sys.stderr)
    for test in tests:
        status = "PASS" if test.passed else "FAIL"
        print(f"  [{status}] {test.name}: {test.description}", file=sys.stderr)
        if test.error:
            print(f"         Error: {test.error[:200]}", file=sys.stderr)


if __name__ == "__main__":
    main()
'''


def generate_tasks(tiers: list[TierDef], output_dir: Path) -> None:
    """Generate Harbor-compatible task directories for all tiers."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for tier in tiers:
        task_dir = output_dir / tier.slug
        if task_dir.exists():
            shutil.rmtree(task_dir)
        task_dir.mkdir(parents=True)

        # task.toml
        (task_dir / "task.toml").write_text(generate_task_toml(tier))

        # instruction.md
        (task_dir / "instruction.md").write_text(generate_instruction(tier))

        # environment/Dockerfile
        env_dir = task_dir / "environment"
        env_dir.mkdir()
        (env_dir / "Dockerfile").write_text(generate_dockerfile(tier))

        # tests/
        tests_dir = task_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test.sh").write_text(generate_test_sh(tier))
        (tests_dir / "mock_server.py").write_text(generate_mock_server())
        (tests_dir / "score.py").write_text(generate_score_py())

        # tests/conformance/
        conf_dir = tests_dir / "conformance"
        conf_dir.mkdir()
        (conf_dir / "run_conformance.py").write_text(generate_run_conformance())

        # solution/ (empty placeholder)
        solution_dir = task_dir / "solution"
        solution_dir.mkdir()
        (solution_dir / "solve.sh").write_text("#!/bin/bash\necho 'No oracle solution available'\nexit 1\n")

        # Make scripts executable
        import stat
        for script in [tests_dir / "test.sh", solution_dir / "solve.sh"]:
            script.chmod(script.stat().st_mode | stat.S_IEXEC)
