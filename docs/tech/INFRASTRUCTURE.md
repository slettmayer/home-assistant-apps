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
The `Dockerfile` uses a parameterized `BUILD_FROM` base image supplied at build time via a `BUILD_FROM` build-arg. The architecture-specific base images are declared in `mcp-proxy/build.yaml` and read from there by the workflow:
- `aarch64`: `ghcr.io/home-assistant/aarch64-base-debian:trixie`
- `amd64`: `ghcr.io/home-assistant/amd64-base-debian:trixie`

The `uv` and `uvx` binaries are copied from a named `uv` build stage pinned to `ghcr.io/astral-sh/uv:0.12.0` (multi-arch aware -- the tag publishes `linux/amd64` and `linux/arm64`). The stage exists so Dependabot's docker parser, which reads `FROM` lines and not inline `COPY --from=<image>` refs, can bump the tag.

The Dockerfile uses a four-stage build (`uv` -> `base` -> `test` -> final). The `test` stage runs two layers of checks:

1. **Tool availability** -- verifies all critical tools are present and executable (`python3`, `uv`, `uvx`, `node`, `npx`, `mcp-proxy --version`).
2. **End-to-end round-trip** (`mcp-proxy/test/smoke_e2e.py`) -- starts the proxy with a single named stdio server, drives a real MCP handshake (`initialize` -> `notifications/initialized` -> `tools/list`) over StreamableHTTP, and asserts the child's tools come back. On failure it prints the proxy's own output and exits non-zero.

The second check exists because `--version` cannot catch child-side breakage: a spawned server resolves its own dependencies in its own `uvx` environment, so an unbounded specifier there only fails when a request actually reaches the child. The test uses the same server the bootstrap config ships, so it covers the fresh-install path. It requires PyPI reachability at build time (already true via `uv tool install`), and it deliberately leaves the warmed `uvx` environment in the image cache so the bootstrap server's first real request skips the download.

The final stage derives from `test` (not `base`), which forces BuildKit to always execute the smoke-test stage -- it cannot be skipped as an unused layer, and it runs on pull-request builds too (which build without pushing).

### CI/CD Pipeline
Defined in `.github/workflows/build.yaml`. Triggers:
- Push to `main` (with `paths-ignore` for docs files -- docs-only pushes skip the workflow entirely since no branch protection applies post-merge)
- Pull requests targeting `main` (no `paths-ignore` -- always triggers so the `gate` check is reported)

The build uses the **`home-assistant/builder` composable actions**. (The monolithic `home-assistant/builder` action was deprecated in 2026.03.0 and its legacy builder image was removed in 2026.06.0, so it can no longer be used.) All three composable actions are pinned to the same SHA (`2026.06.0`) and managed by Dependabot.

Job pipeline: `changes` → `prepare` → `build` (matrix) → `manifest` → `gate`.

1. **`changes`** -- uses `dorny/paths-filter@v4` to detect whether the change touches code (non-doc files). Outputs `code: true/false`.
2. **`prepare`** -- runs only when `code == 'true'`. Reads the add-on version from `mcp-proxy/config.yaml` and calls `home-assistant/builder/actions/prepare-multi-arch-matrix` to produce the build matrix -- one entry per architecture, each carrying its native runner OS and per-arch image name (`ghcr.io/<owner>/<arch>-mcp-proxy`).
3. **`build`** -- matrix over the architectures from `prepare`. Each job runs on its **native runner** (`ubuntu-24.04` for amd64, `ubuntu-24.04-arm` for aarch64 -- no QEMU emulation) and calls `home-assistant/builder/actions/build-image`:
   - `context: mcp-proxy`; the `BUILD_FROM` build-arg and OCI `labels` are read from `mcp-proxy/build.yaml`.
   - On **push to `main`**: `push` and `cosign` are enabled -- each per-arch image is pushed to `ghcr.io/<owner>/<arch>-mcp-proxy:<version>` (and `:latest`) and keyless-signed via OIDC.
   - On **pull requests**: `push` and `cosign` are disabled -- the image is built but not pushed. The Dockerfile's `test` stage still runs, so the smoke tests validate every PR.
