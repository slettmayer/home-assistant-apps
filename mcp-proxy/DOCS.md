# MCP Proxy Add-on for Home Assistant

This add-on bridges stdio-based MCP (Model Context Protocol) servers to SSE/StreamableHTTP endpoints that Home Assistant's LLM integrations can consume.

## How it works

Many MCP servers are distributed as CLI tools launched via `npx` or `uvx`. Home Assistant's LLM integrations expect to connect to MCP servers over HTTP (SSE). This add-on runs [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy), which:

1. Reads your server definitions from a JSON config file
2. Spawns each MCP server as a stdio subprocess
3. Exposes each server as an SSE endpoint at `http://<host>:9876/servers/<name>/sse`

## Configuration

### Server definitions (`servers.json`)

MCP servers are configured by editing the file:

```
/addon-configs/mcp_proxy/servers.json
```

You can edit this file using:
- **File Editor add-on** — navigate to `/addon-configs/mcp_proxy/servers.json`
- **SSH** — edit `/addon-configs/mcp_proxy/servers.json`
- **Samba** — access the `addon_configs` share

On first start, the add-on creates a default config with a calculator example server.

### Example configurations

**uvx-based server (Python):**

```json
{
  "calculator": {
    "command": "uvx",
    "args": ["mcp-server-calculator"]
  }
}
```

**npx-based server (Node.js):**

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/config"]
  }
}
```

**Server with environment variables:**

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
    }
  }
}
```

**Multiple servers:**

```json
{
  "calculator": {
    "command": "uvx",
    "args": ["mcp-server-calculator"]
  },
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/config"]
  }
}
```

### Add-on options

| Option | Default | Description |
|---|---|---|
| `log_level` | `info` | Logging verbosity: `debug`, `info`, `warning`, `error` |
| `pass_environment` | `false` | Pass all container env vars to MCP servers. **Warning:** this includes `SUPERVISOR_TOKEN` and other HA internal variables. Only enable if your MCP servers need access to HA APIs. |

## Connecting from Home Assistant

Each configured MCP server is available at:

```
http://<ha-host>:9876/servers/<server-name>/sse
```

For example, if your server is named `calculator`:

```
http://homeassistant.local:9876/servers/calculator/sse
```

Use this URL when configuring MCP server connections in your Home Assistant LLM integration.

## Health check

The add-on exposes a status endpoint:

```
curl http://homeassistant.local:9876/status
```

This is also used by the HA watchdog to automatically restart the add-on if it becomes unresponsive.

## First-run latency

The first time an MCP server is accessed, `npx` or `uvx` may need to download packages. This can take 30-60 seconds depending on the server and your network speed. Subsequent starts will be faster as packages are cached.

## Troubleshooting

- **"servers.json is not valid JSON"** — Check your config file for syntax errors. Use a JSON validator.
- **Server not responding** — Check the add-on logs for errors from the MCP server process. Try running the command manually in SSH first.
- **Connection refused on port 9876** — Make sure the port is not blocked by your network. The add-on binds to `0.0.0.0:9876`.
- **Slow first response** — This is expected; see "First-run latency" above.
