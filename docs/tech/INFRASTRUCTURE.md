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

The Dockerfile uses a three-stage build (`base` -> `test` -> final). The `test` stage runs smoke tests verifying all critical tools are present and executable (`python3`, `uv`, `uvx`, `node`, `npx`, `mcp-proxy`). The final stage derives from `test` (not `base`), which forces BuildKit to always execute the smoke-test stage -- it cannot be skipped as an unused layer.

### CI/CD Pipeline
Defined in `.github/workflows/build.yaml`. Triggers:
- Push to `main` (with `paths-ignore` for docs files -- docs-only pushes skip the workflow entirely since no branch protection applies post-merge)
- Pull requests targeting `main` (no `paths-ignore` -- always triggers so the `gate` check is reported)

Steps per architecture (`aarch64`, `amd64` matrix):
1. Checkout code
2. Authenticate to GHCR via `docker/login-action@v3` using `GITHUB_TOKEN` (push to `main` only; skipped on PRs)
3. Build and push via `home-assistant/builder` (pinned to SHA, managed by Dependabot)

Builder flags:
- `--docker-hub ghcr.io/<owner>` -- registry prefix
- `--image mcp-proxy` -- image name
- `--target mcp-proxy` -- add-on directory
- `--addon` -- build mode
- `--cosign` (push to `main` only) -- keyless cosign signing via OIDC (`id-token: write` permission)
- `--test` (PRs only) -- builds the image without pushing to GHCR

On pull requests, GHCR login is skipped and `--test` prevents image push. PRs from forks follow the same path (test build only).

The workflow uses a `changes` → `build` → `gate` pattern to handle documentation-only PRs:
1. **`changes`** -- uses `dorny/paths-filter@v3` to detect whether the PR touches code (non-doc files). Outputs `code: true/false`.
2. **`build`** -- the existing matrix build, now conditional on `needs.changes.outputs.code == 'true'`. Skipped entirely for docs-only PRs.
3. **`gate`** -- runs after `build` with `if: always()`. Passes if `build` succeeded or was skipped; fails if `build` failed or was cancelled.

Branch protection requires the `gate` check (not `build`), so docs-only PRs merge cleanly while code PRs still get the full build validation.

### Dependabot Version Bump
Defined in `.github/workflows/dependabot-version-bump.yaml`. Triggers on `pull_request` events (`opened`, `synchronize`) but only runs for `dependabot[bot]`.

When a Dependabot PR is opened or updated:
1. Generates a **GitHub App token** via `actions/create-github-app-token@v2`
2. Checks out the PR branch using the App token (configures git credentials)
3. Bumps the patch version in `mcp-proxy/config.yaml`
4. Adds a changelog entry to `mcp-proxy/CHANGELOG.md`
5. Commits and pushes the version bump

The App token is used instead of `GITHUB_TOKEN` because commits pushed by `GITHUB_TOKEN` do not trigger downstream workflows (GitHub's infinite loop prevention). The App token ensures the version bump commit triggers the build workflow.

Note: the workflow trigger is `pull_request` for all PRs; the Dependabot guard (`if: github.actor == 'dependabot[bot]'`) is at the job level, so a workflow run is created for every PR but exits immediately for non-Dependabot actors.

**CHANGELOG format constraint:** The workflow constructs the changelog by writing the header and new entry, then appending `tail -n +3` of the existing file (skipping `# Changelog\n`). This means `CHANGELOG.md` must start with exactly `# Changelog` on line 1 and a blank line on line 2. The idempotency check uses `grep -q "^## X.Y.Z$"` which requires exact `## X.Y.Z` section headers with no trailing whitespace.

**Required setup:**
- A GitHub App with repository access, installed on the repository
- Repository secrets: `GH_ACTION_APP_ID` (numeric App ID), `GH_ACTION_APP_PRIVATE_KEY` (PEM key)
- These secrets must also be configured under **Dependabot secrets** (Settings > Secrets and variables > Dependabot), not just Actions secrets -- Dependabot workflows cannot access regular Actions secrets

### Dependabot
Configured in `.github/dependabot.yml`. Scope: **GitHub Actions only** (`package-ecosystem: "github-actions"`). Monitors action version references (e.g., `actions/checkout`, `home-assistant/builder`) weekly.

Not monitored by Dependabot:
- `ghcr.io/astral-sh/uv:latest` Docker image reference in the Dockerfile
- Debian package versions in `apt-get install`
- `mcp-proxy` PyPI package version

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
- `docker/login-action@v4`
- `dorny/paths-filter@v3` (detects code vs docs-only changes on PRs)
- `home-assistant/builder` (pinned to SHA, managed by Dependabot)
- `actions/create-github-app-token@v2` (Dependabot version bump workflow)
- GHCR (`ghcr.io`)
- `GITHUB_TOKEN` (automatic, needs `packages: write` and `id-token: write` permissions)
- GitHub App secrets: `GH_ACTION_APP_ID`, `GH_ACTION_APP_PRIVATE_KEY` (configured in both Actions and Dependabot secret settings)
- Cosign (keyless signing via OIDC, provided by `home-assistant/builder` with `--cosign` flag)

## Design Decisions
- GHCR over Docker Hub: aligns with HA ecosystem conventions and GitHub-native auth
- Matrix strategy for architectures: builds `aarch64` and `amd64` in parallel
- `home-assistant/builder` over raw `docker buildx`: handles HA-specific labeling, cosign signing, and conventions
- Cosign keyless signing via OIDC: images pushed to GHCR are signed without managing signing keys; requires `id-token: write` permission on the workflow job

## Known Risks
- `ghcr.io/astral-sh/uv:latest` is not pinned and not monitored by Dependabot; a breaking `uv` release could silently break image builds
- GitHub App token secrets must be configured in **both** Actions and Dependabot secret settings; forgetting Dependabot secrets causes silent failures on Dependabot PRs
- The GitHub App must remain installed on the repository; uninstalling it breaks the Dependabot version bump workflow with a 404 error

## Extension Guidelines
- To add a new architecture, add it to both `mcp-proxy/build.yaml` (with base image) and the `matrix.arch` array in `.github/workflows/build.yaml`
- To add a linting step, insert it before the build step in the workflow
