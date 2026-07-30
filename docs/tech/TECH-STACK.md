# Tech Stack

## Purpose
Documents the languages, frameworks, build tools, and runtime dependencies used in this project.

## Responsibilities
- Catalog all technologies and their roles in the system
- Document base image and multi-arch strategy
- Track external tool dependencies installed in the container

## Non-Responsibilities
- How files are organized: see [ARCHITECTURE.md](ARCHITECTURE.md)
- Coding style rules: see [CONVENTIONS.md](CONVENTIONS.md)
- CI/CD pipeline details: see [INFRASTRUCTURE.md](INFRASTRUCTURE.md)

## Overview

### Languages
- **Shell (Bash)** -- all runtime scripts use `bashio` (HA shell helper library)
- **YAML** -- all configuration and manifest files
- **Python 3** -- used at init time for JSON validation; also the language of `mcp-proxy` itself
- **Node.js** -- available in the container for `npx`-launched MCP servers (not application code)

### Frameworks
- **Home Assistant Add-on framework** -- dictates file structure (`config.yaml`, `build.yaml`, `rootfs/`), options schema, port mapping, watchdog, and filesystem mounts
- **s6-overlay** -- init system in HA base images; manages `cont-init.d/` one-shot scripts and `services.d/` supervised long-running services
- **mcp-proxy** (`github.com/sparfenyuk/mcp-proxy`) -- the core bridging daemon; installed via `uv tool install 'mcp-proxy==0.12.0' --with 'mcp>=1.17,<2'`. Both the tool and its transitive `mcp` SDK are pinned: `mcp-proxy` declares `mcp>=1.17.0` with no upper bound, and `mcp` 2.0.0 (2026-07-28) breaks 0.12.0 outright (`ImportError: cannot import name 'request_ctx' from 'mcp.server.lowlevel.server'`). Lift the `<2` bound only once upstream ships an mcp 2.x-compatible release

### Build Tools
- **uv / uvx** (Astral) -- Python tool manager; binaries sourced via `COPY --from=uv`, where `uv` is a named build stage pinned to `ghcr.io/astral-sh/uv:0.12.0`. The named-stage form (rather than an inline `COPY --from=ghcr.io/...`) is what makes the tag visible to Dependabot's docker parser, which reads `FROM` lines only. `uv tool install` installs `mcp-proxy` at build time into `/usr/local/uv-tools`; `uvx` is available at runtime for users to launch Python MCP servers. `UV_PYTHON_PREFERENCE=only-system` forces `uv` to use system Python 3 (never downloads its own interpreter)
- **npm / npx** -- installed in the container for users to launch Node.js MCP servers
- **home-assistant/builder** -- HA's official builder, used via its composable actions (`prepare-multi-arch-matrix`, `build-image`, `publish-multi-arch-manifest`) wrapping `docker buildx` for native per-arch multi-arch builds; pinned to SHA in workflow, managed by Dependabot (the monolithic `home-assistant/builder` action it replaced was deprecated in 2026.03.0)

### Base Image
- `ghcr.io/home-assistant/{arch}-base-debian:trixie` (Debian 13)
- Chosen for glibc compatibility with arbitrary third-party MCP server native dependencies
- Provides s6-overlay and `bashio` out of the box

### Key Runtime Libraries
- **bashio** -- HA shell helper (part of base image); used for logging, config access, filesystem checks
- **uv tool environment** -- `mcp-proxy` lives at `/usr/local/uv-tools/bin/mcp-proxy` with `UV_PYTHON_PREFERENCE=only-system` to reuse system Python

### API and Communication Patterns
- **SSE** -- primary transport; each MCP server exposed at `http://<host>:9876/servers/<name>/sse`
- **StreamableHTTP** -- alternative transport supported by `mcp-proxy` on the same port
- **stdio** -- internal transport between `mcp-proxy` and spawned MCP server subprocesses
- **HTTP health** -- `/status` endpoint on port 9876 used by HA watchdog

## Dependencies
- `ghcr.io/home-assistant/{arch}-base-debian:trixie` (base image)
- `ghcr.io/astral-sh/uv:0.12.0` (build-time binary copy for `uv`/`uvx`; pinned, Dependabot-monitored)
- `mcp-proxy==0.12.0` from PyPI with `mcp>=1.17,<2` (installed via `uv tool install`)
- Debian packages: `python3`, `python3-pip`, `python3-venv`, `python3-dev`, `nodejs`, `npm`, `build-essential`, `ca-certificates`, `curl`, `git` (`curl`/`git` enable MCP servers to make HTTPS calls and pull from git sources)

## Design Decisions
- Debian trixie over Alpine: glibc compatibility for arbitrary third-party MCP server native deps
- `uv` over `pip`: faster installs, isolated tool environments, multi-arch binary available via Docker COPY
- `build-essential` + `python3-dev` included: ensures MCP servers with C extensions can compile at runtime

## Known Risks
- Image size is large due to Debian base + build tools + Node.js + Python; this is an intentional tradeoff for compatibility
- The `mcp>=1.17,<2` bound keeps the image on the `mcp` 1.x line, which receives security fixes only. It cannot be lifted until `mcp-proxy` supports the 2.x SDK; if upstream goes dormant, that bound becomes a maintenance liability
- User-configured MCP servers are still resolved at runtime with whatever specifiers they declare. Pinning the add-on's own dependencies does not protect a server the user adds -- `DOCS.md` documents the failure mode and the `uvx --with` workaround
- The HA base image is pinned to the rolling `trixie` channel, not a digest, and Dependabot does not resolve the `BUILD_FROM` ARG -- base image changes arrive unannounced

## Extension Guidelines
- To add a new system dependency, add it to the `apt-get install` line in `mcp-proxy/Dockerfile`
- To change the base image, update both entries in `mcp-proxy/build.yaml`
