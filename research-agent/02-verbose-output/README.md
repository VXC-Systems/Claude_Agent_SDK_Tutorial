# Step 02 — The same agent, with everything visible

Step 01 printed four lines. This step prints everything the agent actually does: what it thinks,
which tool it picks and with what arguments, what came back, how long it took, and what it cost.

**The agent is unchanged.** Same model, same MCP server, same isolation switches, same one-shot
`query()`. Only the rendering is different — which is the point: an agent you cannot observe is an
agent you cannot debug.

Part of the [CCAR-F / CCAR-P preparation track](../../EXAM-COVERAGE.md); §8 explains which exam
topics this step covers and what to look at.

---

## 1. What you'll build

```console
$ uv run python research_agent.py "latest stable release of Rust?"
```

```
──SESSION INIT ──────────────────────────────────────────────────────
  SystemMessage(subtype='init').data

  session_id              9161772a-24f0-447a-8f8a-ec6c7526f778
  model                   claude-haiku-4-5-20251001
  apiKeySource            ANTHROPIC_API_KEY
  permissionMode          default
  claude_code_version     2.1.239

  mcp_servers
    ● linkup               connected

  tools  4 discovered · 1 in allowed_tools
    · mcp__linkup__linkup-fetch
    · mcp__linkup__linkup-get-research
    · mcp__linkup__linkup-research
    ✓ mcp__linkup__linkup-search  ← allowed

──TURN 1 ────────────────────────────────────────────────────────────
  AssistantMessage

  message_id                           msg_011CeNC2Rdd6pGomgo8yF51s
  model                                claude-haiku-4-5-20251001
  usage.input_tokens                        3,217
  usage.cache_creation_input_tokens             0
  usage.cache_read_input_tokens                 0
  usage.service_tier                     standard

  ▸ thinking  298 chars · ~146 tokens
      This is current information that would benefit from a real-time
      web search since releases are continuous...

  ▸ tool call  mcp__linkup__linkup-search
      id       toolu_01LjksD4f1e5LP6SfCmhVu3U
      input
        { "query": "latest stable release version" }

  ▸ tool result  ← toolu_01LjksD4f1e5LP6SfCmhVu3U
      parts    1
      size     36,130 chars
        { "results": [ { "name": "...", ...
        … truncated, 36,130 chars total (use --full)

──TURN 2 ────────────────────────────────────────────────────────────
  AssistantMessage

  message_id                           msg_011CeNC2dP46Ja8o3wEd1WSd
  usage.input_tokens                           10
  usage.cache_creation_input_tokens        14,027
  usage.cache_read_input_tokens                 0

  ▸ thinking  810 chars · ~274 tokens
  ▸ answer
      Go 1.26 is the current latest stable release...

──SUMMARY ───────────────────────────────────────────────────────────
  ResultMessage

  subtype                              success
  stop_reason                          end_turn
  is_error                             False
  num_turns                                     2
  duration_ms                               8,505  = 8.51 s
  duration_api_ms                           8,237  = 8.24 s
  total_cost_usd                        $0.024669

  ResultMessage.usage  (snake_case)
    usage.input_tokens                        3,224
    usage.output_tokens                         590
    usage.cache_creation_input_tokens        14,027
    usage.cache_read_input_tokens                 0
    usage.output_tokens_details.thinking_tokens   275

  ResultMessage.model_usage['claude-haiku-4-5-20251001']  (camelCase — note the difference)
    inputTokens                               4,125
    outputTokens                                602
    cacheCreationInputTokens                 14,027
    cacheReadInputTokens                          0
    contextWindow                           200,000
    maxOutputTokens                          32,000
    costUSD                               $0.024669

  computed (not an SDK field)
    context used                             18,152  9.1% of contextWindow
      = inputTokens + cacheCreationInputTokens + cacheReadInputTokens
```

