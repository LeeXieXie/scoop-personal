# Server Timer Transport Fix Implementation Plan

**Goal:** Publish a backward-compatible 1.0.2 timer image that avoids the large
uncompressed GitHub response implicated in the observed invalid-JSON failures.

**Architecture:** Keep the existing standard-library HTTP client and scheduler.
Negotiate gzip for GET requests, bound both wire and decoded response sizes to
4 MiB, detect incomplete responses before parsing, and reuse bounded GET retries.
Publish through the existing GitHub Actions workflow to GHCR for amd64 and arm64.

**Constraints:** No new dependencies. Keep the latest-100 queue check, 180-second
default cadence, fail-closed queue handling, no redirect credential forwarding,
and no automatic POST retry. Never log credentials, response bodies, or arbitrary
remote header/error text. Existing BaoTa credentials and running containers are
not modified as part of publishing the image.

## Task 1: Protect and fix response decoding

Files: `scripts/server_upstream_timer.py`, `scripts/test_server_upstream_timer.py`.

- [x] Add regression tests for gzip-negotiated GETs, valid compressed and identity
  JSON, Content-Length truncation (including an otherwise valid JSON prefix),
  corrupt/truncated gzip, wire and decoded size limits, and sanitized diagnostics.
- [x] Run `python -m unittest discover -s scripts -p test_server_upstream_timer.py
  -v` before implementation and confirm the new tests fail for missing behavior.
- [x] Add bounded decoding and completeness checks, preserving GET retries and
  single-attempt POST dispatch. Record safe numeric/allowlisted diagnostics only.
- [x] Run the timer regression suite again and confirm all tests pass.

## Task 2: Publish the fixed container

Files: `.github/workflows/publish-server-image.yml`,
`.github/workflows/server-timer.yml`, `deploy/server-timer/BAOTA.md`,
`deploy/server-timer/README.md`.

- [x] Change the release image version from 1.0.1 to 1.0.2 while preserving the
  rolling latest tag and full source-SHA tag. Keep earlier release tags intact.
- [x] Correct the existing BaoTa validation assertion from 300 to the documented
  180-second command, without changing the scheduler's interval.
- [x] Document gzip, safe incomplete-response diagnostics, and pull/recreate
  instructions for upgrading from 1.0.0 or 1.0.1. Do not claim server migration.
- [x] Validate YAML and regression tests before committing.

## Task 3: Review and verify the published artifact

- [x] Obtain an independent security/correctness review of the bounded decoder,
  tests, workflow versioning, and credential handling; resolve actionable defects.
- [x] Run all Python tests, focused lint, syntax checks, and `git diff --check`.
- [ ] Commit using Lore intent and verification trailers, integrate any upstream
  automatic manifest updates without reverting them, and push to master.
- [ ] Wait for Publish Server Image and Server Timer to finish successfully for
  the pushed source revision. Verify both platform manifests and image labels.
- [ ] Pull the versioned image on the affected server and run isolated read-only
  `--check` requests using the existing runtime token without exposing it or
  starting a second scheduler. Report the image digest and verification boundary.
