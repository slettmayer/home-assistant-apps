#!/usr/bin/with-contenv bashio
# ==============================================================================
# Create default servers.json if missing, validate JSON
# ==============================================================================

CONFIG_FILE="/config/servers.json"

if ! bashio::fs.file_exists "${CONFIG_FILE}"; then
    bashio::log.info "No servers.json found — creating default config with weather example"
    # geosphere-mcp-server pins its MCP SDK (`mcp[cli]>=2,<3`) and needs no API
    # key, so a fresh install starts cleanly. Do not use a server that declares
    # an unbounded `mcp` specifier here: the previous default
    # (mcp-server-calculator, `mcp>=1.4.1`) resolved the breaking mcp 2.0.0 and
    # crash-looped every fresh install. Keep this example bounded.
    cat > "${CONFIG_FILE}" << 'EOF'
{
  "mcpServers": {
    "geosphere": {
      "command": "uvx",
      "args": ["geosphere-mcp-server"]
    }
  }
}
EOF
fi

# Validate JSON
if ! python3 -c "import json, sys; json.load(open(sys.argv[1]))" "${CONFIG_FILE}" 2>/dev/null; then
    bashio::log.fatal "servers.json is not valid JSON — please fix the file and restart"
    exit 1
fi

# Log configured server names
server_names=$(python3 -c "import json, sys; print(', '.join(json.load(open(sys.argv[1])).get('mcpServers', {}).keys()))" "${CONFIG_FILE}")
bashio::log.info "Configured MCP servers: ${server_names}"