4. **`manifest`** -- runs only on push to `main`. Calls `home-assistant/builder/actions/publish-multi-arch-manifest` to combine the per-arch images into a single multi-arch manifest at `ghcr.io/<owner>/mcp-proxy:<version>` (and `:latest`) -- the ref HA pulls -- and signs it.
5. **`gate`** -- runs after `build` and `manifest` with `if: always()`. Passes if both succeeded or were skipped; fails if either failed or was cancelled.

Branch protection requires the `gate` check (not `build`/`manifest`), so docs-only PRs merge cleanly while code PRs still get the full build validation.

> The per-arch `ghcr.io/<owner>/<arch>-mcp-proxy` repositories are build intermediates. `publish-multi-arch-manifest` copies their blobs into the `mcp-proxy` package, so the published multi-arch image is self-contained and pullable regardless of the per-arch repositories' visibility.

### Dependabot Version Bump
Defined in `.github/workflows/dependabot-version-bump.yaml`. Triggers on `pull_request` events (`opened`, `synchronize`) but only runs for `dependabot[bot]`.

When a Dependabot PR is opened or updated:
1. Generates a **GitHub App token** via `actions/create-github-app-token@v3`
2. Checks out the PR branch using the App token (configures git credentials)
3. Bumps the patch version in `mcp-proxy/config.yaml`
4. Adds a changelog entry to `mcp-proxy/CHANGELOG.md`
5. Commits and pushes the version bump

