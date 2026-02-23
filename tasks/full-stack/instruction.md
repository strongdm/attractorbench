# Full Stack — attractorbench Tiers 1-3

You are building three layers of a software system in one workspace.
Each layer builds on the previous layer's implementation.

**IMPORTANT**: The detailed specifications for each layer are in `/workspace/specs/`.
Read each spec file before implementing its layer.

## Architecture

- **Layer 1: Unified LLM SDK** — multi-provider LLM client library
- **Layer 2: Coding Agent Loop** — imports Layer 1's Client, Request, Response
- **Layer 3: Attractor Pipeline** — imports Layer 2 as CodergenBackend

## Implementation Constraints

- Implement in any programming language
- **Single codebase** — all three layers live in `/workspace`
- Provide a **single `Makefile`** with `build` and `test` targets that build and test ALL layers
- The conformance CLI must be at `./bin/conformance` and support ALL subcommands from all three layers
- Layer 2 **MUST** import and use Layer 1's LLM client (not a separate HTTP client)
- Layer 3 **MUST** import and use Layer 2's agent loop as its CodergenBackend (not call LLM directly)
- Write your own comprehensive test suite (run via `make test`)
- All work goes in `/workspace`

---

## Layer 1: Unified LLM SDK

**Full specification**: `/workspace/specs/tier1_spec.md` — read this file before implementing this layer.

### Conformance Contract

Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

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


### Definition of Done


#### 8.1 Core Infrastructure

- [ ] `Client` can be constructed from environment variables (`Client.from_env()`)
- [ ] `Client` can be constructed programmatically with explicit adapter instances
- [ ] Provider routing works: requests are dispatched to the correct adapter based on `provider` field
- [ ] Default provider is used when `provider` is omitted from a request
- [ ] `ConfigurationError` is raised when no provider is configured and no default is set
- [ ] Middleware chain executes in correct order (request: registration order, response: reverse order)
- [ ] Module-level default client works (`set_default_client()` and implicit lazy initialization)
- [ ] Model catalog is populated with current models and `get_model_info()` / `list_models()` return correct data

#### 8.2 Provider Adapters

