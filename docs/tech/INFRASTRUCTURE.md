# Infrastructure

## Purpose
Documents the Docker build, CI/CD pipeline, image registry, and deployment model.

## Responsibilities
- Describe the Docker image build process and multi-arch strategy
- Document the GitHub Actions CI/CD pipeline
- Explain the GHCR publishing and HA installation flow

## Non-Responsibilities
- Container runtime behavior: see [ARCHITECTURE.md](ARCHITECTURE.md)
- System dependencies installed in the image: see [TECH-STACK.md](TECH-STACK.md)
- Release versioning process: documented in root `CLAUDE.md`

## Overview

### Docker Build
The `Dockerfile` uses a parameterized `BUILD_FROM` base image supplied by the HA builder. Architecture-specific base images are declared in `mcp-proxy/build.yaml`:
- `aarch64`: `ghcr.io/home-assistant/aarch64-base-debian:trixie`
- `amd64`: `ghcr.io/home-assistant/amd64-base-debian:trixie`

The `uv` and `uvx` binaries are copied from `ghcr.io/astral-sh/uv:latest` via `COPY --from` (multi-arch aware).

### CI/CD Pipeline
Defined in `.github/workflows/build.yaml`. Triggers:
- Push to `main`
- Pull requests targeting `main`

Steps per architecture (`aarch64`, `amd64` matrix):
1. Checkout code
2. Authenticate to GHCR via `docker/login-action@v3` using `GITHUB_TOKEN`
3. Build and push via `home-assistant/builder@master`

Builder flags:
- `--docker-hub ghcr.io/<owner>` -- registry prefix
- `--image mcp-proxy` -- image name
- `--target mcp-proxy` -- add-on directory
- `--addon` -- build mode
- `--test` (PRs only) -- builds the image without pushing to GHCR

On pull requests, GHCR login is skipped and `--test` prevents image push. PRs from forks follow the same path (test build only).

The workflow uses a `changes` → `build` → `gate` pattern to handle documentation-only PRs:
1. **`changes`** -- uses `dorny/paths-filter@v3` to detect whether the PR touches code (non-doc files). Outputs `code: true/false`.
2. **`build`** -- the existing matrix build, now conditional on `needs.changes.outputs.code == 'true'`. Skipped entirely for docs-only PRs.
3. **`gate`** -- runs after `build` with `if: always()`. Passes if `build` succeeded or was skipped; fails if `build` failed or was cancelled.

Branch protection requires the `gate` check (not `build`), so docs-only PRs merge cleanly while code PRs still get the full build validation.

### Image Registry
Images are published to `ghcr.io/slettmayer/mcp-proxy:<version>`.

The `image` field in `mcp-proxy/config.yaml` tells HA to pull pre-built images from GHCR instead of building locally. Without this field, HA always builds from the Dockerfile.

### Deployment Model
1. User adds `https://github.com/slettmayer/home-assistant-apps` as a repository in HA Add-on Store
2. HA Supervisor reads `repository.yaml` and discovers add-ons
3. On install, HA pulls `ghcr.io/slettmayer/mcp-proxy:<version>`
4. HA Supervisor manages the container lifecycle (start, stop, watchdog restart)

## Dependencies
- GitHub Actions runners (ubuntu-latest)
- `docker/login-action@v3`
- `home-assistant/builder@master`
- GHCR (`ghcr.io`)
- `GITHUB_TOKEN` (automatic, needs `packages: write` permission)

## Design Decisions
- GHCR over Docker Hub: aligns with HA ecosystem conventions and GitHub-native auth
- Matrix strategy for architectures: builds `aarch64` and `amd64` in parallel
- `home-assistant/builder` over raw `docker buildx`: handles HA-specific labeling, signing, and conventions

## Known Risks
- `home-assistant/builder@master` is not pinned to a tag or SHA; upstream changes could break builds
- `ghcr.io/astral-sh/uv:latest` is not pinned; a breaking `uv` release could silently break image builds
- No image signing or attestation beyond what the HA builder provides by default

## Extension Guidelines
- To add a new architecture, add it to both `mcp-proxy/build.yaml` (with base image) and the `matrix.arch` array in `.github/workflows/build.yaml`
- To add a linting step, insert it before the build step in the workflow
