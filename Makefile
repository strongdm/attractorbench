.PHONY: results generate test

results:
	uv run attractorbench leaderboard jobs/* --markdown > LEADERBOARD.md
	uv run attractorbench run-log jobs/* --markdown > RUN_LOG.md

generate:
	uv run attractorbench generate --output-dir tasks

test:
	uv run pytest tests/ -v
