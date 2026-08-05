# Changelog

## 0.3.1

- Bump astral-sh/uv (Dependabot)

## 0.3.0

- Pin `mcp-proxy` to 0.12.0 and constrain its `mcp` SDK to `>=1.17,<2`. `mcp` 2.0.0 is a breaking release that `mcp-proxy` 0.12.0 does not support (`ImportError: cannot import name 'request_ctx'`); because `mcp-proxy` declares `mcp>=1.17.0` with no upper bound, the next image rebuild would have installed it
- Pin the `uv`/`uvx` source image to `ghcr.io/astral-sh/uv:0.12.0` (was `:latest`), declared as a named build stage so Dependabot tracks it
- **Breaking for fresh installs:** the default `servers.json` example is now `geosphere-mcp-server` instead of `mcp-server-calculator`. The calculator package declares `mcp>=1.4.1` unbounded and crash-loops against `mcp` 2.0.0, so new installs failed out of the box. Existing `servers.json` files are untouched — if yours references `mcp-server-calculator`, change it to `uvx --with 'mcp<2' mcp-server-calculator` or remove it
- Add an end-to-end build-time smoke test that spawns a real MCP server through the proxy and asserts a `tools/list` round-trip. The previous `mcp-proxy --version` check could not catch failures that occur at child-spawn time
- Add a `docker` ecosystem to Dependabot so the `uv` pin does not go stale
- Document the unbounded-dependency failure mode and how to pin servers in `DOCS.md`

## 0.2.13

- Migrate CI to the `home-assistant/builder` composable actions (`prepare-multi-arch-matrix`, `build-image`, `publish-multi-arch-manifest`); the monolithic builder action was deprecated in 2026.03.0 and its legacy builder image was removed in 2026.06.0
- Publish `ghcr.io/slettmayer/mcp-proxy` as a real multi-arch manifest (previously the amd64 and aarch64 matrix builds raced to the same tag, leaving only one architecture published)
- Build each architecture on its native runner (no QEMU emulation)
- Bump actions/checkout to v7 (Dependabot)

## 0.2.12

- Bump home-assistant/builder (Dependabot)

## 0.2.11

- Bump dorny/paths-filter (Dependabot)

## 0.2.10

- Bump actions/create-github-app-token (Dependabot)

## 0.2.9

- Bump actions/checkout (Dependabot)

## 0.2.8

- Add auto-release workflow: GitHub releases are now created automatically on version bump
- Update CI/CD and infrastructure documentation

## 0.2.7

- Bump actions/checkout (Dependabot)

## 0.2.6

- Bump docker/login-action (Dependabot)

## 0.2.5

- Add Docker build smoke tests to CI for critical tools (node, npm, npx, python3, uv, uvx, mcp-proxy)
- Pin `home-assistant/builder` to v2025.03.2, add cosign image signing, and configure Dependabot for GitHub Actions
- Add workflow to auto-bump version and changelog on Dependabot PRs

## 0.2.4

- Remove npm pre-install feature (introduced in 0.2.3) to reduce complexity; npx/uvx packages download on first use as before

## 0.2.2

- Fix log level: convert to uppercase as required by mcp-proxy (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Fix servers.json format: wrap server definitions in `mcpServers` key as required by mcp-proxy
- Update DOCS.md examples to use correct `mcpServers` format

## 0.2.1

- Fix mcp-proxy binary not found: set `UV_TOOL_BIN_DIR` so uv installs entry points to the expected path

## 0.2.0

- Initial working release
- Bridges stdio-based MCP servers (npx/uvx) to SSE endpoints for HA LLM integrations
- Pre-built images for amd64 and aarch64
- Default calculator example server created on first start
- Health check endpoint at `/status` with HA watchdog integration
