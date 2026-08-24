"""Step 02 — the same agent, with everything visible.

Identical behaviour to step 01: one question in, one answer out, with Linkup's
hosted web-search tool available over MCP. The difference is the output — every
message in the stream is rendered, so you can see the agent think, choose a
tool, receive a result, and finish.

Usage:
    uv run python research_agent.py "your research question"
    uv run python research_agent.py --full "..."    # no truncation of long values
    uv run python research_agent.py --raw  "..."    # dump every raw message too
"""

import asyncio
import dataclasses
import json
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

# Your keys belong in a .env file at the repository root — the folder holding
# pyproject.toml. Copy .env.example to .env there and fill it in.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")   # the documented path — use this one
load_dotenv()                        # any .env above the current directory
# The author keeps keys under ~/.config; delete this line unless you do too.
load_dotenv(Path.home() / ".config" / "linkup" / "linkup.env")

MODEL = "claude-haiku-4-5-20251001"
ALLOWED_TOOLS = ["mcp__linkup__linkup-search"]
PREVIEW_CHARS = 600   # how much of a long value to show unless --full


# ---------------------------------------------------------------- formatting

def _supports_colour() -> bool:
    """Colour only when attached to a terminal, and honour NO_COLOR."""
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


COLOUR = _supports_colour()
WIDTH = min(shutil.get_terminal_size((100, 24)).columns, 100)

_CODES = {
    "dim": "2", "bold": "1", "red": "31", "green": "32",
    "yellow": "33", "blue": "34", "magenta": "35", "cyan": "36",
}


def c(text: str, *styles: str) -> str:
    """Wrap text in ANSI styles, or return it unchanged when colour is off."""
    if not COLOUR or not styles:
        return text
    codes = ";".join(_CODES[s] for s in styles)
    return f"\033[{codes}m{text}\033[0m"


def rule(title: str, colour: str = "cyan") -> None:
    """A full-width section header."""
    bar = "─" * max(0, WIDTH - len(title) - 3)
    print(f"\n{c('──' + title + ' ' + bar, colour, 'bold')}")


def kv(key: str, value: object, indent: int = 2, width: int = 13) -> None:
    """One aligned key/value line."""
    print(f"{' ' * indent}{c(key.ljust(width), 'dim')}{value}")


def body(text: str, indent: int = 6, colour: str | None = None) -> None:
    """Wrapped block text, indented under its label."""
    pad = " " * indent
    for para in text.strip().split("\n"):
        if not para.strip():
            print()
            continue
        for line in textwrap.wrap(para, width=WIDTH - indent) or [""]:
            print(pad + (c(line, colour) if colour else line))


def clip(text: str, full: bool) -> tuple[str, str]:
    """Return (shown_text, note) — truncating unless --full was passed."""
    if full or len(text) <= PREVIEW_CHARS:
        return text, ""
    return text[:PREVIEW_CHARS], f"… truncated, {len(text):,} chars total (use --full)"


def num(n: object) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def render_raw(message: object) -> None:
    """Dump a whole message as JSON — the --raw escape hatch."""
    try:
        payload = dataclasses.asdict(message)          # SDK messages are dataclasses
    except TypeError:
        payload = {"repr": repr(message)}
    text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
    print(f"\n  {c('▸ raw ' + type(message).__name__, 'dim', 'bold')}")
    body(text, indent=6, colour="dim")


# ------------------------------------------------------------- renderers

def render_init(data: dict) -> None:
    """The one-off session banner: identity, servers, and tool inventory."""
    rule("SESSION INIT")
    kv("session", data.get("session_id", "?"))
    kv("model", data.get("model", "?"))
    kv("cwd", data.get("cwd", "?"))
    kv("auth via", data.get("apiKeySource", "?"))
    kv("permission", data.get("permissionMode", "?"))
    kv("cli", data.get("claude_code_version", "?"))

    servers = data.get("mcp_servers", [])
    print(f"\n  {c('MCP servers', 'bold')}")
    for s in servers:
        status = s.get("status", "?")
        colour = {"connected": "green", "failed": "red", "needs-auth": "yellow"}.get(status, "dim")
        print(f"    {c('●', colour)} {s.get('name'):<20} {c(status, colour)}")
    if not servers:
        print(f"    {c('(none)', 'dim')}")

    tools = data.get("tools", [])
    print(f"\n  {c('Tools', 'bold')}  "
          f"{c(f'{len(tools)} discovered · {len(ALLOWED_TOOLS)} allowed', 'dim')}")
    for t in tools:
        if t in ALLOWED_TOOLS:
            print(f"    {c('✓', 'green')} {t}  {c('← allowed', 'green', 'dim')}")
        else:
            print(f"    {c('·', 'dim')} {c(t, 'dim')}")
    if not tools:
        print(f"    {c('(none — built-ins are disabled)', 'dim')}")

    # Direct evidence for step 01's claim that saved memory is keyed by cwd.
    mem = (data.get("memory_paths") or {}).get("auto")
    if mem:
        print(f"\n  {c('memory path', 'dim')}  {c(mem, 'dim')}")


