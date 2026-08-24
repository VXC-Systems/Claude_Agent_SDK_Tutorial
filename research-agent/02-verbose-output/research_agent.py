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
# Truncation caps, per kind of content. Tool results are the only thing that is
# reliably enormous (tens of thousands of characters); the model's reasoning and
# the tool arguments are short and are the interesting part, so they are shown in
# full at any sane length. --full removes every cap.
TOOL_RESULT_CHARS = 600
THINKING_CHARS = 4000
TOOL_INPUT_CHARS = 2000


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
    """One aligned key/value line, for prose labels."""
    print(f"{' ' * indent}{c(key.ljust(width), 'dim')}{value}")


def field(name: str, value: object, indent: int = 2, width: int = 37,
          note: str = "") -> None:
    """One aligned line whose label is the REAL SDK field name.

    Used everywhere a number comes straight off a message, so the name you read
    here is the name you use in code (and are asked about in the exam).
    """
    tail = f"  {c(note, 'dim')}" if note else ""
    print(f"{' ' * indent}{c(name.ljust(width), 'dim')}{str(value):>10}{tail}")


def body(text: str, indent: int = 6, colour: str | None = None) -> None:
    """Wrapped block text, indented under its label."""
    pad = " " * indent
    for para in text.strip().split("\n"):
        if not para.strip():
            print()
            continue
        for line in textwrap.wrap(para, width=WIDTH - indent) or [""]:
            print(pad + (c(line, colour) if colour else line))


def clip(text: str, full: bool, limit: int) -> tuple[str, str]:
    """Return (shown_text, note) — truncating at `limit` unless --full was passed."""
    if full or len(text) <= limit:
        return text, ""
    return text[:limit], f"… truncated, {len(text):,} chars total (use --full)"


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
    print(f"  {c('SystemMessage(subtype=\'init\').data', 'dim')}\n")
    for key in ("session_id", "model", "cwd", "apiKeySource",
                "permissionMode", "claude_code_version"):
        print(f"  {c(key.ljust(24), 'dim')}{data.get(key, '?')}")

    servers = data.get("mcp_servers", [])
    print(f"\n  {c('mcp_servers', 'bold')}")
    for s in servers:
        status = s.get("status", "?")
        colour = {"connected": "green", "failed": "red", "needs-auth": "yellow"}.get(status, "dim")
        print(f"    {c('●', colour)} {s.get('name'):<20} {c(status, colour)}")
    if not servers:
        print(f"    {c('(none)', 'dim')}")

    tools = data.get("tools", [])
    print(f"\n  {c('tools', 'bold')}  "
          f"{c(f'{len(tools)} discovered · {len(ALLOWED_TOOLS)} in allowed_tools', 'dim')}")
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
        print(f"\n  {c('memory_paths.auto'.ljust(24), 'dim')}{c(mem, 'dim')}")


def render_turn_header(turn: int, message: AssistantMessage) -> None:
    """Open a turn and show the per-message facts that are actually reliable."""
    rule(f"TURN {turn}", "blue")
    print(f"  {c('AssistantMessage', 'dim')}\n")
    print(f"  {c('message_id'.ljust(37), 'dim')}{message.message_id or '?'}")
    print(f"  {c('model'.ljust(37), 'dim')}{message.model or '?'}")

    # AssistantMessage.usage — snake_case, unlike model_usage. Real names only.
    u = message.usage or {}
    for name in ("input_tokens", "cache_creation_input_tokens",
                 "cache_read_input_tokens"):
        field(f"usage.{name}", num(u.get(name, 0)))
    if u.get("service_tier"):
        print(f"  {c('usage.service_tier'.ljust(37), 'dim')}"
              f"{str(u['service_tier']):>10}")
    # Deliberately not printed per turn: usage.output_tokens (the SDK reports a
    # snapshot here, not a final tally) and stop_reason (None until the run
    # ends). Both appear, correctly, in the SUMMARY.


def render_thinking(block: ThinkingBlock, est: int | None, full: bool) -> None:
    meta = f"{len(block.thinking):,} chars"
    if est:
        meta += f" · ~{est:,} tokens"
    print(f"\n  {c('▸ thinking', 'magenta', 'bold')}  {c(meta, 'dim')}")
    shown, note = clip(block.thinking, full, THINKING_CHARS)
    body(shown, colour="dim")
    if note:
        print(f"      {c(note, 'dim')}")


