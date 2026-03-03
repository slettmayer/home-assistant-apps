# Architecture

## Purpose
Documents the project structure, module boundaries, and data flow for the HA add-on.

## Responsibilities
- Define the file layout and what each component owns
- Describe the runtime data flow from user config to SSE endpoint
- Document the s6 service lifecycle

## Non-Responsibilities
- Technology choices and versions: see [TECH-STACK.md](TECH-STACK.md)
- Code style rules: see [CONVENTIONS.md](CONVENTIONS.md)
- CI/CD pipeline: see [INFRASTRUCTURE.md](INFRASTRUCTURE.md)
- Domain concepts: see [Domain Overview](../domain/OVERVIEW.md)

## Overview

### Project Layout
The layout is framework-driven by the HA add-on specification:

```
home-assistant-apps/
├── repository.yaml              # HA recognizes this repo as an add-on source
├── .github/workflows/build.yaml # CI/CD
└── mcp-proxy/                   # The add-on (siblings would be additional add-ons)
    ├── config.yaml              # Add-on manifest
    ├── build.yaml               # Base image per architecture
    ├── Dockerfile               # Container build
    ├── CHANGELOG.md             # Shown in HA UI on updates
    ├── DOCS.md                  # User-facing documentation
    ├── translations/en.yaml     # HA UI labels
    └── rootfs/etc/              # Filesystem overlay into container
        ├── cont-init.d/         # One-shot init scripts (run once, in order)
        └── services.d/          # Supervised long-running services
```

### Module Boundaries

**Add-on packaging (`mcp-proxy/`)** -- owns the HA manifest, build config, user docs, changelog, and translations. Produces the installable add-on artifact.

**Container init (`rootfs/etc/cont-init.d/mcp-proxy-init.sh`)** -- owns first-run setup and runtime dependency pre-fetching. Creates default `servers.json` if missing, validates JSON syntax, logs configured server names, and pre-installs npm packages globally (`npm install -g`) for any `npx`-based servers to prevent first-connection timeout. Fails fast on invalid config. uvx servers are not pre-installed (they cache on first run).

**Service runtime (`rootfs/etc/services.d/mcp-proxy/run`)** -- owns the main process. Reads HA options via `bashio::config`, transforms values as needed (e.g., lowercase log level to uppercase), and `exec`s `mcp-proxy` with `--named-server-config /config/servers.json` and other CLI flags. The `exec` replaces the shell so s6 directly supervises the `mcp-proxy` process.

**Crash handler (`rootfs/etc/services.d/mcp-proxy/finish`)** -- owns abnormal-exit response. Non-zero, non-256 exit codes trigger s6 supervision tree halt, causing HA to mark the add-on as failed.

**Repository root (`repository.yaml`)** -- owns repo-level metadata for HA Supervisor discovery.

### Data Flow

1. User edits `/addon-configs/mcp_proxy/servers.json` (via File Editor, SSH, or Samba)
2. On container start, `mcp-proxy-init.sh` validates the JSON
3. `run` script reads HA options (`log_level`, `pass_environment`) and launches `mcp-proxy`
4. `mcp-proxy` reads `servers.json`, spawns each MCP server as a stdio subprocess
5. `mcp-proxy` listens on `0.0.0.0:9876`
6. HA LLM integration sends HTTP request to `http://<host>:9876/servers/<name>/sse`
7. `mcp-proxy` translates HTTP to JSON-RPC on subprocess stdin, reads stdout, streams response back over SSE

### s6 Service Lifecycle

```
container start
  → s6-overlay init
    → cont-init.d/mcp-proxy-init.sh (validate config)
      → services.d/mcp-proxy/run (exec mcp-proxy)
        → [running, supervised by s6]
          → on crash: finish script checks exit code
            → non-zero/non-256: halt supervision tree → container exits
            → HA watchdog detects failure → restarts add-on
```

## Dependencies
- HA Supervisor (manages add-on lifecycle, options, watchdog)
- s6-overlay (init system, service supervision)
- `mcp-proxy` binary at `/usr/local/uv-tools/bin/mcp-proxy`
- `bashio` shell helpers (config access, logging)

## Design Decisions
- `exec` in `run` script: replaces shell process so s6 supervises `mcp-proxy` directly (correct signal handling, clean shutdown)
- JSON config file over HA UI schema: MCP server definitions are deeply nested (`command`, `args[]`, `env{}`) and map poorly to HA's flat options schema
- Single port (9876): all servers multiplexed under `/servers/<name>/sse` paths; avoids per-server port management

## Known Risks
- All MCP servers share one process (`mcp-proxy`); a crash in `mcp-proxy` takes down all servers
- No per-server health checking; only the top-level `/status` endpoint is monitored

## Extension Guidelines
- To add another add-on to this repository, create a sibling directory next to `mcp-proxy/` with its own `config.yaml`, `build.yaml`, `Dockerfile`, and `rootfs/`
- Never place `servers.json` inside `rootfs/`; user config lives at `/config/servers.json` via the `addon_config:rw` mount, not inside the container image
- To add another init script, create a new file in `cont-init.d/` with a lexicographically later name
- To add another supervised service, create a new directory under `services.d/` with `run` and `finish` scripts
