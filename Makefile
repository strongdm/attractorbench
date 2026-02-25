.PHONY: results specs-sync specs-update generate test \
	run-sonnet run-opus run-gpt52 \
	run-gemini31 run-gemini31ct run-gemini25pro \
	run-gemini31ct-opencode

V ?= 1
EXTRA_ARGS ?=

results:
	@JOB_DIRS="$$(find jobs -maxdepth 1 -mindepth 1 -type d -print)"; \
		if [ -z "$$JOB_DIRS" ]; then \
			echo "No Harbor job directories found under jobs/"; \
			exit 1; \
		fi; \
		uv run attractorbench leaderboard $$JOB_DIRS --markdown > LEADERBOARD.md; \
		uv run attractorbench run-log $$JOB_DIRS --markdown > RUN_LOG.md; \
		echo "Updated LEADERBOARD.md and RUN_LOG.md"

specs-sync:
	python3 scripts/sync_specs.py

specs-update:
	python3 scripts/sync_specs.py --latest

generate:
	uv run attractorbench generate --output-dir tasks

test:
	uv run pytest tests/ -v

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
