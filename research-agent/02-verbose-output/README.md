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
$ uv run python research_agent.py "Search the web: latest stable Go version?"
```

141 lines showing the conversation as what it actually is — **a list of messages, each with a
role** — rather than a stream of prose:

```
──PROMPT ────────────────────────────────────────────────────────────
  Not a stream message. This is the string passed to query(); it
  becomes the first user turn of the conversation.

  Search the web: latest stable Go version?

──SESSION INIT · SystemMessage(subtype='init') ──────────────────────
  session_id              a2dd210b-fc87-40aa-9b44-4019a7ff00e3
  model                   claude-haiku-4-5-20251001
  apiKeySource            ANTHROPIC_API_KEY

  mcp_servers
    ● linkup               connected
  tools  4 discovered · 1 in allowed_tools
    ✓ mcp__linkup__linkup-search  ← allowed

──[1] AssistantMessage ──────────────────────────────────────────────
  the model speaking — its output

  message_id                           msg_011CeNDULfKXWikKZxU4RRkq
  usage.input_tokens                        3,214
  usage.cache_creation_input_tokens             0

  ▸ ThinkingBlock  260 chars · ~136 tokens
        The user is asking me to search the web... I should use the
        linkup-search function to find this information.

  ▸ ToolUseBlock  mcp__linkup__linkup-search
        .id           toolu_01UV97iYi2dVguZKSFWX9MMH
        .name         mcp__linkup__linkup-search
        .input
          { "query": "latest stable Go version" }

      Claude REQUESTS this call here. It does not execute anything.

