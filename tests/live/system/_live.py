"""Helpers for the live suite: run henhouse commands against the sandbox install and check the result in MySQL
and over HTTP.  Only used inside a sandbox built by tests/live/build_sandbox.sh (the runner checks)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

PROJECT = Path(os.environ.get("HH_LIVE_PROJECT", "/home/hentest/henhouse"))
PROJECT_NAME = PROJECT.name
HOST = os.environ.get("HH_LIVE_HOST", f"{PROJECT_NAME}.local")
MYSQL_ROOT_PW = os.environ.get("HH_LIVE_MYSQL_ROOT_PW", "Sandbox-Root-1")
HTTP_AUTH = ("admin", os.environ.get("HH_LIVE_HTTP_PW", "Sandbox-Pass-1"))

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FAILED = ("Action Error", "Action execution failed")


class HenError(AssertionError):
    pass


def hen(*args: str, expect_ok: bool | None = True, timeout: int = 120) -> str:
    """Run `python3 hen.py <args>` in the sandbox project; return its output without colour codes.

    expect_ok True: the command must succeed; False: it must fail; None: either.
    """
    proc = subprocess.run(["python3", "hen.py", *args], cwd=PROJECT, capture_output=True, text=True,
                          timeout=timeout)
    out = ANSI.sub("", proc.stdout + proc.stderr)
    failed = proc.returncode != 0 or any(f in out for f in FAILED)
    if expect_ok is True and failed:
        raise HenError(f"hen {' '.join(args)} failed:\n{out[-4000:]}")
    if expect_ok is False and not failed:
        raise HenError(f"hen {' '.join(args)} was expected to fail but did not:\n{out[-2000:]}")
    return out


def sql(query: str, params: tuple = (), database: str | None = None) -> List[Dict[str, Any]]:
    import pymysql
    conn = pymysql.connect(unix_socket="/var/run/mysqld/mysqld.sock", user="root", password=MYSQL_ROOT_PW,
                           database=database or PROJECT_NAME, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())
    finally:
        conn.close()


def http_get(path: str = "/") -> tuple[int, str]:
    req = urllib.request.Request(f"http://{HOST}{path}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def mcp(method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(f"http://{HOST}/mcp", data=body, headers={"Content-Type": "application/json"})
    import base64
    token = base64.b64encode(f"{HTTP_AUTH[0]}:{HTTP_AUTH[1]}".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def mcp_tool(name: str, **arguments: Any) -> Any:
    """Call an MCP tool and decode its first text item as JSON."""
    reply = mcp("tools/call", {"name": name, "arguments": arguments})
    assert "error" not in reply, reply
    return json.loads(reply["result"]["content"][0]["text"])


def page_id_from(out: str) -> int:
    m = re.search(r"Page ID:\s*│\s*(\d+)", out)
    assert m, f"no page id in output:\n{out[-2000:]}"
    return int(m.group(1))
