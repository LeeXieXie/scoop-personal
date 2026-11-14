# Server timer stale queue recovery

**Goal:** Publish version 1.0.3 so an old, empty queued Actions run cannot keep
the server timer returning `busy` indefinitely. The user will pull the image and
recreate the existing BaoTa container after publication.

**Evidence:** Run 43475411130 remains `queued` in GitHub's API, has no jobs, and
has not changed since 2026-11-13T17:42:17Z. Ordinary cancellation was rejected;
force cancellation returned HTTP 409 saying the run had not been queued yet.
The existing timer treats every unfinished run in the latest 100 as blocking.

**Approach:** Keep the existing scheduler and HTTP client. Recheck old queued
runs individually after a configurable 1,800 seconds (zero disables recovery).
Ignore a rechecked completed run, or a still-old queued run with zero jobs.
Keep active runs and uncertain states blocking. Emit bounded, sanitized metadata
identifying blockers and ignored stale runs. Do not automatically cancel runs.

**Constraints:** No new dependencies. Preserve the 180-second cadence, bounded
GET retry, single-attempt dispatch POST, read-only `--check`, credential safety,
and existing workflow concurrency. The latest-100 check remains best effort.

## Implementation and validation

- [x] Add regression tests and observe failures before implementation. Cover
  stale empty queues, the age boundary and disable option, changed detail state,
  existing/running jobs, invalid metadata, HTTP failures, stop handling, safe
  diagnostics, and read-only checks.
- [x] Implement the narrow stale queue exception and run all Python tests,
  focused lint, syntax checks, and diff validation.
- [ ] Update deployment documentation and image workflow to version 1.0.3,
  keeping existing release tags intact. Obtain an independent code review.
- [ ] Commit with Lore trailers, integrate upstream changes, push, and verify
  Publish Server Image plus Server Timer for the released source revision.
- [ ] Report cancellation results, published artifact evidence, and BaoTa
  pull/recreate instructions without claiming the user's container was upgraded.

## Verification evidence before publication

- Existing baseline: 48 timer tests passed. Added 12 tests; the unchanged
  implementation reproduced `busy` instead of `dispatched` for an old empty
  queue, and the new state/metadata checks failed as expected.
- After implementation: all 60 timer tests and all 72 Python tests passed.
  Focused Ruff, Python compilation, YAML/Compose defaults, and diff checks passed.
- Live read-only check at 2026-11-15 00:24 China Standard Time returned `checked`
  and identified run 43475411130 as `queued_without_jobs`, age 81,748 seconds.
  This verifies the real stale-record exception without dispatching a workflow.
- GitHub's existing admin login could not cancel the record: ordinary cancel
  said it was completed; force-cancel returned HTTP 409 saying it had not been
  queued yet, while the read API still said `queued`. No successful cancellation
  is claimed. The image fix does not require this record to be deleted.
- Registry preflight: version 1.0.3 did not exist; version 1.0.2 retained digest
  `sha256:b4145e259111a689a633a18c9b850dc08e0fa0ed5f5110d42696057d424203c6`.