The App token is used instead of `GITHUB_TOKEN` because commits pushed by `GITHUB_TOKEN` do not trigger downstream workflows (GitHub's infinite loop prevention). The App token ensures the version bump commit triggers the build workflow.

**CHANGELOG format constraint:** The workflow parses `CHANGELOG.md` assuming it starts with `# Changelog\n` on lines 1-2, and uses `## X.Y.Z` section headers with no trailing whitespace. Breaking this format breaks both the version bump and auto-release workflows.

**Required setup:**
- A GitHub App with repository access, installed on the repository
- Repository secrets: `GH_ACTION_APP_ID` (numeric App ID), `GH_ACTION_APP_PRIVATE_KEY` (PEM key)
- These secrets must also be configured under **Dependabot secrets** (Settings > Secrets and variables > Dependabot), not just Actions secrets

### Dependabot
Configured in `.github/dependabot.yml`. Two ecosystems, both weekly and both grouped into a single PR per ecosystem:

- **`github-actions`** (directory `/`) -- action version references (e.g., `actions/checkout`, `dorny/paths-filter`, and the `home-assistant/builder` composable actions).
- **`docker`** (directory `/mcp-proxy`) -- the pinned `ghcr.io/astral-sh/uv` tag. This only works because the image is declared as a named `FROM ... AS uv` stage; Dependabot's docker parser does not read inline `COPY --from=<image>` references.

The `dependabot-version-bump` workflow is ecosystem-agnostic (it gates on `github.actor == 'dependabot[bot]'`), so docker-ecosystem PRs get the same automatic `config.yaml` patch bump and changelog entry as Actions PRs.

Not monitored by Dependabot:
- The HA base images -- they are referenced through the `BUILD_FROM` ARG, which Dependabot does not resolve, and they track the rolling `trixie` channel by design
- Debian package versions in `apt-get install`
- `mcp-proxy` and its pinned `mcp` SDK (PyPI is not a configured ecosystem -- there is no Python manifest in the repo, only a `RUN uv tool install` line). These pins must be reviewed by hand; see TECH-STACK.md Known Risks

### Auto Release
Defined in `.github/workflows/release.yaml`. Triggers via **`workflow_run`**: it runs only after the `Build Add-on` workflow concludes, and its job runs only when that run was a **successful `push`** to `main` (never for pull requests or failed/cancelled builds). This guarantees the GitHub release is never created before the add-on images are built and published.

When the version in `config.yaml` does not have a matching GitHub release:
1. Checks out the built commit (`workflow_run.head_sha`)
2. Extracts the version from `config.yaml`
3. Checks if a release for that tag already exists (idempotent -- non-version-bump pushes no-op here)
4. Extracts the changelog section for the version from `mcp-proxy/CHANGELOG.md`
5. Creates a GitHub release (tagged at the built commit via `--target`) with the changelog as release notes

This covers both manual version bumps and Dependabot auto-bumps. No secrets beyond `GITHUB_TOKEN` are required (`contents: write` permission).

### Image Registry
Images are published to `ghcr.io/slettmayer/mcp-proxy:<version>` as a multi-arch manifest (`linux/amd64` + `linux/arm64`). Per-arch build intermediates live at `ghcr.io/slettmayer/<arch>-mcp-proxy`.

The `image` field in `mcp-proxy/config.yaml` tells HA to pull pre-built images from GHCR instead of building locally. Without this field, HA always builds from the Dockerfile.

### Deployment Model
1. User adds `https://github.com/slettmayer/home-assistant-apps` as a repository in HA Add-on Store
2. HA Supervisor reads `repository.yaml` and discovers add-ons
3. On install, HA pulls `ghcr.io/slettmayer/mcp-proxy:<version>` (resolving the manifest for the host architecture)
4. HA Supervisor manages the container lifecycle (start, stop, watchdog restart)

## Dependencies
- GitHub Actions runners: `ubuntu-24.04` (amd64 build), `ubuntu-24.04-arm` (aarch64 build), `ubuntu-latest` (other jobs)
- `home-assistant/builder` composable actions -- `prepare-multi-arch-matrix`, `build-image`, `publish-multi-arch-manifest` (pinned to SHA, managed by Dependabot)
- `dorny/paths-filter@v4` (detects code vs docs-only changes)
- `actions/checkout@v7`
- `actions/create-github-app-token@v3` (Dependabot version bump workflow)
- GHCR (`ghcr.io`)
- `GITHUB_TOKEN` (automatic; the `build` and `manifest` jobs need `packages: write` and `id-token: write`)
- GitHub App secrets: `GH_ACTION_APP_ID`, `GH_ACTION_APP_PRIVATE_KEY` (configured in both Actions and Dependabot secret settings)
- Cosign (keyless signing via OIDC, handled inside `build-image` and `publish-multi-arch-manifest`)

## Design Decisions
- GHCR over Docker Hub: aligns with HA ecosystem conventions and GitHub-native auth
- `home-assistant/builder` composable actions over the deprecated monolithic action (and over raw `docker buildx`): they build each arch on native hardware, publish a real multi-arch manifest, and apply HA-specific labeling and cosign signing
- Native per-arch runners: `aarch64` and `amd64` build in parallel, each on matching hardware, avoiding slow QEMU emulation
- Multi-arch manifest: a single `mcp-proxy` tag serves both architectures; HA resolves the correct one at pull time (the `image` field has no `{arch}` placeholder)
- Cosign keyless signing via OIDC: images pushed to GHCR are signed without managing signing keys; requires `id-token: write` on the `build`/`manifest` jobs
- Release gated behind the build (`workflow_run`): a GitHub release is only cut once the images for that commit exist

## Known Risks
- The end-to-end smoke test makes builds depend on PyPI reachability *and* on `geosphere-mcp-server` continuing to publish and start cleanly; a PyPI outage or a broken release of that package fails the build. The tradeoff is deliberate -- the alternative is shipping an image whose proxy cannot actually spawn a server
- GitHub App token secrets must be configured in **both** Actions and Dependabot secret settings; forgetting Dependabot secrets causes silent failures on Dependabot PRs
- The GitHub App must remain installed on the repository; uninstalling it breaks the Dependabot version bump workflow

## Extension Guidelines
- To add a new architecture, add its base image to `mcp-proxy/build.yaml` and add the arch to the `architectures` input of both `prepare-multi-arch-matrix` and `publish-multi-arch-manifest` in `.github/workflows/build.yaml` (supported values: `amd64`, `aarch64`)
- To add a linting step, add it to the `prepare` job or as a separate job that the `build` matrix depends on