Look at the two turn headers together. Turn 1 pays `usage.input_tokens 3,217`; turn 2 pays only
`10`, but writes **14,027 tokens into `usage.cache_creation_input_tokens`** — that is the tool
result being absorbed. The whole economics of the run is legible from four lines.

The agentic loop from step 01's diagram is no longer a diagram. It is the output.

---

## 2. New concepts

### 2.1 The full message stream

Step 01 handled three message types and silently dropped the rest. Here is everything that actually
arrives, in order:

| Message | Carries | Step 01 |
|---|---|---|
| `SystemMessage` `subtype="init"` | Session id, model, cwd, auth source, MCP status, **the full tool inventory** | status only |
| `SystemMessage` `subtype="thinking_tokens"` | A running estimate of thinking tokens, streamed | dropped |
| `AssistantMessage` → `ThinkingBlock` | The model's reasoning before it acts | **dropped** |
| `AssistantMessage` → `ToolUseBlock` | `.name`, `.id`, and `.input` — the actual arguments | name only |
| `UserMessage` → `ToolResultBlock` | `.content`, `.is_error`, `.tool_use_id` | **dropped** |
| `AssistantMessage` → `TextBlock` | Prose for the user | shown |
| `ResultMessage` | Outcome, turns, timings, session id, tokens, cost | subtype + cost |

Two of those are worth pausing on.

**Tool results arrive as a `UserMessage`.** Counter-intuitive until you think in roles: the result
is *input handed to the model*, so it occupies a user turn. That is also why `num_turns` is 2 for a
single search — request, then answer.

**`ToolUseBlock.id` pairs with `ToolResultBlock.tool_use_id`.** With one tool call you can ignore
this. The moment an agent fires several in parallel, that id is the only thing telling you which
result belongs to which request — which is why this step prints both.

### 2.2 Thinking blocks

Haiku 4.5 reasons before it acts, and that reasoning is a real block in the stream. It is worth
reading: in one of the runs above the model decided **not** to search —

> *"I know from my training data that the capital of Malta is Valletta… I can answer this directly
> without needing to use the search tools."*

That is the tool-selection decision, in the model's own words, before it happens. When an agent
picks the wrong tool, this is the first place to look.

### 2.3 Discovered vs. allowed tools

The init message lists **4** Linkup tools. We allow **1**. Step 01 asserted that `allowed_tools`
narrows what Claude may call; here you can see the gap directly, which makes the least-privilege
argument concrete rather than theoretical.

### 2.4 Observability as a first-class output

`ResultMessage` carries far more than cost:

| Field | Why you care |
|---|---|
| `num_turns` | Did the agent loop? How many times? |
| `duration_ms` / `duration_api_ms` | Total vs. time actually spent in the API — the gap is your overhead |
| `session_id` | The handle for resuming a conversation (step 03) |
| `stop_reason` | `end_turn` = finished; anything else needs investigating |
| `usage` | Token counts **and cache behaviour** |
| `permission_denials` | Tools Claude wanted but was not allowed |

### 2.5 What a turn can and cannot tell you

Each turn header shows the facts that are genuinely per-message:

```
──TURN 2 ─────────────────────────────────────────
  AssistantMessage

  message_id                           msg_011CeNC2dP46Ja8o3wEd1WSd
  model                                claude-haiku-4-5-20251001
  usage.input_tokens                           10
  usage.cache_creation_input_tokens        14,027
  usage.cache_read_input_tokens                 0
  usage.service_tier                     standard
```

Compare that with turn 1 (`usage.input_tokens 3,217`, cache creation `0`) and the mechanic is
visible: turn 1 pays for the prompt, then the 36,000-character tool result is **written into the
cache** so turn 2 re-reads almost nothing as fresh input.

Two fields are deliberately **not** shown per turn, because the SDK does not report them
meaningfully at that level:

