ARG BUILD_FROM
FROM ${BUILD_FROM}

# System deps: Python 3, Node.js + npm (for npx), build tools (for native MCP deps)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        nodejs npm \
        build-essential \
        ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

# uv + uvx — copy pre-built binaries from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install mcp-proxy via uv tool
ENV UV_TOOL_DIR=/usr/local/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/uv-tools/bin \
    UV_PYTHON_PREFERENCE=only-system
RUN uv tool install mcp-proxy
ENV PATH="/usr/local/uv-tools/bin:${PATH}"

COPY rootfs /