def render_tool_use(block: ToolUseBlock, full: bool) -> None:
    print(f"\n  {c('▸ tool call', 'yellow', 'bold')}  {c(block.name, 'yellow')}")
    kv("id", c(block.id, "dim"), indent=6, width=9)
    pretty = json.dumps(block.input, indent=2, ensure_ascii=False)
    shown, note = clip(pretty, full, TOOL_INPUT_CHARS)
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
    shown, note = clip(text, full, TOOL_RESULT_CHARS)
    body(shown, indent=8, colour="dim")
    if note:
        print(f"        {c(note, 'dim')}")


def render_answer(text: str) -> None:
    print(f"\n  {c('▸ answer', 'green', 'bold')}")
    body(text, indent=6)


def render_summary(m: ResultMessage) -> None:
    """Every number here is labelled with the field it came from."""
    rule("SUMMARY", "cyan")
    print(f"  {c('ResultMessage', 'dim')}\n")

    ok = not m.is_error
    print(f"  {c('subtype'.ljust(37), 'dim')}"
          f"{c(m.subtype, 'green' if ok else 'red', 'bold')}")
    print(f"  {c('stop_reason'.ljust(37), 'dim')}{m.stop_reason}")
    print(f"  {c('is_error'.ljust(37), 'dim')}{m.is_error}")
    field("num_turns", m.num_turns)
    field("duration_ms", num(m.duration_ms), note=f"= {m.duration_ms / 1000:.2f} s")
    field("duration_api_ms", num(m.duration_api_ms),
          note=f"= {m.duration_api_ms / 1000:.2f} s")
    print(f"  {c('session_id'.ljust(37), 'dim')}{m.session_id}")
    if m.total_cost_usd is not None:
        field("total_cost_usd", f"${m.total_cost_usd:.6f}")

    usage = m.usage or {}
    if usage:
        print(f"\n  {c('ResultMessage.usage', 'bold')}  {c('(snake_case)', 'dim')}")
        for name in ("input_tokens", "output_tokens",
                     "cache_creation_input_tokens", "cache_read_input_tokens"):
            if usage.get(name) is not None:
                field(f"usage.{name}", num(usage[name]), indent=4)
        thinking = (usage.get("output_tokens_details") or {}).get("thinking_tokens")
        if thinking is not None:
            field("usage.output_tokens_details.thinking_tokens", num(thinking),
                  indent=4, width=45)
        # Only worth saying when a cache was populated but never reused.
        if usage.get("cache_creation_input_tokens") and not usage.get("cache_read_input_tokens"):
            print(f"    {c('cache written but not read — a repeat run within the', 'dim')}")
            print(f"    {c('cache window would read it back and cost less', 'dim')}")

    # model_usage uses camelCase for the SAME quantities. Not a typo — worth
    # knowing, because the two dicts sit on the same message.
    for name, mu in (m.model_usage or {}).items():
        get = mu.get if isinstance(mu, dict) else (lambda k, d=None: getattr(mu, k, d))
        print(f"\n  {c(f'ResultMessage.model_usage[{name!r}]', 'bold')}  "
              f"{c('(camelCase — note the difference)', 'dim')}")
        for key in ("inputTokens", "outputTokens", "cacheCreationInputTokens",
                    "cacheReadInputTokens", "contextWindow", "maxOutputTokens"):
            if get(key) is not None:
                field(key, num(get(key)), indent=4)
        if get("costUSD") is not None:
            field("costUSD", f"${get('costUSD'):.6f}", indent=4)

        window = get("contextWindow")
        used = ((get("inputTokens") or 0) + (get("cacheCreationInputTokens") or 0)
                + (get("cacheReadInputTokens") or 0))
        if window:
            print(f"\n  {c('computed (not an SDK field)', 'bold')}")
            field("context used", num(used), indent=4,
                  note=f"{used / window:.1%} of contextWindow")
            print(f"      {c('= inputTokens + cacheCreationInputTokens '
                             '+ cacheReadInputTokens', 'dim')}")

    denials = m.permission_denials or []
    if denials:
        print(f"\n  {c('permission_denials', 'yellow', 'bold')}")
        for d in denials:
            print(f"    {d}")

    if m.errors:
        print(f"\n  {c('errors', 'red', 'bold')}")
        for e in m.errors:
            print(f"    {c(str(e), 'red')}")


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