| Field | Why not |
|---|---|
| `output_tokens` | Per-message it reports a *snapshot*, not a tally — a run totalling 697 output tokens showed `5` and `1` on its two messages. Printing it per turn would look authoritative and be wrong. |
| `stop_reason` | `None` on every `AssistantMessage` in this mode; only the final `ResultMessage` carries it. |

Both appear correctly in the **SUMMARY**. Knowing *which* numbers a stream can be trusted for is
the actual skill here — an observability layer that prints a plausible wrong number is worse than
one that prints nothing.

### 2.6 Every label here is a real field name

The output deliberately uses **the SDK's own field names**, not friendly ones. `usage.input_tokens`,
not "input"; `duration_ms`, not "duration"; `costUSD`, not "cost". You are meant to come away
knowing the names, because those are what you write in code — and what a certification asks about.

Anything the script works out itself is filed under **`computed (not an SDK field)`** with its
formula shown, so you never mistake a derived number for one the SDK reported:

```
  computed (not an SDK field)
    context used                             18,152  9.1% of contextWindow
      = inputTokens + cacheCreationInputTokens + cacheReadInputTokens
```

**The casing trap.** The same quantities appear under two different conventions on the *same*
message:

| Quantity | `ResultMessage.usage` | `ResultMessage.model_usage[model]` |
|---|---|---|
| input tokens | `input_tokens` | `inputTokens` |
| output tokens | `output_tokens` | `outputTokens` |
| cache written | `cache_creation_input_tokens` | `cacheCreationInputTokens` |
| cache read | `cache_read_input_tokens` | `cacheReadInputTokens` |
| cost | *(absent)* | `costUSD` |
| context size | *(absent)* | `contextWindow` |

`usage` is **snake_case**; `model_usage` is **camelCase**. The `init` payload mixes both in one
dict — `session_id` sits next to `apiKeySource`. This is not a typo in the tutorial, and guessing
the wrong casing is the kind of error that costs you a debugging session.

---

## 3. Setup

