# Home Assistant Add-ons

[![Build Add-on](https://github.com/slettmayer/home-assistant-apps/actions/workflows/build.yaml/badge.svg)](https://github.com/slettmayer/home-assistant-apps/actions/workflows/build.yaml)

A collection of add-ons for [Home Assistant](https://www.home-assistant.io/).

## Installation

Add this repository to your Home Assistant instance:

1. Navigate to **Settings** > **Add-ons** > **Add-on Store**
2. Click the three-dot menu (top right) > **Repositories**
3. Paste this URL:
   ```
   https://github.com/slettmayer/home-assistant-apps
   ```
4. Click **Add**, then refresh the page

## Add-ons

### [MCP Proxy](mcp-proxy/)

Bridges stdio-based [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) servers to SSE/StreamableHTTP endpoints for Home Assistant LLM integrations.

Many MCP servers ship as CLI tools launched via `npx` or `uvx`, but Home Assistant expects HTTP (SSE) endpoints. This add-on runs [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy) to handle the translation -- no remote proxy needed.

**Key features:**

- Run any MCP server (`npx`, `uvx`, or custom binary) as an SSE endpoint
- Standard `mcpServers` JSON config format -- same as Claude Desktop, Cursor, etc.
- Multi-server support with path-based routing (`/servers/<name>/sse`)
- Pre-built images for **amd64** and **aarch64**
- Automatic health monitoring via HA watchdog

**Quick example** -- add this to `/addon-configs/mcp_proxy/servers.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/config"]
    }
  }
}
```

Then connect your HA LLM integration to `http://homeassistant.local:9876/servers/filesystem/sse`.

See the [add-on documentation](mcp-proxy/DOCS.md) for full configuration details.

## Support

- **Issues**: [GitHub Issues](https://github.com/slettmayer/home-assistant-apps/issues)
- **Changelog**: [mcp-proxy/CHANGELOG.md](mcp-proxy/CHANGELOG.md)

## License

MIT
