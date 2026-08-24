# Working in this repo

A hands-on Claude Agent SDK tutorial, written as preparation for the Anthropic Claude Certified
Architect certifications — Foundations (CCAR-F) first, Professional (CCAR-P) after.

## What this project is for

- Learn the Agent SDK by building working agents, and **document the learning as it happens**.
- Every step is a real, runnable program. No fragments, no pseudocode.
- **Keep the mistakes.** What broke and why is the most valuable content here; the happy path is
  already in the official docs. Never quietly sanitise a step into a clean narrative.

## Structure

Two levels. Each **agent** is a named folder; each **build stage** of that agent is a numbered
subfolder:

```
<agent-name>/
  README.md          the agent's steps, in order
  NN-short-name/
    *.py              the working code for this stage
    README.md         what it is, how it works, what we learned
```

A new agent is a new top-level folder. Numbered steps are only for stages of building *one* agent.
Number them in the order they were actually built.

## The step README template

Every step README follows the same shape, so readers learn where to look:

| Section | Contents |
|---|---|
| What you'll build | A real terminal transcript, before any theory |
| Concepts | Only what is new since the last step — defined, not assumed |
| Setup | The delta. Shared setup lives in the root README, never duplicated |
| Code walkthrough | Every function and parameter accounted for |
| Running it | Including what correct output looks like |
| **What we learned** | What broke, and why. Required — the section other tutorials lack |
| Design notes | Trade-offs and what the design does *not* handle (CCAR-P level) |
| **Exam topics covered** | See below — required in every step |
| Rough edges | Honest limitations, kept rather than hidden |
| Next | One line |

### The "Exam topics covered" section

**Every step must have one, and it must teach rather than index.** A bare table of task-statement
numbers is not enough — a learner cannot act on `2.3` alone. For each topic covered, give three
things:

1. **What the exam expects you to know** — the concept in plain words, paraphrased, including the
   anti-pattern it tests where there is one.
2. **Where to look in this step** — the specific output line, code block, or section that
   demonstrates it, so the learner can go and see it.
3. **How fully it is covered** — say plainly when a step only *shows* a problem that a later step
   solves. Overclaiming coverage is the failure mode here.

Group by exam and domain, and include the domain weight — it tells the learner how much the topic
is worth. Cover CCAR-P objectives alongside CCAR-F ones where the step earns it.

**Never reproduce exam-guide text, questions, or answers.** Paraphrase topics in your own words;
the guides are distributed through the Anthropic Partner Academy and are not public. Keep
[`EXAM-COVERAGE.md`](EXAM-COVERAGE.md) in sync whenever a step changes what is covered.

## How Claudiu wants this built

Learned from review during steps 01–02. These are settled; do not re-litigate them.

### Pace

- **Do not run ahead to the next step.** A step is finished when *he* says so, not when the code
  works. Expect several rounds of "this part isn't right" on a step that already runs, and treat
  each as a real defect rather than polish. Never close a message by pushing toward the next step.
- Answer the question actually asked before proposing anything further.

### Output that teaches

- **Use the real SDK field name for every value shown** — `usage.input_tokens`, `duration_ms`,
  `contextWindow`. Never a friendly relabel like "input" or "cost". He is learning names he will be
  examined on, and a prettier label hides the thing worth knowing.
- **Label anything derived as computed**, with its formula, so a calculated number is never
  mistaken for one the SDK reported.
- **Never show the same quantity twice under two names.** Token counts appear once, in the API's
  own snake_case; `model_usage` shows only fields that exist nowhere else. Redundancy reads as
  noise, not rigour.
- **The display must be structurally truthful.** Render each message as its own section labelled
  with its class, because the class *is* the role — a `ToolResultBlock` lives in a `UserMessage`
  and must never be drawn as part of an `AssistantMessage`. A layout that groups things wrongly
  teaches a wrong mental model, and no test will ever catch it.
- **Make the invisible visible**: who executes a tool, that the whole conversation is resent on
  every call, that the prompt itself is not a stream message. If a mechanism matters, print
  evidence of it rather than describing it in prose alone.
- **Truncate per kind of content.** Tool results are enormous and get clipped hard; the model's
  reasoning is short and is the interesting part, so it is shown in full. One global cap is wrong.
  Truncation always states the real size.

### Verification

- **Inspect the live stream before designing any display.** Field names are not a specification —
  `usage.output_tokens` reports a snapshot rather than a tally, and `stop_reason` is null on every
  assistant message. Both would have been printed as authoritative nonsense if written from the
  type declarations alone.
- **Exercise every path.** A run where the model answers from its own knowledge never touches the
  tool-call code. It looks finished and is not.
- When a review challenges a claim, **measure it** and report which way it went — including when
  the challenge was wrong.

### Explaining

- He asks *why*, not just *what*. "Two casings, watch out" is a worse answer than "they differ
  because the two objects come from opposite sides of the subprocess boundary". Explain the
  mechanism; the rule then follows from it and is remembered.
- Give exact copy-pasteable commands when he is going to run something himself, and say up front
  how large the output will be.

## Definition of done for a step

1. Code works, **verified by running it** — never "should work".
2. README written to the template above.
3. `student-review` skill run; findings fixed or consciously accepted.
4. `publish-audit` skill run; clean.
5. Indexed in the root README and the agent's README.

## Review skills

Two project-scoped skills in `.claude/skills/`. Both are **read-only and report-only** — they
diagnose, they do not fix, so the author decides what to accept.

| Skill | Perspective | Answers |
|---|---|---|
| `student-review` | A newcomer with no context | Is this followable? Is anything used before it's explained? |
| `publish-audit` | A security auditor | Would publishing this leak a key, private data, or a username? |

## Rules that do not bend

- **Never commit a credential.** Keys are loaded from a git-ignored `.env` in the project root, or
  from the environment. `.env.example` documents the shape with placeholders only. Never paste a
  real key into a README, a code comment, an issue, or a commit.
- **No private or work data.** This is a public learning repo: no employer-internal names, systems,
  customer data, internal hostnames, or credentials belonging to anything else.
- **No machine-specific absolute paths** in code or prose — they leak a username and break for
  every reader. Derive paths from `__file__` or `Path.home()`.
- **Verify claims before teaching them.** If a step asserts how the SDK behaves, that behaviour was
  measured, not assumed. When a measurement contradicts an earlier claim, correct the claim and say
  so.