def render_turn_header(turn: int, message: AssistantMessage) -> None:
    """Open a turn and show the per-message facts that are actually reliable."""
    rule(f"TURN {turn}", "blue")
    kv("message", c(message.message_id or "?", "dim"))
    kv("model", message.model or "?")

    u = message.usage or {}
    parts = [
        f"input {num(u.get('input_tokens', 0))}",
        f"cache write {num(u.get('cache_creation_input_tokens', 0))}",
        f"cache read {num(u.get('cache_read_input_tokens', 0))}",
    ]
    kv("tokens in", c(" · ".join(parts), "dim"))
    if u.get("service_tier"):
        kv("tier", c(str(u["service_tier"]), "dim"))
    # Deliberately not printed per turn: output_tokens (the SDK reports a
    # snapshot here, not a final tally) and stop_reason (None until the run
    # ends). Both appear, correctly, in the SUMMARY.


def render_thinking(block: ThinkingBlock, est: int | None, full: bool) -> None:
    meta = f"{len(block.thinking):,} chars"
    if est:
        meta += f" · ~{est:,} tokens"
    print(f"\n  {c('▸ thinking', 'magenta', 'bold')}  {c(meta, 'dim')}")
    shown, note = clip(block.thinking, full)
    body(shown, colour="dim")
    if note:
        print(f"      {c(note, 'dim')}")


def render_tool_use(block: ToolUseBlock, full: bool) -> None:
    print(f"\n  {c('▸ tool call', 'yellow', 'bold')}  {c(block.name, 'yellow')}")
    kv("id", c(block.id, "dim"), indent=6, width=9)
    pretty = json.dumps(block.input, indent=2, ensure_ascii=False)
    shown, note = clip(pretty, full)
    print(f"      {c('input', 'dim')}")
    body(shown, indent=8)
    if note:
        print(f"        {c(note, 'dim')}")


def render_tool_result(block, full: bool) -> None:
    is_error = bool(getattr(block, "is_error", False))
    label, colour = ("tool error", "red") if is_error else ("tool result", "green")
    print(f"\n  {c('▸ ' + label, colour, 'bold')}  "
          f"{c('← ' + str(getattr(block, 'tool_use_id', '?')), 'dim')}")

    content = getattr(block, "content", "")
    # MCP returns a list of typed parts; flatten the text ones for display.
    if isinstance(content, list):
        text = "\n".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
        kv("parts", len(content), indent=6, width=9)
    else:
        text = str(content)
    kv("size", f"{len(text):,} chars", indent=6, width=9)
    shown, note = clip(text, full)
    body(shown, indent=8, colour="dim")
    if note:
        print(f"        {c(note, 'dim')}")


def render_answer(text: str) -> None:
    print(f"\n  {c('▸ answer', 'green', 'bold')}")
    body(text, indent=6)