──[2] UserMessage ───────────────────────────────────────────────────
  NOT you, and not the model. The SDK ran the tool and is handing
  the result back as a USER turn — the model's next input.

  ▸ ToolResultBlock
        .tool_use_id  toolu_01UV97iYi2dVguZKSFWX9MMH  ← pairs with above
        .is_error     None
        .content      list of 1 part(s), 36,130 chars
          { "results": [ { "name": "Golang Latest Version", ...
          … truncated, 36,130 chars total (use --full)

──[3] AssistantMessage ──────────────────────────────────────────────
  usage.input_tokens                           10
  usage.cache_creation_input_tokens        14,033

  ▸ ThinkingBlock  782 chars · ~267 tokens
  ▸ TextBlock  729 chars
        Based on the search results, the latest stable Go version is
        **Go 1.26.6**...

──ResultMessage ─────────────────────────────────────────────────────
  subtype                              success
  stop_reason                          end_turn
  num_turns                                     2
  duration_ms                               7,596  = 7.60 s
  total_cost_usd                        $0.024551

  ResultMessage.usage  — passed through verbatim from the Anthropic API
    input_tokens                              3,224
    output_tokens                               565
    cache_creation_input_tokens              14,033
    cache_read_input_tokens                       0
    output_tokens_details.thinking_tokens       302

  ResultMessage.model_usage  — computed locally; not in the API response
    contextWindow                           200,000
    maxOutputTokens                          32,000
    provider                             firstParty

  computed here, not an SDK field
    context used                             18,158  9.1% of contextWindow
```

---

## 2. New concepts

### 2.1 A conversation is a list of messages, each with a role

This is the thing worth taking away from the step. A Claude conversation is not a transcript of
prose — it is an ordered list of **messages**, and each message's *type* is its role:

| Class | Whose turn it is |
|---|---|
| `UserMessage` | Input **to** the model |
| `AssistantMessage` | Output **from** the model |
| `SystemMessage` | The harness talking about the run, not part of the conversation |
| `ResultMessage` | A summary emitted once the run finishes |

Neither `UserMessage` nor `AssistantMessage` has a `role` field, because **the class is the role**.

### 2.2 Who actually runs the tool

Follow messages [1] → [2] → [3] in the output above and the answer is unambiguous:

1. **`[1] AssistantMessage`** contains a `ToolUseBlock`. The model has *asked* for
   `linkup-search` with `{"query": "latest stable Go version"}`. It has executed nothing — a
   language model cannot make a network call.
2. **The SDK** reads that block, calls the Linkup MCP server, and gets 36,130 characters back.
3. **`[2] UserMessage`** carries the answer in a `ToolResultBlock`. It is a **user** message
   because, from the model's point of view, a tool result is *input handed to it* — the same role
   your original question occupies.
4. **`[3] AssistantMessage`** is the model reading that input and replying.

So the loop is: **the model requests, your code executes, the result goes back as a user turn.**
That single sentence is most of Domain 1.

`ToolUseBlock.id` and `ToolResultBlock.tool_use_id` are the same string — that pairing is what
lets several tools run in parallel and still be matched to their requests.

### 2.3 Every call resends the whole conversation

The stream shows each message **as it arrives**, which makes it look as though the second call
sends only the tool result. It does not. **The Claude API is stateless: every request carries the
entire conversation so far.** The second call above contained:

```
  user       "Search the web: latest stable Go version?"
  assistant  thinking + tool_use(linkup-search)
  user       tool_result — 36,130 characters
```

…plus the system prompt and the tool definitions. Nothing is remembered server-side.

The token counts prove it, which is why the script prints the sum:

```
[1]  usage.input_tokens                  3,214
     usage.cache_creation_input_tokens       0
     context sent to the model           3,214   computed · first call

[3]  usage.input_tokens                     10
     usage.cache_creation_input_tokens  14,022
     context sent to the model          14,032   computed · grew by 10,818
```

The second call received **14,032 tokens, not 10.** The other 14,022 were *billed* as cache
creation rather than fresh input — but they were still sent. Those extra 10,818 tokens are turn
one's output plus that 36,130-character tool result.

This is the central economic fact about agents: **context grows with every turn, and you pay for
all of it on every call.** A five-search agent is not five times one search, because each call
re-sends everything before it. Prompt caching is what makes that affordable; trimming tool output
before it lands is what keeps it small (step 03).

`context sent to the model` is labelled **computed** — it is a sum this script performs, not a
field the SDK reports.

### 2.4 The prompt is not in the stream

The string you pass to `query()` never comes back as a `UserMessage`. It becomes the conversation's
first user turn on the other side of the subprocess, but the stream you iterate starts with the
model's reply. The script prints it under `──PROMPT` and **says it is not a stream message**, so
you do not go hunting for something that was never emitted.

### 2.5 Blocks, and how they arrive

A message's `.content` is a **list of blocks**, not a string, because one message can mix kinds:

| Block | Field to read | Appears in |
|---|---|---|
| `ThinkingBlock` | `.thinking` | `AssistantMessage` |
| `TextBlock` | `.text` | either |
| `ToolUseBlock` | `.id`, `.name`, `.input` | `AssistantMessage` |
| `ToolResultBlock` | `.tool_use_id`, `.content`, `.is_error` | `UserMessage` |

A wrinkle worth knowing: the SDK often delivers **one block per `AssistantMessage`**, with several
such objects sharing a single `message_id`. So "one API message" and "one object you receive" are
not the same thing — group by `message_id` when you care about the former.

### 2.6 Thinking blocks

Haiku 4.5 reasons before it acts, and that reasoning is a real block you can read. In one run the
model decided **not** to search:

> *"I know from my training data that the capital of Malta is Valletta… I can answer this directly
> without needing to use the search tools."*

That is the tool-selection decision in the model's own words, *before* it happens. When an agent
picks the wrong tool, this is the first place to look.

### 2.7 Discovered vs. allowed tools

The init message lists **4** Linkup tools; we allow **1**. Step 01 argued that scoping tools
matters; here the gap is on screen.

### 2.8 Field names, and the casing question

Every label in the output is a **real SDK field name** — `usage.input_tokens`, `duration_ms`,
`contextWindow` — because those are what you write in code and what a certification asks about.
Anything derived is filed under **`computed here, not an SDK field`** so you never revise a
calculated number into memory as a real one.

You may notice two naming styles. `snake_case` (underscores) is the Python and REST convention;
`camelCase` (a capital letter) is the JavaScript one. Both appear because the two objects come from
**opposite sides of the subprocess boundary**, and the SDK's own types say so:

```
ResultMessage.usage        →  dict[str, Any]           ← untyped: whatever the API sent
ResultMessage.model_usage  →  dict[str, ModelUsage]    ← a TypedDict the SDK declares
```

`usage` is passed through verbatim from the **Anthropic API**, which is snake_case. `model_usage`
is assembled by the **Claude Code CLI**, which is TypeScript, hence camelCase. The giveaway is its
contents: `costUSD`, `contextWindow`, `provider` — **the API returns none of those**. It reports
tokens and has no idea what you are paying.

**`model_usage` also repeats every token count under camelCase names. This script does not print
them twice.** Token counts appear once, in `usage`, in the API's own casing; `model_usage` shows
only what exists nowhere else. Seeing `input_tokens` and `inputTokens` side by side teaches nothing
except that you can be confused in two languages.

The rule worth keeping: **casing tells you which layer you are touching.** camelCase means the
tooling computed it, so do not go looking for that field in the Anthropic API reference.

### 2.9 Why `stop_reason` is empty on every turn

Conceptually the agentic loop *is* driven by `stop_reason`: the raw Messages API returns
`"tool_use"` when the model wants a tool and `"end_turn"` when it is done, and a hand-written loop
branches on exactly that. The exam tests this.

You will not see the intermediate values here. Measured across a full run: **one `end_turn` in the
entire stream — on the `ResultMessage` — and `null` on all four `AssistantMessage` objects.**

That is because **the SDK runs the loop for you** (step 01 §2.1). It reads `tool_use`, executes the
tool, returns the result, and surfaces a `stop_reason` only once the whole run is finished. Know
the concept for the exam; know that this surface abstracts it. Seeing `"tool_use"` with your own
eyes means dropping to the raw Messages API, which is a different exercise.

The same applies to `usage.output_tokens`, which reports a *snapshot* per message rather than a
tally — a run totalling 617 output tokens showed `5` and `1` on its two messages. Both fields are
correct on the `ResultMessage`, and that is the only place this script prints them.

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

### 4.3 One section per message, not per "turn"

An earlier version of this step drew `TURN 1` / `TURN 2` headers and rendered the tool result
underneath the assistant's — which quietly told the reader that a tool result is part of the
assistant's message. **It is not.** It is a separate `UserMessage`.

The loop now opens a new section whenever the message *type* changes:

```python
elif isinstance(message, AssistantMessage):
    if message.message_id != current_message_id:
        current_message_id = message.message_id
        seq += 1
        render_assistant_header(seq, message)
    ...

elif isinstance(message, UserMessage):
    seq += 1
    current_message_id = None      # the next assistant reply is a new message
    render_user_header(seq, message)
```

`message_id` groups the several `AssistantMessage` objects that belong to one API message (§2.4);
resetting it on a `UserMessage` means the model's next reply correctly opens a new section.

`num_turns` in the summary counts round-trips (2 here), while the sequence counts messages (3).
Both are shown, because they are different things.

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
6. **The layout was making a false claim.** Drawing tool results under a `TURN` heading alongside
   the assistant's thinking implied they were part of the assistant's message. A reader called it
   out, and they were right: a tool result is a `UserMessage`. The old layout would have taught the
   wrong mental model to everyone who read it — and no test would ever have caught it, because the
   code was working perfectly.
7. **Showing the same number twice under two names is not thoroughness.** Printing both
   `input_tokens` and `inputTokens` felt rigorous and was just noise. Token counts now appear once;
   `model_usage` shows only what exists nowhere else.
8. **Friendly labels were hiding the thing worth learning.** The display originally read `input`,
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

*Where to look:* the `[1]` / `[2]` / `[3]` message sections and `stop_reason: end_turn` in the
`ResultMessage`. Step 01 covered this as a diagram; here the loop is the transcript. Note **§2.9**
for the wrinkle that matters on the exam: the per-message `stop_reason` the API defines is not
surfaced by this SDK, because the SDK is the thing reading it.

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
