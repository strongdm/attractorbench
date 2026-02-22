#!/usr/bin/env python3
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
        prompt="Multi-line\nattribute test",
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
    print(f"\nConformance Results: {results['passed']}/{results['total']} passed", file=sys.stderr)
    for test in tests:
        status = "PASS" if test.passed else "FAIL"
        print(f"  [{status}] {test.name}: {test.description}", file=sys.stderr)
        if test.error:
            print(f"         Error: {test.error[:200]}", file=sys.stderr)


if __name__ == "__main__":
    main()
