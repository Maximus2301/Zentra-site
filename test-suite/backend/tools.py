"""
Tool implementations and Anthropic tool schemas for the test suite orchestrator.
Each tool returns a plain string — the Anthropic API requires tool_result content to be str.
"""

import os
import re
import json
import base64
import asyncio
from pathlib import Path
from typing import Any

import httpx


# ── Path safety ───────────────────────────────────────────────────────────────

_SAFE_ROOTS: list[Path] = []


def set_safe_roots(roots: list[str]) -> None:
    global _SAFE_ROOTS
    _SAFE_ROOTS = [Path(r).resolve() for r in roots if r]


def _is_safe_path(path: str) -> bool:
    if not _SAFE_ROOTS:
        return True  # no restrictions set
    try:
        resolved = Path(path).resolve()
        return any(
            resolved == root or str(resolved).startswith(str(root) + os.sep)
            for root in _SAFE_ROOTS
        )
    except Exception:
        return False


# ── Tool implementations ──────────────────────────────────────────────────────

async def fetch_webpage(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "TestSuiteOrchestrator/1.0 (security-audit-bot)"},
        ) as client:
            r = await client.get(url)

        # Strip script/style blocks to reduce noise
        html = r.text
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<[^>]+>", " ", html)  # strip all tags
        html = re.sub(r"\s+", " ", html).strip()

        result = {
            "status_code": r.status_code,
            "final_url": str(r.url),
            "content_type": r.headers.get("content-type", ""),
            "content_length_raw": len(r.text),
            "text_preview": html[:6000],
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def check_security_headers(url: str) -> str:
    important = [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
        "x-xss-protection",
        "cache-control",
        "access-control-allow-origin",
    ]
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            try:
                r = await client.head(url)
            except Exception:
                r = await client.get(url)

        headers_lower = {k.lower(): v for k, v in r.headers.items()}
        results = {}
        for h in important:
            results[h] = headers_lower.get(h, "MISSING")

        return json.dumps(
            {"status_code": r.status_code, "url": str(r.url), "security_headers": results},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


def read_file(path: str) -> str:
    if not _is_safe_path(path):
        return json.dumps({"error": f"Path not allowed (outside safe roots): {path}"})
    p = Path(path)
    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})
    if p.is_dir():
        return json.dumps({"error": f"Path is a directory. Use list_files instead: {path}"})
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > 10000
        return json.dumps(
            {
                "path": str(p),
                "size_chars": len(content),
                "truncated": truncated,
                "content": content[:10000] + ("\n[... truncated ...]" if truncated else ""),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_files(directory: str, pattern: str = "**/*") -> str:
    if not _is_safe_path(directory):
        return json.dumps({"error": f"Path not allowed: {directory}"})
    base = Path(directory)
    if not base.exists():
        return json.dumps({"error": f"Directory not found: {directory}"})
    if not base.is_dir():
        return json.dumps({"error": f"Not a directory: {directory}"})
    try:
        files = [f for f in base.glob(pattern) if f.is_file()]
        file_list = sorted(str(f) for f in files)[:200]
        return json.dumps(
            {"directory": str(base), "pattern": pattern, "total_found": len(files), "files": file_list},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_in_code(directory: str, pattern: str, file_glob: str = "") -> str:
    if not _is_safe_path(directory):
        return json.dumps({"error": f"Path not allowed: {directory}"})
    base = Path(directory)
    if not base.exists():
        return json.dumps({"error": f"Directory not found: {directory}"})
    try:
        glob_pattern = file_glob if file_glob else "**/*"
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        for f in base.glob(glob_pattern):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        matches.append(f"{f}:{i}: {line.strip()}")
                        if len(matches) >= 60:
                            break
            except Exception:
                continue
            if len(matches) >= 60:
                break

        return json.dumps(
            {"pattern": pattern, "directory": directory, "matches_found": len(matches), "matches": matches},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def take_screenshot(url: str) -> str:
    try:
        from playwright.async_api import async_playwright  # type: ignore

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(url, timeout=20000, wait_until="networkidle")
            screenshot_bytes = await page.screenshot(full_page=False)
            await browser.close()

        b64 = base64.b64encode(screenshot_bytes).decode()
        return json.dumps(
            {"url": url, "status": "captured", "screenshot_base64": b64[:500] + "...[truncated for log]"},
        )
    except ImportError:
        return json.dumps(
            {
                "error": "playwright not installed",
                "install": "pip install playwright && playwright install chromium",
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def extract_links(url: str) -> str:
    try:
        from urllib.parse import urljoin, urlparse

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            r = await client.get(url, headers={"User-Agent": "TestSuiteOrchestrator/1.0"})

        base = str(r.url)
        hrefs = re.findall(r'href=["\']([^"\'#][^"\']*)["\']', r.text, re.IGNORECASE)
        forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
        imgs = re.findall(r'<img[^>]*src=["\']([^"\']+)["\']', r.text, re.IGNORECASE)

        abs_links = list(dict.fromkeys(urljoin(base, h) for h in hrefs))[:80]
        abs_forms = list(dict.fromkeys(urljoin(base, f) for f in forms))
        abs_imgs = list(dict.fromkeys(urljoin(base, i) for i in imgs))[:30]

        return json.dumps(
            {
                "base_url": base,
                "links_found": len(abs_links),
                "links": abs_links,
                "forms": abs_forms,
                "images": abs_imgs,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def dispatch_tool(name: str, inputs: dict) -> str:
    try:
        if name == "fetch_webpage":
            return await fetch_webpage(inputs["url"])
        elif name == "check_security_headers":
            return await check_security_headers(inputs["url"])
        elif name == "read_file":
            return read_file(inputs["path"])
        elif name == "list_files":
            return list_files(inputs["directory"], inputs.get("pattern", "**/*"))
        elif name == "search_in_code":
            return search_in_code(
                inputs["directory"], inputs["pattern"], inputs.get("file_glob", "")
            )
        elif name == "take_screenshot":
            return await take_screenshot(inputs["url"])
        elif name == "extract_links":
            return await extract_links(inputs["url"])
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except KeyError as e:
        return json.dumps({"error": f"Missing required parameter: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {e}"})


# ── Anthropic tool schemas ────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "fetch_webpage",
        "description": (
            "Fetch a webpage and return its visible text content, HTTP status code, "
            "and response headers. Script and style tags are stripped. Returns up to 6000 chars."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full URL to fetch"}},
            "required": ["url"],
        },
    },
    {
        "name": "check_security_headers",
        "description": (
            "Check the HTTP security response headers of a URL. "
            "Returns presence/absence of CSP, HSTS, X-Frame-Options, and other headers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to inspect"}},
            "required": ["url"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a source code or config file by its absolute path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in a directory. Supports glob patterns like **/*.dart or **/*.py.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Absolute directory path"},
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (default **/*). Examples: **/*.dart, **/*.py, **/*.js",
                    "default": "**/*",
                },
            },
            "required": ["directory"],
        },
    },
    {
        "name": "search_in_code",
        "description": (
            "Search for a regex or text pattern across all files in a directory. "
            "Returns matching lines with file path and line number."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to search in"},
                "pattern": {"type": "string", "description": "Regex or text to search for"},
                "file_glob": {
                    "type": "string",
                    "description": "File filter glob, e.g. *.dart or *.py (optional)",
                    "default": "",
                },
            },
            "required": ["directory", "pattern"],
        },
    },
    {
        "name": "take_screenshot",
        "description": (
            "Take a screenshot of a webpage using a headless browser. "
            "Requires playwright to be installed. Returns base64-encoded PNG."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to screenshot"}},
            "required": ["url"],
        },
    },
    {
        "name": "extract_links",
        "description": (
            "Extract all hyperlinks, form actions, and image sources from a webpage. "
            "Resolves relative URLs to absolute."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to parse"}},
            "required": ["url"],
        },
    },
]
