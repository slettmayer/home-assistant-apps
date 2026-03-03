#!/usr/bin/with-contenv bashio
# ==============================================================================
# Create default servers.json if missing, validate JSON
# ==============================================================================

CONFIG_FILE="/config/servers.json"

if ! bashio::fs.file_exists "${CONFIG_FILE}"; then
    bashio::log.info "No servers.json found — creating default config with calculator example"
    cat > "${CONFIG_FILE}" << 'EOF'
{
  "mcpServers": {
    "calculator": {
      "command": "uvx",
      "args": ["mcp-server-calculator"]
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

# ==============================================================================
# Pre-install packages so mcp-proxy doesn't time out waiting for downloads
# ==============================================================================

python3 -c "
import json, sys

config = json.load(open(sys.argv[1]))
servers = config.get('mcpServers', {})

for name, server in servers.items():
    cmd = server.get('command', '')
    args = server.get('args', [])
    # Extract the package name (first non-flag argument)
    pkg = next((a for a in args if not a.startswith('-')), None)
    if pkg:
        print(f'{cmd}:{name}:{pkg}')
" "${CONFIG_FILE}" | while IFS=: read -r cmd name pkg; do
    case "${cmd}" in
        npx)
            if ! npm list -g "${pkg}" >/dev/null 2>&1; then
                bashio::log.info "Pre-installing npm package for ${name}: ${pkg}"
                npm install -g "${pkg}" || bashio::log.warning "Failed to pre-install ${pkg}"
            else
                bashio::log.info "npm package already cached for ${name}: ${pkg}"
            fi
            ;;
        uvx)
            if ! /usr/local/uv-tools/bin/mcp-proxy --version >/dev/null 2>&1; then
                true  # uvx caches on first run, skip pre-install
            fi
            bashio::log.info "uvx server ${name} will cache on first run: ${pkg}"
            ;;
    esac
done
