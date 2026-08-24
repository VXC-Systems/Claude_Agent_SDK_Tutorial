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
| Exam mapping | Specific task statements from the published exam guides |
| Rough edges | Honest limitations, kept rather than hidden |
| Next | One line |

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