def render_summary(m: ResultMessage) -> None:
    rule("SUMMARY", "cyan")
    ok = not m.is_error
    kv("outcome", f"{c(m.subtype, 'green' if ok else 'red', 'bold')}"
                  f"{c(' · ' + m.stop_reason, 'dim') if m.stop_reason else ''}")
    kv("turns", m.num_turns)
    kv("duration", f"{m.duration_ms / 1000:.2f} s"
                   f"{c(f'   (API {m.duration_api_ms / 1000:.2f} s)', 'dim')}")
    kv("session", c(m.session_id, "dim"))

    usage = m.usage or {}
    if usage:
        print(f"\n  {c('Tokens (whole run)', 'bold')}")
        rows = [
            ("input", usage.get("input_tokens")),
            ("output", usage.get("output_tokens")),
            ("thinking", (usage.get("output_tokens_details") or {}).get("thinking_tokens")),
            ("cache write", usage.get("cache_creation_input_tokens")),
            ("cache read", usage.get("cache_read_input_tokens")),
        ]
        for name, value in rows:
            if value is not None:
                print(f"    {c(name.ljust(13), 'dim')}{num(value):>10}")
        # Only worth saying when a cache was actually populated but not reused.
        if usage.get("cache_creation_input_tokens") and not usage.get("cache_read_input_tokens"):
            print(f"    {c('cache written but not read — a repeat run within the', 'dim')}")
            print(f"    {c('cache window would read it back and cost less', 'dim')}")

    # Per-model detail: real cost, and how much of the context window was used.
    for name, mu in (m.model_usage or {}).items():
        get = mu.get if isinstance(mu, dict) else lambda k, d=None: getattr(mu, k, d)
        print(f"\n  {c('Model', 'bold')}  {c(name, 'dim')}")
        window = get("contextWindow")
        used = (get("inputTokens") or 0) + (get("cacheCreationInputTokens") or 0) \
            + (get("cacheReadInputTokens") or 0)
        if window:
            print(f"    {c('context'.ljust(13), 'dim')}{num(used):>10}"
                  f"{c(f' / {num(window)}  ({used / window:.1%})', 'dim')}")
        if get("maxOutputTokens"):
            print(f"    {c('max output'.ljust(13), 'dim')}{num(get('maxOutputTokens')):>10}")
        if get("costUSD") is not None:
            print(f"    {c('cost'.ljust(13), 'dim')}{'$' + format(get('costUSD'), '.6f'):>10}")

    denials = m.permission_denials or []
    if denials:
        print(f"\n  {c('Permission denials', 'yellow', 'bold')}")
        for d in denials:
            print(f"    {d}")

    if m.errors:
        print(f"\n  {c('Errors', 'red', 'bold')}")
        for e in m.errors:
            print(f"    {c(str(e), 'red')}")

    if m.total_cost_usd is not None:
        print()
        kv("total cost", c(f"${m.total_cost_usd:.6f}", "bold"))


# ------------------------------------------------------------------- main

def require_env(name: str) -> str:
    """Return an environment variable, or exit with an actionable message."""
    value = os.environ.get(name)
    if not value:
        sys.exit(
            f"Missing {name}.\n"
            f"Copy .env.example to .env in {PROJECT_ROOT} and add your key."
        )
    return value


async def main() -> None:
    flags = {"--full", "--raw"}
    args = [a for a in sys.argv[1:] if a not in flags]
    full = "--full" in sys.argv
    raw = "--raw" in sys.argv
    if not args:
        print('Usage: uv run python research_agent.py [--full] [--raw] "your question"')
        sys.exit(1)
    question = " ".join(args)

    linkup_key = require_env("LINKUP_API_KEY")
    require_env("ANTHROPIC_API_KEY")

    options = ClaudeAgentOptions(
        model=MODEL,
        # Identical isolation to step 01 — see that step's README for why.
        tools=[],
        setting_sources=[],
        cwd=tempfile.gettempdir(),
        mcp_servers={
            "linkup": {
                "type": "http",
                "url": "https://mcp.linkup.so/mcp",
                "headers": {"Authorization": f"Bearer {linkup_key}"},
            }
        },
        allowed_tools=ALLOWED_TOOLS,
    )

    rule("QUESTION")
    body(question, indent=2)

    turn = 0
    current_message_id: str | None = None
    thinking_est: int | None = None

    async for message in query(prompt=question, options=options):
        if raw:
            render_raw(message)

        # --- system: the init banner, plus streaming thinking-token estimates
        if isinstance(message, SystemMessage):
            if message.subtype == "init":
                render_init(message.data)
            elif message.subtype == "thinking_tokens":
                thinking_est = message.data.get("estimated_tokens", thinking_est)

        # --- assistant: thinking, tool requests, and final prose
        elif isinstance(message, AssistantMessage):
            # Blocks sharing a message_id belong to one API message — that is
            # the real turn boundary, not a heuristic.
            if message.message_id != current_message_id:
                current_message_id = message.message_id
                turn += 1
                render_turn_header(turn, message)
            for block in message.content:
                if isinstance(block, ThinkingBlock):
                    render_thinking(block, thinking_est, full)
                    thinking_est = None
                elif isinstance(block, ToolUseBlock):
                    render_tool_use(block, full)
                elif isinstance(block, TextBlock):
                    render_answer(block.text)

        # --- user: tool results are handed back as a user-role turn
        elif isinstance(message, UserMessage):
            blocks = message.content if isinstance(message.content, list) else [message.content]
            for block in blocks:
                if type(block).__name__ == "ToolResultBlock":
                    render_tool_result(block, full)

        # --- result: the run is over
        elif isinstance(message, ResultMessage):
            render_summary(message)


if __name__ == "__main__":
    asyncio.run(main())
