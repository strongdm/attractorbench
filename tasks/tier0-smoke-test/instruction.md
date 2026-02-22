# Smoke Test — attractorbench Tier 0

You are implementing **Smoke Test** from the Attractor NLSpec suite.

## Task

Read the specification below and implement a complete, working system that satisfies all requirements.

## Implementation Constraints

- Implement in any programming language
- Provide a `Makefile` with `build` and `test` targets
- The conformance CLI must be at `./bin/conformance`
- Write your own comprehensive test suite (run via `make test`)
- All work goes in `/workspace`

## Conformance Contract

Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance client-from-env` — Read OPENAI_API_KEY from the environment. Print "ok" and exit 0 if set, exit 1 otherwise.
- `./bin/conformance list-models` — Send GET to $OPENAI_BASE_URL/models. Print the JSON response to stdout. Exit 0.
- `./bin/conformance complete` — Read a JSON request from stdin. POST it to $OPENAI_BASE_URL/responses. Print the JSON response to stdout. Exit 0.

The mock LLM server runs at `http://localhost:9999` inside the test container. Set environment variables:
- `OPENAI_API_KEY=test-key`
- `OPENAI_BASE_URL=http://localhost:9999/v1`


## Definition of Done Checklist


### 0.1 Plumbing

- [ ] `make build` exits 0
- [ ] `make test` exits 0
- [ ] `./bin/conformance` exists and is executable
- [ ] `./bin/conformance client-from-env` reads OPENAI_API_KEY and exits 0
- [ ] `./bin/conformance list-models` returns JSON array from mock server
- [ ] `./bin/conformance complete` sends request and returns JSON response from mock server


---

## Full Specification

# Tier 0: Smoke Test

A minimal plumbing check to validate that your Harbor + attractorbench integration works before committing to a full tier run.

## Overview

Implement a trivial conformance CLI that proves the toolchain works end-to-end: environment builds, mock server responds, conformance binary runs, and scoring produces a reward.json.

## Requirements

1. Create a `Makefile` with `build` and `test` targets.
2. Create a CLI at `./bin/conformance` that accepts subcommands.
3. Implement the conformance contract below.

## Conformance Contract

```
./bin/conformance client-from-env
    Read OPENAI_API_KEY from the environment. Print "ok" and exit 0 if set, exit 1 otherwise.

./bin/conformance list-models
    Send GET to $OPENAI_BASE_URL/models. Print the JSON response to stdout. Exit 0.

./bin/conformance complete
    Read a JSON request from stdin with at least {"model": "...", "messages": [...]}.
    POST it to $OPENAI_BASE_URL/responses.
    Print the JSON response to stdout. Exit 0.
```

## Definition of Done

### 0.1 Plumbing

- [ ] `make build` exits 0
- [ ] `make test` exits 0
- [ ] `./bin/conformance` exists and is executable
- [ ] `./bin/conformance client-from-env` reads OPENAI_API_KEY and exits 0
- [ ] `./bin/conformance list-models` returns JSON array from mock server
- [ ] `./bin/conformance complete` sends request and returns JSON response from mock server

