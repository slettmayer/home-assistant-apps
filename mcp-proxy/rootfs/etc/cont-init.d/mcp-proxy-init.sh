#!/usr/bin/with-contenv bashio
# ==============================================================================
# Create default servers.json if missing, validate JSON
# ==============================================================================

CONFIG_FILE="/config/servers.json"

if ! bashio::fs.file_exists "${CONFIG_FILE}"; then
    bashio::log.info "No servers.json found — creating default config with calculator example"
    cat > "${CONFIG_FILE}" << 'EOF'
{
  "calculator": {
    "command": "uvx",
    "args": ["mcp-server-calculator"]
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
server_names=$(python3 -c "import json, sys; print(', '.join(json.load(open(sys.argv[1])).keys()))" "${CONFIG_FILE}")
bashio::log.info "Configured MCP servers: ${server_names}"
