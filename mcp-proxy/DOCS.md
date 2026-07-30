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

On first start, the add-on creates a default config with a weather example server
([`geosphere-mcp-server`](https://pypi.org/project/geosphere-mcp-server/)), which needs no API key.

### Pin your MCP servers

Most MCP servers depend on the `mcp` Python SDK, and many declare it with **no upper version bound**
(e.g. `mcp>=1.4.1`). `mcp` 2.0.0 was a breaking release, so such a server can start resolving an
incompatible SDK and fail at launch — without you changing anything. A crashing server takes the whole
proxy down with it, not just itself.

Two habits avoid this:

- **Don't use `@latest`.** `uvx mcp-server-foo@latest` forces a fresh dependency resolve on every
  restart, which turns a dormant risk into an outage at the worst possible moment. A plain
  `uvx mcp-server-foo` reuses the cached environment.
- **Constrain the SDK yourself** when a server's own bound is missing, using `--with`:

  ```json
  {
    "mcpServers": {
      "example": {
        "command": "uvx",
        "args": ["--with", "mcp<2", "mcp-server-example"]
      }
    }
  }
  ```

If a server stops working after previously being fine, this is the first thing to check — the add-on log
will show a `ModuleNotFoundError` or `ImportError` from the server process.

### Example configurations

The config file uses the standard MCP `mcpServers` format:

**uvx-based server (Python):**

```json
{
  "mcpServers": {
    "geosphere": {
      "command": "uvx",
      "args": ["geosphere-mcp-server"]
    }
  }
}
```

**npx-based server (Node.js):**

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

**Server with environment variables:**

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

**Multiple servers:**

```json
{
  "mcpServers": {
    "geosphere": {
      "command": "uvx",
      "args": ["geosphere-mcp-server"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/config"]
    }
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

For example, if your server is named `geosphere`:

```
http://homeassistant.local:9876/servers/geosphere/sse
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
- **Add-on crash-loops, or one bad server makes all of them unavailable** — The proxy exits if any configured server fails to start, so a single broken entry takes down the rest. Look for `ModuleNotFoundError` / `ImportError` in the log to identify the culprit, then pin its SDK as described in "Pin your MCP servers" above.
- **Connection refused on port 9876** — Make sure the port is not blocked by your network. The add-on binds to `0.0.0.0:9876`.
- **Slow first response** — This is expected; see "First-run latency" above.
