# Changelog

## 0.2.1

- Fix mcp-proxy binary not found: set `UV_TOOL_BIN_DIR` so uv installs entry points to the expected path

## 0.2.0

- Initial working release
- Bridges stdio-based MCP servers (npx/uvx) to SSE endpoints for HA LLM integrations
- Pre-built images for amd64 and aarch64
- Default calculator example server created on first start
- Health check endpoint at `/status` with HA watchdog integration