Nothing new. Same keys, same `.env` at the repository root — see the
[project README](../../README.md) and [step 01 §3](../01-one-shot/README.md#3-setup).

```bash
cd research-agent/02-verbose-output
uv run python research_agent.py "your research question"
```

Two flags, both about *how much* you see:

**The default already shows every turn and every message.** Nothing is dropped — only *long values*
are clipped, and the caps differ by what the value is:

| Content | Cap | Why |
|---|---|---|
| Tool results | 600 chars | Reliably enormous — a single web search returns 36,000–48,000 characters and would bury everything else |
| The model's thinking | 4,000 chars | Short and the most interesting part of the run; effectively never clipped |
| Tool arguments | 2,000 chars | Usually a single line |
| The answer | never clipped | It is the point |

A clipped value always states its real size, so truncation is never silent.

| Flag | Effect |
|---|---|
| `--full` | Removes every cap, including tool results. Expect ~700 lines. |
| `--raw` | Additionally dumps **every message in the stream as JSON** before the formatted view. The escape hatch: if the pretty output hides something, `--raw` shows the object exactly as the SDK delivered it. Adds ~1,300 lines. |

```bash
uv run python research_agent.py --full "latest stable Go version?"
```

```bash
uv run python research_agent.py --raw "What is 2+2?"
```

They combine, which is the most verbose the script gets:

```bash
uv run python research_agent.py --full --raw "latest stable Go version?"
```

---

## 4. The code

The agent half is **identical to step 01** — same `ClaudeAgentOptions`, same isolation switches,
same `async for`. Read step 01 for that. What follows is only what is new.

### 4.1 Terminal formatting without dependencies

```python
def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
```

Colour is applied only when writing to a real terminal, so piping to a file or `grep` produces
clean text instead of escape codes. `NO_COLOR` is a
[cross-tool convention](https://no-color.org/) worth honouring.

Everything else is four small helpers — `c()` for styling, `rule()` for section headers, `kv()` for
aligned pairs, `body()` for wrapped text at an indent. No `rich`, no dependency: the point of this
step is seeing the message structure, and a formatting library would sit between you and it.

### 4.2 Truncation, per kind of content

```python
TOOL_RESULT_CHARS = 600
THINKING_CHARS = 4000
TOOL_INPUT_CHARS = 2000

def clip(text: str, full: bool, limit: int) -> tuple[str, str]:
    if full or len(text) <= limit:
        return text, ""
    return text[:limit], f"… truncated, {len(text):,} chars total (use --full)"
```

The first version used **one** cap for everything, which was wrong in a way that took a reader to
notice: at 600 characters it clipped a 1,014-character *thinking block* — the most interesting
content in the run — with exactly the same rule it used on a 36,000-character tool result.

One cap treats "enormous machine output" and "the model's reasoning" as the same problem. They are
not: tool results need aggressive clipping, reasoning needs none. Hence three constants, and a
`limit` parameter rather than a global.

The note always states the **real size**, because a truncation you cannot see is a lie.

### 4.3 Tracking turns, properly

```python
if message.message_id != current_message_id:
    current_message_id = message.message_id
    turn += 1
    render_turn_header(turn, message)
```

The first version of this step guessed at turn boundaries by counting tool results. That worked,
but it was a heuristic. **`message_id` is the real thing**: blocks sharing an id are one API
message, so a thinking block and the tool call that follows it belong to the same turn — which is
why `render_turn_header` only fires when the id changes.

That also gives each turn its own `usage` and `model`, which is where the per-turn token line comes
from.

### 4.4 `--raw`, the escape hatch

```python
try:
    payload = dataclasses.asdict(message)   # SDK messages are dataclasses
except TypeError:
    payload = {"repr": repr(message)}
```

Any pretty renderer is a lossy view — it shows what its author thought mattered. `--raw` dumps the
message as JSON so you can check the formatted output against the source, and discover fields this
script ignores. Every finding in §6 came from looking at raw messages first.

### 4.5 Rendering the init banner

`render_init()` pulls the interesting keys out of `message.data`, which is a plain dict. One line
worth calling out:

```python
mem = (data.get("memory_paths") or {}).get("auto")
```

That prints the path Claude Code would load saved memory from — and it resolves under the temp
directory we set as `cwd`. **This is direct evidence for step 01's third isolation finding**, which
was established from behaviour alone: the memory selection really is keyed to the working
directory. The banner shows the mechanism, not just its symptom.

---

## 5. Running it

Try a question the model can answer alone, then one it cannot:

```bash
uv run python research_agent.py "What is the capital of Malta?"
uv run python research_agent.py "What is the latest stable release of Rust?"
```

The first finishes in **one turn with no tool call** — and the thinking block tells you why. The
second runs two turns with a search in between. Same code, different behaviour, decided by the
model. Watching that difference is the exercise.

---

## 6. What we learned building it

1. **The stream is much richer than step 01 suggested.** Thinking blocks, streamed token
   estimates, and full tool results were all arriving and being silently dropped. A message type
   you do not handle is not an error — which makes it easy to be unaware of what you are missing.
2. **A conditional message can lie if you get the condition wrong.** The cache hint originally
   printed "cache was written, not read" whenever the read count was zero — including runs where
   *nothing was cached at all*. Caught by running a query that used no cache. The fix is checking
   that a cache was actually created:
   ```python
   if usage.get("cache_creation_input_tokens") and not usage.get("cache_read_input_tokens"):
   ```
   A wrong explanation is worse than no explanation, because the reader believes it.
3. **Verifying one path is not verifying the feature.** The first successful run answered from the
   model's own knowledge, so the tool-call, tool-result and turn-tracking code had never executed.
   It looked finished. Forcing a search exercised the other half.
4. **Not every field in the stream is trustworthy at the level it appears.** Adding per-turn stats
   looked like a simple matter of printing `message.usage`. Inspecting a real run first showed
   `output_tokens` reporting `5` and `1` on two messages of a run that totalled **697** — a
   snapshot, not a tally — and `stop_reason` sitting at `None` on every assistant message. Both are
   now shown only in the summary, where they are correct, with the reason written next to the code.
   Had the display been written from the field names alone, it would have printed confident
   nonsense.
5. **`message_id` beats a heuristic.** Turns were originally reconstructed by counting tool
   results. It gave the right answer, but grouping by `message_id` *is* the boundary rather than a
   proxy for it — and it hands you each turn's `usage` and `model` for free.
6. **Friendly labels were hiding the thing worth learning.** The display originally read `input`,
   `cache write`, `cost`, `duration` — pleasant, and useless for anyone who then has to write the
   code. Switching every label to the real field name surfaced something none of us had noticed:
   `usage` is snake_case while `model_usage` is camelCase, on the same message. A prettier interface
   had been quietly concealing an API detail that will bite in practice.

---

## 7. Design notes

- **Observability is cheap here and expensive later.** Every number displayed already existed in
  the stream; the only cost is printing it. In production the same fields are what you would ship
  to logs or a dashboard — `duration_api_ms`, `num_turns` and `usage` are the three that tell you
  whether an agent is behaving.
- **Truncate loudly, never silently.** A clipped value that does not announce its real size will
  eventually be mistaken for the whole value.
- **Degrade gracefully.** `isatty()` and `NO_COLOR` mean the same script is useful interactively
  and in a pipeline. An agent script that only works in a terminal is half a tool.
- **Cost is a design signal.** The summary shows ~13,000 tokens of cache *written* and none read.
  In a one-shot script that write is pure overhead; it only pays off when a session is reused —
  which is the argument for step 03.

**What this design is not.** Output goes to stdout as text, not structured logs. There is no
`--json` mode, no persistence, and no redaction — everything the tool returns is printed, so do not
point this at a tool handling sensitive data without adding one.

---

## 8. Exam topics covered

This step is unusually dense in exam terms, because *observing* the loop is how most of Domain 1
gets assessed. For the tutorial-wide picture see [`EXAM-COVERAGE.md`](../../EXAM-COVERAGE.md).

### CCAR-F Domain 1 — Agentic Architecture & Orchestration (27% of the exam)

**Topic 1.1 — the agentic loop.** The exam expects you to know the loop's lifecycle: a request goes
to Claude, you inspect why it stopped, execute any tool it asked for, return the result, and repeat
until it stops for a different reason. It also tests the *anti-patterns* — deciding you are finished
by parsing prose, or capping iterations as your primary stopping rule, instead of reading the stop
signal.

*Where to look:* the `TURN 1` / `TURN 2` headers and `stop_reason: end_turn` in the summary. Step
01 covered this as a diagram; here the loop is literally the transcript. Note that the run ends
because the model stopped asking for tools — not because the script counted anything.

### CCAR-F Domain 2 — Tool Design & MCP Integration (18%)

**Topic 2.3 — tool distribution and capability bloat.** The exam's claim is that giving an agent
more tools degrades its selection reliability, and that scoping each agent to what its role needs
is the fix.

*Where to look:* `Tools  4 discovered · 1 allowed`. This is the same lesson as step 01's
`tools=[]`, but now measurable rather than argued.

**Topic 2.4 — MCP server integration.** Knowing that tools from configured servers are discovered
at connection time and become available together.

*Where to look:* the `MCP servers` block and the tool inventory — both come from a single `init`
message emitted before Claude does anything.

### CCAR-F Domain 5 — Context Management & Reliability (15%)

**Topic 5.1 — managing conversation context.** The exam is concerned with tool results accumulating
in context and consuming tokens out of proportion to their relevance — a 40-field response where 5
fields matter.

*Where to look:* `size 48,265 chars` on the tool result, against `input 4,119` tokens in the
summary. That single search dominates the context budget. This step only *shows* the problem;
trimming tool output before it accumulates is step 03's concern.

**Topic 5.3 — error propagation.** Distinguishing a failed call from a successful call that
returned nothing.

*Where to look:* `is_error` on the tool result changes the label to `▸ tool error` in red, and
`permission_denials` appears in the summary when Claude wanted a tool it was not allowed.

### CCAR-P Domain 4 — Evaluation, Testing & Optimization (16%)

**Monitoring with logging and observability; optimising token, latency and cost trade-offs.** The
Professional exam asks you to justify configuration decisions against measurements rather than
intuition.

*Where to look:* the entire summary block. `duration` vs `(API …)` separates model time from your
overhead; the token table shows where the budget went.

### CCAR-P Domain 2 — Models, Prompting & Context Engineering (13%)

**Prompt reuse strategies, including caching.** *Where to look:* the `cache write` / `cache read`
pair, in both turn headers and the summary. Prompt caching happens whether or not you asked for it,
and in a one-shot script it is pure cost — written every run, read never. Seeing the number is what
makes the trade-off arguable rather than theoretical.

**Optimising context windows and managing token usage.** The Professional exam expects you to
reason about how much of the window a design consumes, not just whether it fits.

*Where to look:* the `computed (not an SDK field)` block in the summary, derived from
`model_usage.contextWindow`. One web search consumed roughly 9% of the window; five would consume
half. That is the argument for trimming tool output before it accumulates — step 03's problem.

### Knowing the field names themselves

Both exams test the SDK's actual surface, not a paraphrase of it. Every number this step prints is
labelled with the field it came from, so reading the output *is* revision. The ones worth being
able to name without looking them up:

| Object | Fields |
|---|---|
| `ResultMessage` | `subtype`, `stop_reason`, `is_error`, `num_turns`, `duration_ms`, `duration_api_ms`, `session_id`, `total_cost_usd`, `usage`, `model_usage`, `permission_denials`, `result` |
| `ResultMessage.usage` | `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens_details.thinking_tokens` |
| `ResultMessage.model_usage[model]` | `inputTokens`, `outputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`, `contextWindow`, `maxOutputTokens`, `costUSD` |
| `AssistantMessage` | `content`, `model`, `message_id`, `session_id`, `usage`, `stop_reason`, `parent_tool_use_id` |
| Blocks | `TextBlock.text` · `ThinkingBlock.thinking` · `ToolUseBlock.id/.name/.input` · `ToolResultBlock.tool_use_id/.content/.is_error` |
| `SystemMessage(subtype="init").data` | `session_id`, `model`, `cwd`, `tools`, `mcp_servers`, `apiKeySource`, `permissionMode`, `memory_paths` |

And the trap from §2.6: **`usage` is snake_case, `model_usage` is camelCase**, for the same
quantities, on the same message.

---

## 9. Rough edges

- **stdout only.** No `--json` mode, so this is readable but not machine-parseable. A CI-facing
  version would want structured output.
- **No redaction.** Tool results print verbatim. Fine for web search; not fine for a tool returning
  customer data.
- **Thinking blocks are model-dependent.** Haiku 4.5 emits them here; a different model or setting
  may not, and the section simply will not appear.
- **Turn tracking is inferred**, not read from the stream. It matches `num_turns` in every run
  observed, but it is reconstruction rather than ground truth.
- Still one-shot: no memory between runs.

---

## 10. Next

**Step 03 — multi-turn chat.** Replace one-shot `query()` with `ClaudeSDKClient` so the session
stays open, follow-up questions build on earlier answers, and that 13,000-token cache write finally
gets read back.

### Reference

- [Python SDK reference](https://code.claude.com/docs/en/agent-sdk/python)
- [Streaming vs. single-turn](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode)
- [MCP configuration](https://code.claude.com/docs/en/agent-sdk/mcp)
