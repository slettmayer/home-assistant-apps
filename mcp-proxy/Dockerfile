# uv + uvx source image. Declared as a named FROM stage (not an inline
# `COPY --from=ghcr.io/...`) so Dependabot's docker ecosystem actually parses
# and bumps the tag — its parser reads FROM lines, not COPY --from refs.
FROM ghcr.io/astral-sh/uv:0.12.0 AS uv

# BUILD_FROM is supplied by CI (per-arch, from build.yaml). The default only
# applies to a manual `docker build` without --build-arg, and silences the
# BuildKit InvalidDefaultArgInFrom warning.
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:trixie
FROM ${BUILD_FROM} AS base

# System deps: Python 3, Node.js + npm (for npx), build tools (for native MCP deps)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        nodejs npm \
        build-essential \
        ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

# uv + uvx — copy pre-built binaries from the pinned official image
COPY --from=uv /uv /uvx /usr/local/bin/

# Install mcp-proxy via uv tool.
#
# Both the tool and its transitive `mcp` SDK are pinned. mcp 2.0.0 (2026-07-28)
# is a breaking release and mcp-proxy 0.12.0 predates it: under mcp 2.x its
# entrypoint dies at import with
#   ImportError: cannot import name 'request_ctx' from 'mcp.server.lowlevel.server'
# mcp-proxy declares `mcp>=1.17.0` with no upper bound, so an unpinned install
# resolves 2.x and produces a broken image. mcp 1.29.0 was released alongside
# 2.0.0 as the supported final 1.x. Revisit the `<2` bound when mcp-proxy
# publishes an mcp 2.x-compatible release.
ENV UV_TOOL_DIR=/usr/local/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/uv-tools/bin \
    UV_PYTHON_PREFERENCE=only-system
RUN uv tool install 'mcp-proxy==0.12.0' --with 'mcp>=1.17,<2'
ENV PATH="/usr/local/uv-tools/bin:${PATH}"

# Smoke-test stage: verify all critical tools are functional
FROM base AS test
RUN python3 --version \
    && uv --version \
    && uvx --version \
    && node --version \
    && npx --version \
    && /usr/local/uv-tools/bin/mcp-proxy --version

# End-to-end smoke test: spawn a real stdio MCP server through the proxy and
# assert a tools/list round-trip.
#
# `mcp-proxy --version` alone cannot catch breakage on the *child* side: a
# child's dependency resolution happens in its own uvx environment at spawn
# time, so an unbounded specifier in the child only fails when a request
# actually reaches it. This stage exercises that path with the same server the
# bootstrap config ships, which is the case users hit on a fresh install.
#
# Requires PyPI reachability at build time (already true via `uv tool install`).
# The uvx environment this warms is deliberately left in the image cache so the
# bootstrap server's first real request does not pay the download cost.
COPY test/smoke_e2e.py /tmp/smoke_e2e.py
RUN python3 /tmp/smoke_e2e.py && rm -f /tmp/smoke_e2e.py

# Final stage: derived from test so BuildKit cannot skip it
FROM test
COPY rootfs /
