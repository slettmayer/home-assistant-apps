# Changelog

## 0.2.3

- Pre-install npm packages for npx-based MCP servers during init to prevent mcp-proxy timeout on first connection

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
