# Build the image once in CI and push it by digest

| | |
|---|---|
| ID | 0036 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M |
| Depends on | 0035 |
| Blocks | 0037 |
| Repos | mulearnbackend |

## Why

Building on each host from `git pull` means hosts can run different code, nothing is tested first, and rollback isn't clean. Build once in CI, push to a registry, and deploy the same digest everywhere ([ADR-013](../adr/ADR-013-immutable-images-by-digest.md)).

## Before you start

- Issue 0035 must be merged.
- A maintainer sets up GHCR permissions for the workflow (`packages: write`).

## What to do

1. Create `.github/workflows/image.yml`, triggered on `push` to `dev` and on version tags. It:
   - builds the image with Buildx;
   - pushes to `ghcr.io/gtech-mulearn/mulearnbackend` with the tags `sha-<short sha>` and, on tags, the version;
   - prints the pushed digest in the job summary.
2. Scan the image with Trivy and fail on critical vulnerabilities, with an allowlist file for accepted ones.
3. Write the digest to a build artifact (`image-digest.txt`), so the deploy script can consume it.

## Acceptance criteria

- [ ] A push to `dev` publishes an image and records its digest.
- [ ] The Trivy step runs and fails on a critical vulnerability (show it on a throwaway branch with an old base image).

## How to test

The workflow run on `dev` is the test. Paste the digest from the job summary in the pull request.

## Out of scope

- Deploying images (issues 0037 and 0045).

## Notes for reviewers

Check the workflow's permissions are the minimum it needs.
