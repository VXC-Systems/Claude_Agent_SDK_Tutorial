# Claude Agent SDK — a hands-on tutorial

Learn the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) by building real
agents, one working step at a time.

This is written as **preparation for the Anthropic Claude Certified Architect certifications** —
**Foundations** (CCAR-F) first, **Professional** (CCAR-P) after — but it is a normal SDK tutorial
too. You do not need to be sitting an exam for it to be useful.

**What makes it different:** it keeps the mistakes. Every step has a *What we learned* section
recording what actually broke and why. Those sections are the reason this exists — the happy path
is already in the official docs.

---

## Start here

| Step | What you'll build | Concepts |
|---|---|---|
| [`research-agent/01-one-shot/`](research-agent/01-one-shot/) | A CLI agent that searches the live web before answering | Agentic loop · MCP · tools · permissions · isolation |

More steps are added as they're built. Each is a complete, runnable program, not a fragment.

## Setup

```bash
git clone https://github.com/VXC-Systems/Claude_Agent_SDK_Tutorial.git
cd Claude_Agent_SDK_Tutorial

# install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS / Linux
# Windows PowerShell: irm https://astral.sh/uv/install.ps1 | iex
# or, any platform with pipx: pipx install uv

uv sync
cp .env.example .env      # then add your keys
```

You need an **Anthropic API key** (paid — runs cost cents) and a **Linkup API key** for the
research-agent steps. `.env` lives in this folder and is git-ignored. Each step's README explains
what it needs and why.

Developed on macOS; the code avoids platform-specific paths and should run on Linux and Windows,
though only macOS has been exercised.

---

## How this is organised

Two levels. Each **agent** is a named folder; each **build stage** of that agent is a numbered
folder inside it.

```
research-agent/          the agent
├── README.md            its steps, in order
└── 01-one-shot/         one stage — code + a README that teaches it
```

A new agent is a new top-level folder. Numbered steps are only for the stages of building *one*
agent, so you can read a single agent's arc from simple to complete.

Every step README follows the same shape: what you'll build → new concepts → setup → code
walkthrough → run it → **what we learned** → design notes → exam mapping → rough edges → next.

## Certification coverage

The exams are published by Anthropic; download the guides from the Anthropic Partner Academy. Each
step's §8 maps its content to specific task statements.

**Foundations (CCAR-F)** — 60 items, 120 minutes, scaled cut score 720/1000.

| Domain | Weight | Covered here |
|---|---|---|
| 1 — Agentic Architecture & Orchestration | 27% | **Yes** — the core of this tutorial |
| 2 — Tool Design & MCP Integration | 18% | **Yes** |
| 3 — Claude Code Configuration & Workflows | 20% | **Mostly not** — a separate tutorial. Partial exception: the review skills in `.claude/skills/` |
| 4 — Prompt Engineering & Structured Output | 20% | **Yes**, in later steps |
| 5 — Context Management & Reliability | 15% | **Yes** |

So this tutorial covers roughly **80%** of the Foundations blueprint. Domain 3 is about configuring
Claude Code rather than building with the SDK, and belongs elsewhere.

**Professional (CCAR-P)** — 63 items, seven domains, and a different character: architectural
judgement and trade-offs rather than SDK mechanics. There are no prescribed exercises; the guide
asks you to *build and operate an end-to-end solution*. Each step's **Design notes** section is
written for that level — why a design went the way it did, and what it does not handle.

## Contributing / reviewing

Two project-scoped Claude Code skills live in [`.claude/skills/`](.claude/skills/) and are used on
every step before it is considered done:

| Skill | Perspective |
|---|---|
| `student-review` | A newcomer with no context — is anything unexplained, out of order, or impossible to run? |
| `publish-audit` | A security auditor — would publishing this leak a key, private data, or a username? |

Both are read-only: they report, they don't fix. They are the reason step 01 ships with a
`.gitignore`, a stated `.env` location, and a guard on an optional field that would otherwise have
crashed on the error path — every one of those was a review finding, not foresight.

## Licence

[MIT](LICENSE) — use it, fork it, teach from it.
