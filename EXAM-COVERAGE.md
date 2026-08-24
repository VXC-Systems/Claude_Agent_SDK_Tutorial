# Exam coverage

What this tutorial covers, measured against the published blueprints for the Anthropic **Claude
Certified Architect** certifications — Foundations (CCAR-F) and Professional (CCAR-P).

Two purposes: show a reader honestly what they are and aren't getting, and drive the roadmap. The
gaps in these tables *are* the backlog.

> **On sourcing.** The exam guides are distributed through the Anthropic Partner Academy and are
> not publicly downloadable. The tables below use **domain names, weights and paraphrased topic
> labels** to index against — they do not reproduce the guides' text, task-statement wording, or
> any exam content. Read the guides themselves; this is a map, not a substitute.

**Legend** — ✅ taught · ◐ partly covered or demonstrated but not taught · ○ planned · ⊘ out of
scope for *this* tutorial (belongs to a sibling one)

---

## Foundations (CCAR-F)

60 items · 120 minutes · scaled cut score 720/1000 · five domains.

### Domain 1 — Agentic Architecture & Orchestration (27%)

| # | Topic | Status | Where |
|---|---|---|---|
| 1.1 | Agentic loop: `stop_reason`, feeding tool results back, model-driven vs. scripted control flow | ◐ | Step 01 §2.1 — observed through the SDK, not hand-implemented |
| 1.2 | Multi-agent orchestration, coordinator ↔ subagent | ○ | Step 06 |
| 1.3 | Subagent invocation, explicit context passing, spawning | ○ | Step 06 |
| 1.4 | Multi-step workflows: prerequisite gates and structured handoff | ○ | Step 05 |
| 1.5 | Hooks for tool-call interception and result normalisation | ○ | Step 05 |
| 1.6 | Task decomposition: fixed chains vs. adaptive | ○ | Step 06 |
| 1.7 | Session state, resumption, forking | ○ | Step 02 |

### Domain 2 — Tool Design & MCP Integration (18%)

| # | Topic | Status | Where |
|---|---|---|---|
| 2.1 | Tool interface design — descriptions as the selection mechanism, disambiguating similar tools | ○ | Step 03 |
| 2.2 | Structured error responses: error category, retryable flag, partial results | ○ | Step 03 |
| 2.3 | Tool distribution, capability bloat, `tool_choice` | ✅ | Step 01 §4.5, §6 |
| 2.4 | MCP server integration: transports, scoping, auth, naming | ✅ | Step 01 §2.4, §4.5, §6 |
| 2.5 | Built-in tools (Read/Write/Edit/Bash/Grep/Glob) and when each fits | ○ | Step 07 |

### Domain 3 — Claude Code Configuration & Workflows (20%)

Mostly a **sibling tutorial** — this is about configuring Claude Code, not building with the SDK.
Two items are nonetheless demonstrated by this repo's own machinery.

| # | Topic | Status | Where |
|---|---|---|---|
| 3.1 | `CLAUDE.md` hierarchy, scoping, modular organisation | ◐ | This repo has one; demonstrated, not taught |
| 3.2 | Custom slash commands and skills (`SKILL.md`, `context: fork`, `allowed-tools`) | ◐ | [`.claude/skills/`](.claude/skills/) — both review skills are exactly this |
| 3.3 | Path-specific rules with glob scoping | ⊘ | Sibling tutorial |
| 3.4 | Plan mode vs. direct execution | ⊘ | Sibling tutorial |
| 3.5 | Iterative refinement techniques | ⊘ | Sibling tutorial |
| 3.6 | Claude Code in CI/CD (`-p`, JSON output) | ⊘ | Sibling tutorial |

### Domain 4 — Prompt Engineering & Structured Output (20%)

| # | Topic | Status | Where |
|---|---|---|---|
| 4.1 | Explicit criteria over vague instructions, false-positive control | ◐ | The review skills are written this way; not yet taught as a step |
| 4.2 | Few-shot prompting for consistency and ambiguous cases | ○ | Step 04 |
| 4.3 | Structured output via tool use + JSON schema, `tool_choice` modes | ○ | Step 04 |
| 4.4 | Validation, retry-with-error-feedback, and its limits | ○ | Step 04 |
| 4.5 | Batch processing strategy and when it is inappropriate | ○ | Step 08 |
| 4.6 | Multi-instance and multi-pass review architectures | ◐ | Used on every step (two independent reviewers); not yet taught |

### Domain 5 — Context Management & Reliability (15%)

| # | Topic | Status | Where |
|---|---|---|---|
| 5.1 | Preserving critical facts across long conversations | ○ | Step 02 |
| 5.2 | Escalation triggers and ambiguity resolution | ○ | Step 07 |
| 5.3 | Error propagation across agents; access failure vs. empty result | ◐ | Step 01 §3.5 — MCP status surfaced; full treatment in Step 06 |
| 5.4 | Context management in large codebase exploration | ○ | Step 07 |
| 5.5 | Human review workflows and confidence calibration | ○ | Step 07 |
| 5.6 | Provenance and uncertainty in multi-source synthesis | ○ | Step 06 |

**Current Foundations coverage:** 2 of 30 topics fully taught, 6 partly. Domain 3 (20% of the
exam) is deliberately out of scope here.

---

## Professional (CCAR-P)

63 items · seven domains · a different character — architectural judgement and trade-offs rather
than SDK mechanics, with no prescribed exercises. Each step's **Design notes** section is written
at this level.

| Domain | Weight | Coverage |
|---|---|---|
| 1 — Solution Design & Architecture | 17% | ◐ Agentic vs. workflow patterns, decomposition (Steps 05–06) |
| 2 — Models, Prompting & Context Engineering | 13% | ◐ Model selection and pinning (Step 01); caching and context budgets (Step 02) |
| 3 — Integration | 19% | ✅ Capability bloat, protocol choice, auth — Step 01 §7 |
| 4 — Evaluation, Testing & Optimization | 16% | ○ Step 08 — the biggest gap |
| 5 — Governance, Safety & Risk | 14% | ◐ Least privilege (Step 01 §7); human-in-the-loop (Step 07) |
| 6 — Stakeholder Communication & Lifecycle | 14% | ⊘ Not a code topic; the step READMEs model the documentation practice |
| 7 — Developer Productivity & Operational Enablement | 7% | ◐ The repo's own skills and review workflow |

---

## Roadmap implied by the gaps

Ordered by difficulty, not by exam domain — each step is a working agent.

| Step | Builds | Closes |
|---|---|---|
| 02 — Multi-turn chat | Persistent session via `ClaudeSDKClient` | 1.7, 5.1 |
| 03 — Your own tools | In-process tools with `@tool`, deliberately confusable pairs, structured errors | 2.1, 2.2 |
| 04 — Structured output | JSON-schema extraction, validation-retry, few-shot | 4.2, 4.3, 4.4 |
| 05 — Hooks and enforcement | `PreToolUse`/`PostToolUse`, a prerequisite gate, a threshold block | 1.4, 1.5 |
| 06 — Multi-agent research | Coordinator + subagents, parallel spawning, provenance, error propagation | 1.2, 1.3, 1.6, 5.3, 5.6 |
| 07 — Escalation and review | Escalation criteria, confidence routing, built-in tools on a codebase | 2.5, 5.2, 5.4, 5.5 |
| 08 — Batch and evaluation | Message Batches API, multi-pass review, measuring quality | 4.5, 4.6 |

Steps 05–06 together correspond to two of the exercises the Foundations guide sets out; step 04
corresponds to a third.
