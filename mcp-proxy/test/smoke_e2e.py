#!/usr/bin/env python3
"""Build-time end-to-end smoke test for the MCP Proxy add-on.

Starts mcp-proxy with a single named stdio server, then drives a real MCP
handshake (initialize -> notifications/initialized -> tools/list) over the
StreamableHTTP endpoint and asserts the child's tools come back.

This is the only test that exercises child-spawn-time dependency resolution,
which is where unbounded `mcp` specifiers actually break. Exits non-zero with
the proxy's own output attached on any failure.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# Overridable so the script can be run against a local venv install, not just
# the image's uv-tool path.
PROXY = os.environ.get("MCP_PROXY_BIN", "/usr/local/uv-tools/bin/mcp-proxy")
HOST = "127.0.0.1"
PORT = 19876
BASE = f"http://{HOST}:{PORT}"

# Must match the bootstrap default written by cont-init.d/mcp-proxy-init.sh.
SERVER_NAME = "geosphere"
SERVER_COMMAND = "uvx geosphere-mcp-server"

# Advisory only. The assertion that matters is that the child spawned and
# answered tools/list with a non-empty list -- that is what proves dependency
# resolution and the stdio bridge work. Pinning exact tool names would turn an
# upstream rename into a failed add-on build, which is not what this test is
# for, so a mismatch warns instead of failing.
EXPECTED_TOOLS = {"get_current_weather", "get_hourly_forecast", "get_daily_forecast"}

STARTUP_TIMEOUT = 60  # proxy binding its port; no package download involved
REQUEST_TIMEOUT = 300  # first request spawns the child, which uvx may download


def post(path, payload, session_id=None):
    """POST one JSON-RPC message; return (parsed_or_None, response_headers)."""
    headers = {
        "Content-Type": "application/json",
        # The server picks its framing from Accept; it may answer with either
        # a plain JSON body or a text/event-stream, so accept and parse both.
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id

    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = resp.read().decode()
        resp_headers = dict(resp.headers)

    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[len("data:") :].strip()
        if line.startswith("{"):
            return json.loads(line), resp_headers
    return None, resp_headers


def wait_for_status(proc):
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"mcp-proxy exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"{BASE}/status", timeout=5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            time.sleep(1)
    raise RuntimeError(f"/status did not become ready within {STARTUP_TIMEOUT}s")


def run_handshake():
    init, headers = post(
        f"/servers/{SERVER_NAME}/mcp",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "addon-build-smoke-test", "version": "1"},
            },
        },
    )
    if not init or "result" not in init:
        raise RuntimeError(f"initialize failed: {json.dumps(init)}")

    session_id = next(
        (v for k, v in headers.items() if k.lower() == "mcp-session-id"), None
    )
    if not session_id:
        raise RuntimeError(f"no mcp-session-id in initialize response: {headers}")

    post(
        f"/servers/{SERVER_NAME}/mcp",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        session_id,
    )

    listed, _ = post(
        f"/servers/{SERVER_NAME}/mcp",
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        session_id,
    )
    if not listed or "result" not in listed:
        raise RuntimeError(f"tools/list failed: {json.dumps(listed)}")

    tools = {t["name"] for t in listed["result"].get("tools", [])}
    if not tools:
        raise RuntimeError("tools/list returned an empty tool list")
    missing = EXPECTED_TOOLS - tools
    if missing:
        print(
            f"WARNING: expected tools not advertised: {sorted(missing)} "
            f"(got {sorted(tools)}) -- upstream may have renamed them",
            flush=True,
        )
    return sorted(tools)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = os.path.join(tmp, "smoke-servers.json")
        with open(config_path, "w") as fh:
            json.dump(
                {
                    "mcpServers": {
                        SERVER_NAME: {
                            "command": SERVER_COMMAND.split()[0],
                            "args": SERVER_COMMAND.split()[1:],
                        }
                    }
                },
                fh,
            )

        proc = subprocess.Popen(
            [PROXY, "--named-server-config", config_path, "--port", str(PORT), "--host", HOST],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            status = wait_for_status(proc)
            print(f"proxy ready: {json.dumps(status)}", flush=True)
            tools = run_handshake()
            print(f"OK: {SERVER_NAME} exposed {len(tools)} tools: {tools}", flush=True)
        except Exception as exc:
            print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
            proc.kill()
            output = proc.communicate(timeout=30)[0] or "(no output)"
            print("--- mcp-proxy output ---", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