- [ ] Adapter uses the provider's **native API** (OpenAI: Responses API, Anthropic: Messages API, Gemini: Gemini API) -- NOT a compatibility shim
- [ ] Authentication works (API key from env var or explicit config)
- [ ] `complete()` sends a request and returns a correctly populated `Response`
- [ ] `stream()` returns an async iterator of correctly typed `StreamEvent` objects
- [ ] System messages are extracted/handled per provider convention
- [ ] All 5 roles (SYSTEM, USER, ASSISTANT, TOOL, DEVELOPER) are translated correctly
- [ ] `provider_options` escape hatch passes through provider-specific parameters
- [ ] Beta headers are supported (especially Anthropic's `anthropic-beta` header)
- [ ] HTTP errors are translated to the correct error hierarchy types
- [ ] `Retry-After` headers are parsed and set on the error object

#### 8.3 Message & Content Model

- [ ] Messages with text-only content work across all providers
- [ ] **Image input works**: images sent as URL, base64 data, and local file path are correctly translated per provider
- [ ] Audio and document content parts are handled (or gracefully rejected if provider doesn't support them)
- [ ] Tool call content parts round-trip correctly (assistant message with tool calls -> tool result messages -> next assistant message)
- [ ] Thinking blocks (Anthropic) are preserved and round-tripped with signatures intact
- [ ] Redacted thinking blocks are passed through verbatim
- [ ] Multimodal messages (text + images in the same message) work

#### 8.4 Generation

- [ ] `generate()` works with a simple text `prompt`
- [ ] `generate()` works with a full `messages` list
- [ ] `generate()` rejects when both `prompt` and `messages` are provided
- [ ] `stream()` yields `TEXT_DELTA` events that concatenate to the full response text
- [ ] `stream()` yields `STREAM_START` and `FINISH` events with correct metadata
- [ ] Streaming follows the start/delta/end pattern for text segments
- [ ] `generate_object()` returns parsed, validated structured output
- [ ] `generate_object()` raises `NoObjectGeneratedError` on parse/validation failure
- [ ] Cancellation via abort signal works for both `generate()` and `stream()`
- [ ] Timeouts work (total timeout and per-step timeout)

#### 8.5 Reasoning Tokens

- [ ] OpenAI reasoning models (GPT-5.2 series, etc.) return `reasoning_tokens` in `Usage` via the Responses API
- [ ] `reasoning_effort` parameter is passed through correctly to OpenAI reasoning models
- [ ] Anthropic extended thinking blocks are returned as `THINKING` content parts when enabled
- [ ] Thinking block `signature` field is preserved for round-tripping
- [ ] Gemini thinking tokens (`thoughtsTokenCount`) are mapped to `reasoning_tokens` in `Usage`
- [ ] `Usage` correctly reports `reasoning_tokens` as distinct from `output_tokens`

#### 8.6 Prompt Caching

- [ ] **OpenAI**: caching works automatically via the Responses API (no client-side configuration needed)
- [ ] **OpenAI**: `Usage.cache_read_tokens` is populated from `usage.prompt_tokens_details.cached_tokens`
- [ ] **Anthropic**: adapter automatically injects `cache_control` breakpoints on the system prompt, tool definitions, and conversation prefix
- [ ] **Anthropic**: `prompt-caching-2024-07-31` beta header is included automatically when cache_control is present
- [ ] **Anthropic**: `Usage.cache_read_tokens` and `Usage.cache_write_tokens` are populated correctly
- [ ] **Anthropic**: automatic caching can be disabled via `provider_options.anthropic.auto_cache = false`
- [ ] **Gemini**: automatic prefix caching works (no client-side configuration needed)
- [ ] **Gemini**: `Usage.cache_read_tokens` is populated from `usageMetadata.cachedContentTokenCount`
- [ ] Multi-turn agentic session: verify that turn 5+ shows significant cache_read_tokens (>50% of input tokens) for all three providers

#### 8.7 Tool Calling

- [ ] Tools with `execute` handlers (active tools) trigger automatic tool execution loops
- [ ] Tools without `execute` handlers (passive tools) return tool calls to the caller without looping
- [ ] `max_tool_rounds` is respected: loop stops after the configured number of rounds
- [ ] `max_tool_rounds = 0` disables automatic execution entirely
- [ ] **Parallel tool calls**: when the model returns N tool calls in one response, all N are executed concurrently
- [ ] **Parallel tool results**: all N results are sent back in a single continuation request (not one at a time)
- [ ] Tool execution errors are sent to the model as error results (`is_error = true`), not raised as exceptions
- [ ] Unknown tool calls (model calls a tool not in definitions) send an error result, not an exception
- [ ] `ToolChoice` modes (auto, none, required, named) are translated correctly per provider
- [ ] Tool call argument JSON is parsed and validated before passing to execute handlers
- [ ] `StepResult` objects track each step's tool calls, results, and usage

#### 8.8 Error Handling & Retry

- [ ] All errors in the hierarchy are raised for the correct HTTP status codes (see Section 6.4 table)
- [ ] `retryable` flag is set correctly on each error type
- [ ] Exponential backoff with jitter works: delays increase correctly per attempt
- [ ] `Retry-After` header overrides calculated backoff when present (and within `max_delay`)
- [ ] `max_retries = 0` disables automatic retries
- [ ] Rate limit errors (429) are retried transparently
- [ ] Non-retryable errors (401, 403, 404) are raised immediately without retry
- [ ] Retries apply per-step, not to the entire multi-step operation
- [ ] Streaming does not retry after partial data has been delivered

#### 8.9 Cross-Provider Parity

- [ ] [Matrix] Simple text generation (col 1)
- [ ] [Matrix] Simple text generation (col 2)
- [ ] [Matrix] Simple text generation (col 3)
- [ ] [Matrix] Streaming text generation (col 1)
- [ ] [Matrix] Streaming text generation (col 2)
- [ ] [Matrix] Streaming text generation (col 3)
- [ ] [Matrix] Image input (base64) (col 1)
- [ ] [Matrix] Image input (base64) (col 2)
- [ ] [Matrix] Image input (base64) (col 3)
- [ ] [Matrix] Image input (URL) (col 1)
- [ ] [Matrix] Image input (URL) (col 2)
- [ ] [Matrix] Image input (URL) (col 3)
- [ ] [Matrix] Single tool call + execution (col 1)
- [ ] [Matrix] Single tool call + execution (col 2)
- [ ] [Matrix] Single tool call + execution (col 3)
- [ ] [Matrix] Multiple parallel tool calls (col 1)
- [ ] [Matrix] Multiple parallel tool calls (col 2)
- [ ] [Matrix] Multiple parallel tool calls (col 3)
- [ ] [Matrix] Multi-step tool loop (3+ rounds) (col 1)
- [ ] [Matrix] Multi-step tool loop (3+ rounds) (col 2)
- [ ] [Matrix] Multi-step tool loop (3+ rounds) (col 3)
- [ ] [Matrix] Streaming with tool calls (col 1)
- [ ] [Matrix] Streaming with tool calls (col 2)
- [ ] [Matrix] Streaming with tool calls (col 3)
- [ ] [Matrix] Structured output (generate_object) (col 1)
- [ ] [Matrix] Structured output (generate_object) (col 2)
- [ ] [Matrix] Structured output (generate_object) (col 3)
- [ ] [Matrix] Reasoning/thinking token reporting (col 1)
- [ ] [Matrix] Reasoning/thinking token reporting (col 2)
- [ ] [Matrix] Reasoning/thinking token reporting (col 3)
- [ ] [Matrix] Error handling (invalid API key -> 401) (col 1)
- [ ] [Matrix] Error handling (invalid API key -> 401) (col 2)
- [ ] [Matrix] Error handling (invalid API key -> 401) (col 3)
- [ ] [Matrix] Error handling (rate limit -> 429) (col 1)
- [ ] [Matrix] Error handling (rate limit -> 429) (col 2)
- [ ] [Matrix] Error handling (rate limit -> 429) (col 3)
- [ ] [Matrix] Usage token counts are accurate (col 1)
- [ ] [Matrix] Usage token counts are accurate (col 2)
- [ ] [Matrix] Usage token counts are accurate (col 3)
- [ ] [Matrix] Prompt caching (cache_read_tokens > 0 on turn 2+) (col 1)
- [ ] [Matrix] Prompt caching (cache_read_tokens > 0 on turn 2+) (col 2)
- [ ] [Matrix] Prompt caching (cache_read_tokens > 0 on turn 2+) (col 3)
- [ ] [Matrix] Provider-specific options pass through (col 1)
- [ ] [Matrix] Provider-specific options pass through (col 2)
- [ ] [Matrix] Provider-specific options pass through (col 3)

#### 8.10 Integration Smoke Test



---

## Layer 2: Coding Agent Loop

**Full specification**: `/workspace/specs/tier2_spec.md` — read this file before implementing this layer.

### Conformance Contract

Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance session-create` — Create a session with a mock provider profile. Exit 0 on success.
- `./bin/conformance process-input` — Read a JSON task prompt from stdin, run the agentic loop against the mock LLM, write JSON session result to stdout.
- `./bin/conformance tool-dispatch` — Read a JSON tool call from stdin, dispatch it, write JSON tool result to stdout.
- `./bin/conformance steering` — Read a JSON steering message from stdin, inject it into a running session, write acknowledgment to stdout.
- `./bin/conformance events` — Run a short session, write newline-delimited JSON events to stdout.

The mock LLM server runs at `http://localhost:9999` inside the test container.


### Definition of Done


#### 9.1 Core Loop

- [ ] Session can be created with a ProviderProfile and ExecutionEnvironment
- [ ] `process_input()` runs the agentic loop: LLM call -> tool execution -> loop until natural completion
- [ ] Natural completion: model responds with text only (no tool calls) and the loop exits
- [ ] Round limits: `max_tool_rounds_per_input` stops the loop when reached
- [ ] Session turn limits: `max_turns` stops the loop across all inputs
- [ ] Abort signal: cancellation stops the loop, kills running processes, transitions to CLOSED
- [ ] Loop detection: consecutive identical tool call patterns trigger a warning SteeringTurn
- [ ] Multiple sequential inputs work: submit, wait for completion, submit again

#### 9.2 Provider Profiles

- [ ] OpenAI profile provides codex-rs-aligned tools including `apply_patch` (v4a format)
- [ ] Anthropic profile provides Claude Code-aligned tools including `edit_file` (old_string/new_string)
- [ ] Gemini profile provides gemini-cli-aligned tools
- [ ] Each profile produces a provider-specific system prompt covering identity, tool usage, and coding guidance
- [ ] Custom tools can be registered on top of any profile
- [ ] Tool name collisions resolved: custom registration overrides profile defaults

#### 9.3 Tool Execution

- [ ] Tool calls are dispatched through the ToolRegistry
- [ ] Unknown tool calls return an error result to the LLM (not an exception)
- [ ] Tool argument JSON is parsed and validated against the tool's parameter schema
- [ ] Tool execution errors are caught and returned as error results (`is_error = true`)
- [ ] Parallel tool execution works when the profile's `supports_parallel_tool_calls` is true

#### 9.4 Execution Environment

- [ ] `LocalExecutionEnvironment` implements all file and command operations
- [ ] Command timeout default is 10 seconds
- [ ] Command timeout is overridable per-call via the shell tool's `timeout_ms` parameter
- [ ] Timed-out commands: process group receives SIGTERM, then SIGKILL after 2 seconds
- [ ] Environment variable filtering excludes sensitive variables (`*_API_KEY`, `*_SECRET`, etc.) by default
- [ ] The `ExecutionEnvironment` interface is implementable by consumers for custom environments (Docker, K8s, WASM, SSH)

#### 9.5 Tool Output Truncation

- [ ] Character-based truncation runs FIRST on all tool outputs (handles pathological cases like 10MB single-line CSVs)
- [ ] Line-based truncation runs SECOND where configured (shell: 256, grep: 200, glob: 500)
- [ ] Truncation inserts a visible marker: `[WARNING: Tool output was truncated. N characters removed...]`
- [ ] The full untruncated output is available via the `TOOL_CALL_END` event
- [ ] Default character limits match the table in Section 5.2 (read_file: 50k, shell: 30k, grep: 20k, etc.)
- [ ] Both character and line limits are overridable via `SessionConfig`

#### 9.6 Steering

- [ ] `steer()` queues a message that is injected after the current tool round
- [ ] `follow_up()` queues a message that is processed after the current input completes
- [ ] Steering messages appear as SteeringTurn in the history
- [ ] SteeringTurns are converted to user-role messages for the LLM

#### 9.7 Reasoning Effort

- [ ] `reasoning_effort` is passed through to the LLM SDK Request
- [ ] Changing `reasoning_effort` mid-session takes effect on the next LLM call
- [ ] Valid values: "low", "medium", "high", null (provider default) (certain providers might have other options like `xhigh`)

#### 9.8 System Prompts

- [ ] System prompt includes provider-specific base instructions
- [ ] System prompt includes environment context (platform, git, working dir, date, model info)
- [ ] System prompt includes tool descriptions from the active profile
- [ ] Project documentation files (AGENTS.md + provider-specific files) are discovered and included
- [ ] User instruction overrides are appended last (highest priority)
- [ ] Only relevant project files are loaded (e.g., Anthropic profile loads CLAUDE.md, not GEMINI.md)

#### 9.9 Subagents

- [ ] Subagents can be spawned with a scoped task via the `spawn_agent` tool
- [ ] Subagents share the parent's execution environment (same filesystem)
- [ ] Subagents maintain independent conversation history
- [ ] Depth limiting prevents recursive spawning (default max depth: 1)
- [ ] Subagent results are returned to the parent as tool results
- [ ] `send_input`, `wait`, and `close_agent` tools work correctly

#### 9.10 Event System

- [ ] All event kinds listed in Section 2.9 are emitted at the correct times
- [ ] Events are delivered via async iterator or language-appropriate equivalent
- [ ] `TOOL_CALL_END` events carry full untruncated tool output
- [ ] Session lifecycle events (SESSION_START, SESSION_END) bracket the session

#### 9.11 Error Handling

- [ ] Tool execution errors -> error result sent to LLM (model can recover)
- [ ] LLM API transient errors (429, 500-503) -> retry with backoff (handled by Unified LLM SDK layer)
- [ ] Authentication errors -> surface immediately, no retry, session transitions to CLOSED
- [ ] Context window overflow -> emit warning event (no automatic compaction)
- [ ] Graceful shutdown: abort signal -> cancel LLM stream -> kill running processes -> flush events -> emit SESSION_END

#### 9.12 Cross-Provider Parity Matrix

- [ ] [Matrix] Simple file creation task (col 1)
- [ ] [Matrix] Simple file creation task (col 2)
- [ ] [Matrix] Simple file creation task (col 3)
- [ ] [Matrix] Read file, then edit it (col 1)
- [ ] [Matrix] Read file, then edit it (col 2)
- [ ] [Matrix] Read file, then edit it (col 3)
- [ ] [Matrix] Multi-file edit in one session (col 1)
- [ ] [Matrix] Multi-file edit in one session (col 2)
- [ ] [Matrix] Multi-file edit in one session (col 3)
- [ ] [Matrix] Shell command execution (col 1)
- [ ] [Matrix] Shell command execution (col 2)
- [ ] [Matrix] Shell command execution (col 3)
- [ ] [Matrix] Shell command timeout handling (col 1)
- [ ] [Matrix] Shell command timeout handling (col 2)
- [ ] [Matrix] Shell command timeout handling (col 3)
- [ ] [Matrix] Grep + glob to find files (col 1)
- [ ] [Matrix] Grep + glob to find files (col 2)
- [ ] [Matrix] Grep + glob to find files (col 3)
- [ ] [Matrix] Multi-step task (read -> analyze -> edit) (col 1)
- [ ] [Matrix] Multi-step task (read -> analyze -> edit) (col 2)
- [ ] [Matrix] Multi-step task (read -> analyze -> edit) (col 3)
- [ ] [Matrix] Tool output truncation (large file) (col 1)
- [ ] [Matrix] Tool output truncation (large file) (col 2)
- [ ] [Matrix] Tool output truncation (large file) (col 3)
- [ ] [Matrix] Parallel tool calls (if supported) (col 1)
- [ ] [Matrix] Parallel tool calls (if supported) (col 2)
- [ ] [Matrix] Parallel tool calls (if supported) (col 3)
- [ ] [Matrix] Steering mid-task (col 1)
- [ ] [Matrix] Steering mid-task (col 2)
- [ ] [Matrix] Steering mid-task (col 3)
- [ ] [Matrix] Reasoning effort change (col 1)
- [ ] [Matrix] Reasoning effort change (col 2)
- [ ] [Matrix] Reasoning effort change (col 3)
- [ ] [Matrix] Subagent spawn and wait (col 1)
- [ ] [Matrix] Subagent spawn and wait (col 2)
- [ ] [Matrix] Subagent spawn and wait (col 3)
- [ ] [Matrix] Loop detection triggers warning (col 1)
- [ ] [Matrix] Loop detection triggers warning (col 2)
- [ ] [Matrix] Loop detection triggers warning (col 3)
- [ ] [Matrix] Error recovery (tool fails, model retries) (col 1)
- [ ] [Matrix] Error recovery (tool fails, model retries) (col 2)
- [ ] [Matrix] Error recovery (tool fails, model retries) (col 3)
- [ ] [Matrix] Provider-specific editing format works (col 1)
- [ ] [Matrix] Provider-specific editing format works (col 2)
- [ ] [Matrix] Provider-specific editing format works (col 3)

#### 9.13 Integration Smoke Test



---

## Layer 3: Attractor Pipeline

**Full specification**: `/workspace/specs/tier3_spec.md` — read this file before implementing this layer.

### Conformance Contract

Your implementation must expose a CLI at `./bin/conformance` with these subcommands:

- `./bin/conformance parse <dotfile>` — Parse a DOT file, write JSON AST to stdout.
- `./bin/conformance validate <dotfile>` — Validate a DOT file, write JSON diagnostics to stdout.
- `./bin/conformance run <dotfile>` — Execute the pipeline with a mock backend, write JSON execution result to stdout.
- `./bin/conformance list-handlers` — Write a JSON array of registered handler types to stdout.

The mock LLM backend runs at `http://localhost:9999` inside the test container. The `CodergenBackend` should send requests there.


### Definition of Done


#### 11.1 DOT Parsing

- [ ] Parser accepts the supported DOT subset (digraph with graph/node/edge attribute blocks)
- [ ] Graph-level attributes (`goal`, `label`, `model_stylesheet`) are extracted correctly
- [ ] Node attributes are parsed including multi-line attribute blocks (attributes spanning multiple lines within `[...]`)
- [ ] Edge attributes (`label`, `condition`, `weight`) are parsed correctly
- [ ] Chained edges (`A -> B -> C`) produce individual edges for each pair
- [ ] Node/edge default blocks (`node [...]`, `edge [...]`) apply to subsequent declarations
- [ ] Subgraph blocks are flattened (contents kept, wrapper removed)
- [ ] `class` attribute on nodes merges in attributes from the stylesheet
- [ ] Quoted and unquoted attribute values both work
- [ ] Comments (`//` and `/* */`) are stripped before parsing

#### 11.2 Validation and Linting

- [ ] Exactly one start node (shape=Mdiamond) is required
- [ ] Exactly one exit node (shape=Msquare) is required
- [ ] Start node has no incoming edges
- [ ] Exit node has no outgoing edges
- [ ] All nodes are reachable from start (no orphans)
- [ ] All edges reference valid node IDs
- [ ] Codergen nodes (shape=box) have non-empty `prompt` attribute (warning if missing)
- [ ] Condition expressions on edges parse without errors
- [ ] `validate_or_raise()` throws on error-severity violations
- [ ] Lint results include rule name, severity (error/warning), node/edge ID, and message

#### 11.3 Execution Engine

- [ ] Engine resolves the start node and begins execution there
- [ ] Each node's handler is resolved via shape-to-handler-type mapping
- [ ] Handler is called with (node, context, graph, logs_root) and returns an Outcome
- [ ] Outcome is written to `{logs_root}/{node_id}/status.json`
- [ ] Edge selection follows the 5-step priority: condition match -> preferred label -> suggested IDs -> weight -> lexical
- [ ] Engine loops: execute node -> select edge -> advance to next node -> repeat
- [ ] Terminal node (shape=Msquare) stops execution
- [ ] Pipeline outcome is "success" if all goal_gate nodes succeeded, "fail" otherwise

#### 11.4 Goal Gate Enforcement

- [ ] Nodes with `goal_gate=true` are tracked throughout execution
- [ ] Before allowing exit via a terminal node, the engine checks all goal gate nodes have status SUCCESS
- [ ] If any goal gate node has not succeeded, the engine routes to `retry_target` (if configured) instead of exiting
- [ ] If no retry_target and goal gates unsatisfied, pipeline outcome is "fail"

#### 11.5 Retry Logic

- [ ] Nodes with `max_retries > 0` are retried on RETRY or FAIL outcomes
- [ ] Retry count is tracked per-node and respects the configured limit
- [ ] Backoff between retries works (constant, linear, or exponential as configured)
- [ ] Jitter is applied to backoff delays when configured
- [ ] After retry exhaustion, the node's final outcome is used for edge selection

#### 11.6 Node Handlers

- [ ] **Start handler:** Returns SUCCESS immediately (no-op)
- [ ] **Exit handler:** Returns SUCCESS immediately (no-op, engine checks goal gates)
- [ ] **Codergen handler:** Expands `$goal` in prompt, calls `CodergenBackend.run()`, writes prompt.md and response.md to stage dir
- [ ] **Wait.human handler:** Presents outgoing edge labels as choices to the interviewer, returns selected label as preferred_label
- [ ] **Conditional handler:** Passes through; engine evaluates edge conditions against outcome/context
- [ ] **Parallel handler:** Fans out to multiple target nodes concurrently (or sequentially as fallback)
- [ ] **Fan-in handler:** Waits for all parallel branches to complete before proceeding
- [ ] **Tool handler:** Executes configured tool/command and returns result
- [ ] Custom handlers can be registered by type string

#### 11.7 State and Context

- [ ] Context is a key-value store accessible to all handlers
- [ ] Handlers can read context and return `context_updates` in the Outcome
- [ ] Context updates are merged after each node execution
- [ ] Checkpoint is saved after each node completion (current_node, completed_nodes, context, retry counts)
- [ ] Resume from checkpoint: load checkpoint -> restore state -> continue from current_node
- [ ] Artifacts are written to `{logs_root}/{node_id}/` (prompt.md, response.md, status.json)

#### 11.8 Human-in-the-Loop

- [ ] Interviewer interface works: `ask(question) -> Answer`
- [ ] Question supports types: SINGLE_SELECT, MULTI_SELECT, FREE_TEXT, CONFIRM
- [ ] AutoApproveInterviewer always selects the first option (for automation/testing)
- [ ] ConsoleInterviewer prompts in terminal and reads user input
- [ ] CallbackInterviewer delegates to a provided function
- [ ] QueueInterviewer reads from a pre-filled answer queue (for testing)

#### 11.9 Condition Expressions

- [ ] `=` (equals) operator works for string comparison
- [ ] `!=` (not equals) operator works
- [ ] `&&` (AND) conjunction works with multiple clauses
- [ ] `outcome` variable resolves to the current node's outcome status
- [ ] `preferred_label` variable resolves to the outcome's preferred label
- [ ] `context.*` variables resolve to context values (missing keys = empty string)
- [ ] Empty condition always evaluates to true (unconditional edge)

#### 11.10 Model Stylesheet

- [ ] Stylesheet is parsed from the graph's `model_stylesheet` attribute
- [ ] Selectors by shape name work (e.g., `box { model = "claude-opus-4-6" }`)
- [ ] Selectors by class name work (e.g., `.fast { model = "gemini-3-flash-preview" }`)
- [ ] Selectors by node ID work (e.g., `#review { reasoning_effort = "high" }`)
- [ ] Specificity order: universal < shape < class < ID
- [ ] Stylesheet properties are overridden by explicit node attributes

#### 11.11 Transforms and Extensibility

- [ ] AST transforms can modify the Graph between parsing and validation
- [ ] Transform interface: `transform(graph) -> graph`
- [ ] Built-in variable expansion transform replaces `$goal` in prompts
- [ ] Custom transforms can be registered and run in order
- [ ] HTTP server mode (if implemented): POST /run starts pipeline, GET /status checks state, POST /answer submits human input

#### 11.12 Cross-Feature Parity Matrix

- [ ] [Matrix] Parse a simple linear pipeline (start -> A -> B -> done)
- [ ] [Matrix] Parse a pipeline with graph-level attributes (goal, label)
- [ ] [Matrix] Parse multi-line node attributes
- [ ] [Matrix] Validate: missing start node -> error
- [ ] [Matrix] Validate: missing exit node -> error
- [ ] [Matrix] Validate: orphan node -> warning
- [ ] [Matrix] Execute a linear 3-node pipeline end-to-end
- [ ] [Matrix] Execute with conditional branching (success/fail paths)
- [ ] [Matrix] Execute with retry on failure (max_retries=2)
- [ ] [Matrix] Goal gate blocks exit when unsatisfied
- [ ] [Matrix] Goal gate allows exit when all satisfied
- [ ] [Matrix] Wait.human presents choices and routes on selection
- [ ] [Matrix] Edge selection: condition match wins over weight
- [ ] [Matrix] Edge selection: weight breaks ties for unconditional edges
- [ ] [Matrix] Edge selection: lexical tiebreak as final fallback
- [ ] [Matrix] Context updates from one node are visible to the next
- [ ] [Matrix] Checkpoint save and resume produces same result
- [ ] [Matrix] Stylesheet applies model override to nodes by shape
- [ ] [Matrix] Prompt variable expansion ($goal) works
- [ ] [Matrix] Parallel fan-out and fan-in complete correctly
- [ ] [Matrix] Custom handler registration and execution works
- [ ] [Matrix] Pipeline with 10+ nodes completes without errors

#### 11.13 Integration Smoke Test



