# Domain Overview

## Purpose
Documents the business domain, core concepts, and terminology for the MCP Proxy add-on.

## Responsibilities
- Define core domain concepts and their relationships
- Provide a glossary of domain-specific terminology
- Document external integrations and data flow

## Non-Responsibilities
- Technical implementation details: see [Technical Context](../tech/README.md)
- File structure and module boundaries: see [Architecture](../tech/ARCHITECTURE.md)

## Overview

### Domain Classification
This project solves a protocol mismatch: MCP servers are distributed as stdio-based CLI tools, but Home Assistant's LLM integrations require HTTP (SSE) endpoints. The add-on packages `mcp-proxy` to bridge this gap locally.

Industry: Smart home / AI tooling infrastructure.

### Core Concepts

**MCP Server** -- a tool server conforming to the Model Context Protocol. Defined in `servers.json` by `command`, `args[]`, and optional `env{}`. Each server becomes a named SSE endpoint.

**servers.json** -- the user-editable config file at `/addon-configs/mcp_proxy/servers.json` (mapped to `/config/servers.json` inside the container). A JSON object with a top-level `mcpServers` key whose value is a flat map of server names to server definitions. Each definition has `command`, `args[]`, optional `env{}`, and optional `type` (e.g., `"stdio"`). Single source of truth for active MCP servers.

**SSE Endpoint** -- HTTP endpoint per server at `http://<host>:9876/servers/<name>/sse`. This is the interface consumed by HA LLM integrations.

**mcp-proxy** -- the third-party Python daemon that reads `servers.json`, spawns MCP servers as stdio subprocesses, and bridges stdio to HTTP. This add-on is a packaging wrapper around it.

**Add-on** -- the HA Supervisor concept for a managed Docker container. This project is a single add-on (`slug: mcp_proxy`) within an HA add-on repository.

**SUPERVISOR_TOKEN** -- an HA internal credential automatically present in every add-on container. Grants access to the HA Supervisor API. Its exposure to MCP subprocesses is controlled by the `pass_environment` option (default: off).

### Terminology Glossary

| Term | Definition |
|------|-----------|
| MCP | Model Context Protocol -- open protocol for exposing tool-call capabilities to LLMs |
| stdio transport | Default MCP mode: server reads JSON-RPC from stdin, writes to stdout |
| SSE | Server-Sent Events -- HTTP streaming protocol used as the MCP network transport |
| StreamableHTTP | Alternative MCP HTTP transport (newer than SSE), also supported |
| uvx | Astral's `uv tool run`; launches Python MCP servers from PyPI without persistent install |
| npx | Node.js package runner; launches JS/TS MCP servers from npm without persistent install |
| s6-overlay | Init system in HA base images; manages service startup and supervision |
| bashio | HA shell helper library providing config access, logging, and filesystem helpers |
| addon_config | HA filesystem mount type; maps `/addon-configs/<slug>/` to `/config/` in the container |
| Watchdog | HA feature that polls `/status` and restarts the add-on if it stops responding |

### External Integrations

| Integration | Role |
|------------|------|
| mcp-proxy (PyPI) | Core daemon; all HTTP serving and subprocess management |
| HA Supervisor | Manages add-on lifecycle, options, watchdog |
| GHCR | Pre-built image registry |
| Third-party MCP servers | User-configured; fetched and launched at runtime by npx/uvx |

### Security Considerations
- `pass_environment` defaults to `false` to prevent leaking `SUPERVISOR_TOKEN` to MCP subprocesses
- A malicious MCP server with access to `SUPERVISOR_TOKEN` could control the HA instance
- The add-on itself handles no user data; it is purely a network proxy

## Dependencies
- HA Supervisor API (for add-on lifecycle management)
- `mcp-proxy` upstream project (core functionality)
- User-configured MCP servers (runtime behavior)

## Design Decisions
- JSON config file over HA UI: MCP server definitions are deeply nested and don't fit HA's flat options schema
- Single port with path-based routing: avoids per-server port management
- Default calculator example: provides immediate feedback on first install

## Known Risks
- Tight coupling to `mcp-proxy` upstream; the `--named-server-config` CLI flag is the integration point -- if upstream renames it, the `run` script breaks silently
- First-run latency: uvx servers download packages on first use (30-60 seconds). npx servers are pre-installed at container startup (v0.2.3+), shifting that delay to add-on start time instead

## Extension Guidelines
- New domain concepts should be added to the glossary table above
- New external integrations should be documented in the integrations table
