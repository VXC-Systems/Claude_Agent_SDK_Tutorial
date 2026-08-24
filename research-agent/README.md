# Research agent

An agent that answers questions grounded in live web results, built up in stages. Each stage is a
complete, runnable program — not a draft of the next one.

## Steps

| Step | Shape | Status |
|---|---|---|
| [`01-one-shot/`](01-one-shot/) | One question in, one answer out. No conversation state. | Done |
| [`02-verbose-output/`](02-verbose-output/) | The same agent, fully instrumented — every message with its role, who actually executes the tool, how context grows each call, plus timings, tokens, cache and cost. | Done |
| `03-multiturn-chat/` | Interactive terminal chat, using the SDK's persistent-session client (`ClaudeSDKClient`) so follow-up questions build on earlier answers. | Not written yet |

Start at [step 01](01-one-shot/) — it introduces the agentic loop, MCP, tools and permissions from
scratch, and later steps assume it. Step 02 keeps the same agent and changes only what you can see
of it, which is the cheapest way to learn the message stream.

## Setup

Setup is shared across the whole tutorial and lives in the [project README](../README.md): clone,
install `uv`, `uv sync`, then copy `.env.example` to `.env` and add your keys.

This agent needs an **Anthropic API key** and a **Linkup API key** (free tier). Each step's README
says what it uses and why.
