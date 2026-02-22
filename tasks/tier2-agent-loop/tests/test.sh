#!/bin/bash
# attractorbench Tier 2: Coding Agent Loop — Verifier
set -uo pipefail
set +e

cleanup() {
  if [ -n "${MOCK_PID:-}" ]; then
    kill "$MOCK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

mkdir -p /logs/verifier

cd /workspace

# Start mock LLM server in background
python3 /tests/mock_server.py >> /logs/verifier/mock-server.log 2>&1 &
MOCK_PID=$!

# Wait for mock server readiness
for _ in {1..20}; do
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
python3 /tests/conformance/run_conformance.py --tier 2 >> /logs/verifier/conformance.log 2>&1
CONFORMANCE_EXIT=$?
echo "Conformance exit code: $CONFORMANCE_EXIT" | tee -a /logs/verifier/conformance.log

# Aggregate into reward.json
python3 /tests/score.py \
  --build-exit $BUILD_EXIT \
  --selftest-exit $SELFTEST_EXIT \
  --conformance-exit $CONFORMANCE_EXIT \
  --selftest-log /logs/verifier/self-test.log \
  --conformance /logs/verifier/conformance_results.json \
  --output /logs/verifier/reward.json

echo "=== Done ==="
cat /logs/verifier/reward.json

exit 0
