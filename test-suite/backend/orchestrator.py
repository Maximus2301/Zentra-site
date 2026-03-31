"""
Orchestrator: loads agent prompts, runs each via Claude API tool-use loop,
streams progress events through an asyncio Queue, aggregates final reports.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

import anthropic

from tools import TOOL_SCHEMAS, dispatch_tool, set_safe_roots

# ── Constants ─────────────────────────────────────────────────────────────────

COMMANDS_DIR = Path.home() / ".claude" / "commands"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096
MAX_TOOL_ITERATIONS = 25

AGENT_META = {
    "test-ui":        {"file": "test-ui.md",        "label": "UI/UX Test Lead",          "color": "#8b5cf6"},
    "test-logic":     {"file": "test-logic.md",      "label": "Business Logic Lead",      "color": "#3b82f6"},
    "test-data":      {"file": "test-data.md",       "label": "Data & Parsing Lead",      "color": "#10b981"},
    "test-security":  {"file": "test-security.md",   "label": "Security & Privacy Lead",  "color": "#ef4444"},
    "test-e2e":       {"file": "test-e2e.md",        "label": "End-to-End Flow Lead",     "color": "#f59e0b"},
    "threat-analysis":{"file": "threat-analysis.md", "label": "Threat Analysis Lead",     "color": "#06b6d4"},
}


# ── Prompt loader ─────────────────────────────────────────────────────────────

def load_agent_prompt(agent_key: str, target: str) -> str:
    meta = AGENT_META[agent_key]
    path = COMMANDS_DIR / meta["file"]

    if not path.exists():
        return (
            f"You are a {meta['label']}. "
            f"Analyse the target '{target}' using the available tools and produce a "
            "structured test report with severity-rated findings."
        )

    text = path.read_text(encoding="utf-8")

    # Strip YAML frontmatter (--- ... ---)
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].strip()

    # Replace $ARGUMENTS placeholder
    text = text.replace("**$ARGUMENTS**", f"**{target}**")
    text = text.replace("$ARGUMENTS", target)

    return text


def get_agents_list() -> list[dict]:
    result = []
    for key, meta in AGENT_META.items():
        path = COMMANDS_DIR / meta["file"]
        description = ""
        if path.exists():
            first_line = path.read_text(encoding="utf-8", errors="replace")
            m = __import__("re").search(r"description:\s*(.+)", first_line)
            if m:
                description = m.group(1).strip()
        result.append({
            "key": key,
            "label": meta["label"],
            "color": meta["color"],
            "description": description or meta["label"],
        })
    return result


# ── Per-agent runner ──────────────────────────────────────────────────────────

async def run_agent(
    client: anthropic.AsyncAnthropic,
    agent_key: str,
    target: str,
    target_type: str,
    emit: Callable,
) -> str:
    meta = AGENT_META[agent_key]
    label = meta["label"]

    await emit({"type": "agent_start", "agent": agent_key, "label": label})

    system_prompt = load_agent_prompt(agent_key, target)

    if target_type == "url":
        user_msg = (
            f"Target: {target}\n"
            "Target type: Web URL\n\n"
            "Use the available tools to thoroughly audit this web target. "
            "Start with fetch_webpage to get page content, then check_security_headers, "
            "extract_links to discover pages, and take_screenshot if visual analysis helps.\n\n"
            "Produce a complete structured test report following your report format exactly."
        )
    else:
        user_msg = (
            f"Target: {target}\n"
            "Target type: Local codebase / file path\n\n"
            "Use the available tools to thoroughly audit this codebase. "
            "Start with list_files to understand the project structure, "
            "then read_file to inspect key files, and search_in_code to find patterns.\n\n"
            "Produce a complete structured test report following your report format exactly."
        )

    messages = [{"role": "user", "content": user_msg}]
    iteration = 0
    final_report = ""

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1

        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
        except anthropic.APIError as e:
            await emit({"type": "agent_error", "agent": agent_key, "label": label, "error": str(e)})
            return f"**Agent error:** {e}"

        # Collect text blocks from this response
        text_blocks = [b.text for b in response.content if hasattr(b, "text") and b.text]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if text_blocks:
            preview = " ".join(text_blocks)[:200].replace("\n", " ")
            await emit({
                "type": "progress",
                "agent": agent_key,
                "label": label,
                "message": preview,
            })

        # Done — no more tool calls
        if response.stop_reason == "end_turn" and not tool_uses:
            final_report = "\n\n".join(text_blocks)
            await emit({
                "type": "agent_done",
                "agent": agent_key,
                "label": label,
                "report": final_report,
            })
            return final_report

        # Append assistant turn (full content list — required by API)
        messages.append({"role": "assistant", "content": response.content})

        # Execute all tool calls and collect results in ONE user turn
        tool_results = []
        for tool_use in tool_uses:
            await emit({
                "type": "tool_call",
                "agent": agent_key,
                "label": label,
                "tool": tool_use.name,
                "input_preview": json.dumps(tool_use.input)[:120],
            })

            result_str = await dispatch_tool(tool_use.name, tool_use.input)

            # Preview for the log
            try:
                result_obj = json.loads(result_str)
                preview = str(result_obj)[:150]
            except Exception:
                preview = result_str[:150]

            await emit({
                "type": "tool_result",
                "agent": agent_key,
                "label": label,
                "tool": tool_use.name,
                "result_preview": preview,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_str[:8000] or "(tool returned no output)",
            })

        # All tool results go in ONE user message (only if non-empty)
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # End turn with tool uses should not happen, but handle it
        if response.stop_reason == "end_turn":
            final_report = "\n\n".join(text_blocks)
            break

    if not final_report:
        # Extract whatever text we have from the last response
        final_report = "\n\n".join(text_blocks) if text_blocks else "No report generated."

    await emit({
        "type": "agent_done",
        "agent": agent_key,
        "label": label,
        "report": final_report,
    })
    return final_report


# ── Suite runner ──────────────────────────────────────────────────────────────

async def run_suite(
    run_id: str,
    target: str,
    target_type: str,
    agent_keys: list[str],
    queue: asyncio.Queue,
    store: dict,
) -> None:
    async def emit(event: dict) -> None:
        enriched = {**event, "run_id": run_id, "ts": datetime.utcnow().isoformat()}
        store["events"].append(enriched)
        await queue.put(enriched)

    # Set path safety roots
    safe_roots = [str(Path.home() / ".claude" / "commands")]
    if target_type == "path":
        safe_roots.append(target)
    set_safe_roots(safe_roots)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        await emit({"type": "fatal_error", "error": "ANTHROPIC_API_KEY environment variable not set."})
        await queue.put(None)
        return

    client = anthropic.AsyncAnthropic(api_key=api_key)
    valid_keys = [k for k in agent_keys if k in AGENT_META]

    await emit({
        "type": "suite_start",
        "agents": valid_keys,
        "target": target,
        "target_type": target_type,
    })

    reports: dict[str, str] = {}

    # Run agents sequentially — easier to follow in the log
    for key in valid_keys:
        try:
            report = await run_agent(client, key, target, target_type, emit)
            reports[key] = report
        except Exception as e:
            await emit({"type": "agent_error", "agent": key, "label": AGENT_META[key]["label"], "error": str(e)})
            reports[key] = f"**Agent crashed:** {e}"

    # Build consolidated report
    consolidated = _build_consolidated(target, reports)
    store["report"] = consolidated
    store["status"] = "complete"

    await emit({"type": "stream_end", "consolidated_report": consolidated})
    await queue.put(None)  # sentinel — closes the SSE generator


# ── Report aggregator ─────────────────────────────────────────────────────────

def _build_consolidated(target: str, reports: dict[str, str]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Consolidated Test Report",
        "",
        f"**Target:** `{target}`  ",
        f"**Generated:** {now}  ",
        f"**Agents run:** {len(reports)}  ",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    for i, key in enumerate(reports, 1):
        label = AGENT_META.get(key, {}).get("label", key)
        lines.append(f"{i}. [{label}](#{key.replace('-', '')})")

    lines += ["", "---", ""]

    for key, report in reports.items():
        label = AGENT_META.get(key, {}).get("label", key)
        anchor = key.replace("-", "")
        lines += [
            f'<a name="{anchor}"></a>',
            f"## {label}",
            "",
            report or "_No output from this agent._",
            "",
            "---",
            "",
        ]

    lines += [
        f"*Report generated by AI Test Suite Orchestrator — {now}*",
    ]

    return "\n".join(lines)
