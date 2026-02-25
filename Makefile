.PHONY: results specs-sync specs-update generate test \
	run-sonnet run-opus run-gpt52 run-gpt52-high run-gpt53-high \
	run-gemini31 run-gemini31ct run-gemini25pro \
	run-gemini31ct-opencode run-slate

V ?= 1
EXTRA_ARGS ?=

# ── Results & Leaderboard ──────────────────────────────────────────
# `make results` generates results/*.md with AUTHORITATIVE token/cost
# data computed from Harbor's result.json + litellm pricing tables.
#
# IMPORTANT: When updating LEADERBOARD.md or RUN_LOG.md, ALWAYS copy
# token counts, wall times, and costs from results/*.md. NEVER write
# "-" or "unknown" for these fields — the data is there. Run
# `make results` first, then copy the numbers.

results:
	@mkdir -p results
	@JOB_DIRS="$$(find jobs -maxdepth 1 -mindepth 1 -type d -print)"; \
		if [ -z "$$JOB_DIRS" ]; then \
			echo "No Harbor job directories found under jobs/"; \
			exit 1; \
		fi; \
		uv run attractorbench leaderboard $$JOB_DIRS --markdown > results/leaderboard.md; \
		uv run attractorbench run-log $$JOB_DIRS --markdown > results/run_log.md; \
		echo ""; \
		echo "=== REFERENCE DATA (results/*.md) ==="; \
		echo "Copy token/cost data from these files into LEADERBOARD.md and RUN_LOG.md."; \
		echo "Do NOT leave '-' for tokens or costs — the data is computed from Harbor results."; \
		echo ""

specs-sync:
	python3 scripts/sync_specs.py

specs-update:
	python3 scripts/sync_specs.py --latest

generate:
	uv run attractorbench generate --output-dir tasks

test:
	uv run pytest tests/ -v

# ── Default slate ─────────────────────────────────────────────────
# The "default slate" — the 5 runs we do every day.
# Usage:  make run-slate V=12
# Runs all 5 in parallel, then scores and rebuilds results.

run-slate: generate
	@echo "=== Running default slate (V=$(V)) ==="
	@echo "  opus46-v$(V)  sonnet46-v$(V)  gpt53codex-high-v$(V)  gemini31ct-v$(V)  gpt52-high-v$(V)"
	@echo ""
	@harbor run --path ./tasks --agent claude-code --model anthropic/claude-opus-4-6 \
		--env docker --timeout-multiplier 2 --job-name opus46-v$(V) $(EXTRA_ARGS) & \
	harbor run --path ./tasks --agent claude-code --model anthropic/claude-sonnet-4-6 \
		--env docker --timeout-multiplier 2 --job-name sonnet46-v$(V) $(EXTRA_ARGS) & \
	harbor run --path ./tasks --agent codex --model openai/gpt-5.3-codex \
		--env docker --timeout-multiplier 2 --agent-kwarg reasoning_effort=high \
		--job-name gpt53codex-high-v$(V) $(EXTRA_ARGS) & \
	harbor run --path ./tasks --agent gemini-cli --model google/gemini-3.1-pro-preview-customtools \
		--env docker --job-name gemini31ct-v$(V) $(EXTRA_ARGS) & \
	harbor run --path ./tasks --agent codex --model openai/gpt-5.2 \
		--env docker --timeout-multiplier 2 --agent-kwarg reasoning_effort=high \
		--job-name gpt52-high-v$(V) $(EXTRA_ARGS) & \
	wait
	@echo ""
	@echo "=== All runs complete. Scoring... ==="
	uv run attractorbench score jobs/opus46-v$(V)
	uv run attractorbench score jobs/sonnet46-v$(V)
	uv run attractorbench score jobs/gpt53codex-high-v$(V)
	uv run attractorbench score jobs/gemini31ct-v$(V)
	uv run attractorbench score jobs/gpt52-high-v$(V)
	$(MAKE) results

# ── Agent run targets ──────────────────────────────────────────────
# Usage:  make run-sonnet V=2 EXTRA_ARGS="--n-concurrent 2"
# Each target: generates tasks → runs Harbor → scores → updates results

run-sonnet: generate
	harbor run --path ./tasks --agent claude-code --model anthropic/claude-sonnet-4-6 \
		--env docker --timeout-multiplier 2 --job-name sonnet46-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/sonnet46-v$(V)
	$(MAKE) results

run-opus: generate
	harbor run --path ./tasks --agent claude-code --model anthropic/claude-opus-4-6 \
		--env docker --timeout-multiplier 2 --job-name opus46-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/opus46-v$(V)
	$(MAKE) results

run-gpt52: generate
	harbor run --path ./tasks --agent codex --model openai/gpt-5.2 \
		--env docker --timeout-multiplier 2 --job-name gpt52-codex-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gpt52-codex-v$(V)
	$(MAKE) results

run-gpt52-high: generate
	harbor run --path ./tasks --agent codex --model openai/gpt-5.2 \
		--env docker --timeout-multiplier 2 --agent-kwarg reasoning_effort=high \
		--job-name gpt52-high-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gpt52-high-v$(V)
	$(MAKE) results

run-gpt53-high: generate
	harbor run --path ./tasks --agent codex --model openai/gpt-5.3-codex \
		--env docker --timeout-multiplier 2 --agent-kwarg reasoning_effort=high \
		--job-name gpt53codex-high-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gpt53codex-high-v$(V)
	$(MAKE) results

run-gemini31: generate
	harbor run --path ./tasks --agent gemini-cli --model google/gemini-3.1-pro-preview \
		--env docker --job-name gemini31-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gemini31-v$(V)
	$(MAKE) results

run-gemini31ct: generate
	harbor run --path ./tasks --agent gemini-cli --model google/gemini-3.1-pro-preview-customtools \
		--env docker --job-name gemini31ct-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gemini31ct-v$(V)
	$(MAKE) results

run-gemini25pro: generate
	harbor run --path ./tasks --agent gemini-cli --model google/gemini-2.5-pro \
		--env docker --job-name gemini25pro-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gemini25pro-v$(V)
	$(MAKE) results

run-gemini31ct-opencode: generate
	harbor run --path ./tasks --agent opencode --model google/gemini-3.1-pro-preview-customtools \
		--env docker --job-name gemini31ct-opencode-v$(V) $(EXTRA_ARGS)
	uv run attractorbench score jobs/gemini31ct-opencode-v$(V)
	$(MAKE) results
