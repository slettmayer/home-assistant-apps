# Conventions

## Purpose
Documents naming patterns, code style, error handling, and shell scripting conventions used in this project.

## Responsibilities
- Define naming conventions for files, variables, and identifiers
- Document shell scripting style rules
- Describe error handling and logging patterns

## Non-Responsibilities
- Project structure and file layout: see [ARCHITECTURE.md](ARCHITECTURE.md)
- Technology choices: see [TECH-STACK.md](TECH-STACK.md)
- Git workflow and CI: see [INFRASTRUCTURE.md](INFRASTRUCTURE.md)

## Overview

### Naming Conventions

| Context | Convention | Examples |
|---------|-----------|----------|
| Shell scripts | `kebab-case` | `mcp-proxy-init.sh`, `run`, `finish` |
| Shell local variables | `snake_case` | `log_level`, `pass_env_flag`, `server_names` |
| Shell path constants | `UPPER_SNAKE_CASE` | `CONFIG_FILE` |
| Add-on slug | `snake_case` | `mcp_proxy` |
| Docker image name | `kebab-case` | `mcp-proxy` |
| YAML config keys | `snake_case` | `log_level`, `pass_environment`, `build_from` |
| s6 service directory | matches service name | `mcp-proxy/` |
| Workflow files | `kebab-case` | `build.yaml` |
| Documentation | `UPPER_CASE` | `DOCS.md`, `CHANGELOG.md` |
| Git branches | `type/description` | `feature/mcp-proxy-addon`, `fix/ghcr-auth` |

### Shell Script Style
- Shebang: `#!/usr/bin/with-contenv bashio` (never plain `#!/bin/bash`)
- Indentation: 4 spaces
- Variable expansion: always quoted and braced (`"${variable}"`)
- Command continuation: `\` at end of line for multi-line commands
- Section headers in init/finish scripts use block comment banners:
  ```sh
  # ==============================================================================
  # Descriptive title
  # ==============================================================================
  ```
- Heredocs: single-quoted delimiter (`<< 'EOF'`) to prevent variable interpolation
- Inline Python: use `python3 -c "..."` for JSON manipulation in shell scripts; do not parse JSON with shell tools (`grep`, `awk`, `cut`)
- Intentionally unquoted variables: when a variable may be empty and should expand to nothing (not an empty string argument), leave it unquoted (e.g., `${pass_env_flag}`). Document the intent with a comment

### YAML Style
- Indentation: 2 spaces
- Multiline strings: `>-` (folded, strip trailing newline)

### Dockerfile Style
- `RUN` instructions chained with `&&` and `\` continuations
- Always use `--no-install-recommends` with `apt-get install`
- Always clean up with `rm -rf /var/lib/apt/lists/*` after `apt-get`

### Error Handling
- Init scripts validate preconditions and `exit 1` on failure (prevents service from starting)
- `finish` script halts the s6 supervision tree on unexpected exit codes (not 0 or 256)
- No silent failures: every error path either exits non-zero or logs explicitly before halting

### Logging
- `bashio::log.info` -- normal status messages
- `bashio::log.warning` -- security-sensitive configuration (e.g., `pass_environment` enabled)
- `bashio::log.error` -- crash/failure reporting
- `bashio::log.fatal` -- unrecoverable init failures (followed by `exit 1`)

## Dependencies
- `bashio` shell library (provided by HA base image)

## Design Decisions
- `with-contenv bashio` shebang over plain bash: provides access to HA Supervisor environment and the `bashio` helper library in every script
- Full paths to `uv tool` binaries in service scripts: Dockerfile `ENV PATH` is not available in s6 service context

### Option Value Transformation
- HA option schema values are always lowercase (e.g., `debug`, `info`)
- When the target daemon requires different casing, transform inline in the `run` script via variable reassignment (e.g., `log_level=$(echo "${log_level}" | tr '[:lower:]' '[:upper:]')`)

## Known Risks
- No `shellcheck` or `yamllint` in CI; shell script errors are only caught at runtime
- No automated linting for YAML files

## Extension Guidelines
- New shell scripts must use `#!/usr/bin/with-contenv bashio` shebang
- New shell scripts must use 4-space indentation and quoted/braced variable expansion
- Always use full paths to binaries installed via `uv tool` (e.g., `/usr/local/uv-tools/bin/<tool>`)
