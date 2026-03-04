# Changelog

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
