# Home Assistant Apps
> HA add-on repository; currently hosts the MCP Proxy add-on bridging stdio-based MCP servers to SSE/StreamableHTTP endpoints via mcp-proxy.

## Quick Reference
- **Build**: CI via `home-assistant/builder` on push/PR to `main` (no local build script)
- **Run**: Deploy to HA instance with repo URL; no local dev server
- **Test**: No automated tests; validation by deploying to HA
- **Lint**: No linter configured (shellcheck/yamllint recommended but not set up)

## Architecture Overview
Single HA add-on following the s6-overlay service model. The `mcp-proxy/` directory contains the
entire add-on. `cont-init.d/` runs one-shot init (config validation), `services.d/mcp-proxy/run`
launches the `mcp-proxy` daemon which spawns MCP servers as stdio subprocesses and exposes them
as SSE endpoints on port 9876. User config lives in `servers.json` (JSON file, not HA UI).
See [ARCHITECTURE.md](docs/tech/ARCHITECTURE.md) for data flow and module boundaries.

## Tech Stack
- Shell (Bash) with `bashio` helpers, YAML configs, Dockerfile
- Base: Debian trixie HA images (`ghcr.io/home-assistant/{arch}-base-debian:trixie`)
- `mcp-proxy` installed via `uv tool install` at `/usr/local/uv-tools/bin/mcp-proxy`
- Node.js + npm (for npx), Python 3 (for uvx), build-essential (for native deps)
- CI: GitHub Actions with `home-assistant/builder`, images pushed to GHCR

## Core Conventions
- All shell scripts use `#!/usr/bin/with-contenv bashio` shebang, never plain bash
- Always use full paths to uv-tool binaries in s6 scripts (Dockerfile `ENV PATH` is NOT available)
- Write `finish` scripts in bash, not `execlineb` (s6 binaries not on PATH in HA's s6-overlay v3)
- Use `/run/s6/basedir/bin/halt` to halt the supervision tree
- Shell: 4-space indent, quoted braced vars (`"${var}"`), YAML: 2-space indent
- See [CONVENTIONS.md](docs/tech/CONVENTIONS.md) for full style guide

## Business Domain
Bridges stdio MCP servers (npx/uvx) to SSE endpoints for HA LLM integrations, replacing
the need for a remote proxy instance. Core config is `servers.json` mapping server names
to commands. See [Domain Overview](docs/domain/OVERVIEW.md) for concepts and glossary.

## Release Workflow
Every release requires these steps:
1. Bump `version` in `mcp-proxy/config.yaml` (semver)
2. Update `mcp-proxy/CHANGELOG.md` with new version section
3. The `image` field stays as `ghcr.io/slettmayer/mcp-proxy` (no tag -- HA appends version)
4. Merge PR to `main`, then create GitHub release:
   ```bash
   gh release create v<version> --target main --title "v<version>" --notes "..."
   ```

## Critical Warnings
- `config.yaml` MUST have an `image` field or HA builds locally instead of pulling from GHCR
- `pass_environment` leaks `SUPERVISOR_TOKEN` to MCP servers -- default is off for a reason
- `home-assistant/builder@master` is unpinned; upstream changes can break builds
- Never place `servers.json` inside `rootfs/`; user config lives at `/config/servers.json` via `addon_config:rw` mount

## Branch Protection
- `main` requires PRs with passing CI checks -- no direct pushes

## Structural Risks
- No `.gitignore` -- risk of committing secrets (e.g., `servers.json` with API keys in `rootfs/`)
- No shellcheck or yamllint in CI; script errors only caught at runtime
- No automated tests; validation is manual HA deployment
- `ghcr.io/astral-sh/uv:latest` is unpinned; breaking changes can silently affect builds
- Qodana/CheckStyle configs are dead JVM scaffolding (no Java in project) -- should be removed
- Doc-only PRs rely on the `gate` job (which passes when `build` is skipped); branch protection must require `gate` not `build`

## Detailed Guides
- [Technical Context](docs/tech/README.md) -- architecture, tech stack, conventions, infrastructure
- [Domain Context](docs/domain/README.md) -- business domain, concepts, terminology, integrations
- [Documentation Contributing Guide](docs/README.md) -- how to maintain these docs
