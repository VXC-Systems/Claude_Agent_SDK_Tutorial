"""Step 01 — a one-shot research agent.

Asks Claude a single question. Claude may call Linkup's hosted web-search tool
(over MCP) before answering, then the run ends.

Usage:
    uv run python research_agent.py "your research question"
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

# Your keys belong in a .env file at the repository root — the folder holding
# pyproject.toml. Copy .env.example to .env there and fill it in.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# load_dotenv() never overwrites a variable that is already set, so the first
# source to define a key wins. Later calls are optional fallbacks: they are
# skipped silently when the file does not exist.
load_dotenv(PROJECT_ROOT / ".env")   # the documented path — use this one
load_dotenv()                        # any .env above the current directory
# The author keeps keys under ~/.config; delete this line unless you do too.
load_dotenv(Path.home() / ".config" / "linkup" / "linkup.env")

MODEL = "claude-haiku-4-5-20251001"


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
    if len(sys.argv) < 2:
        print('Usage: uv run python research_agent.py "your research question"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])

    linkup_key = require_env("LINKUP_API_KEY")
    require_env("ANTHROPIC_API_KEY")

    options = ClaudeAgentOptions(
        model=MODEL,
        # Three separate switches, each closing a different way that outside
        # configuration leaks into this run. See the README for what we hit.
        tools=[],            # no built-in tools (Read/Bash/WebSearch/...)
        setting_sources=[],  # ignore .mcp.json / CLAUDE.md / settings.json on disk
        cwd=tempfile.gettempdir(),  # run outside any project directory (portable)
        mcp_servers={
            "linkup": {
                "type": "http",
                "url": "https://mcp.linkup.so/mcp",
                # The key travels in a header, not the URL: query strings end up
                # in server logs, proxy logs and tracebacks.
                "headers": {"Authorization": f"Bearer {linkup_key}"},
            }
        },
        allowed_tools=["mcp__linkup__linkup-search"],
    )

    async for message in query(prompt=question, options=options):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            # Makes "the tool never connected" distinguishable from
            # "Claude decided it did not need the tool".
            for server in message.data.get("mcp_servers", []):
                print(f"[mcp: {server.get('name')} {server.get('status')}]")
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"[calling tool: {block.name}]")
        elif isinstance(message, ResultMessage):
            # total_cost_usd is Optional — it is absent on some error paths, and
            # formatting None would crash exactly when the run already failed.
            cost = (
                f" · ${message.total_cost_usd:.4f}"
                if message.total_cost_usd is not None
                else ""
            )
            print(f"\n--- {message.subtype}{cost} ---")


if __name__ == "__main__":
    asyncio.run(main())
