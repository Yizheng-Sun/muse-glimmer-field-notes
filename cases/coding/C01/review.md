# C01 — preparation and human review

This is evaluator reference material. Keep this file, `case.json`, the check, fixed source, discovery notes and experiment Git history outside the coding agent's accessible filesystem. Give the agent only its sanitized prompt and clean broken source.

## Selection

The case fixes confusing environment-variable hints shown to CLI users. It is a small configuration edge case: the upstream change touches one production file, one test file and the changelog. Click needs no runtime dependency for this macOS/Linux check.

The PR itself is the original report. It was created **2026-10-06 13:28:53 UTC** and merged **2026-10-06 20:59:00 UTC**, inside the two-week merge window. No separate issue is linked in its body; `case.json` records the PR as the original report instead of inventing an issue date.

The sanitized prompt converts the PR's before/after tables into requirements, changes the example option/variable names, and removes the implementation, source links, PR number and fixed revision. Tuple and empty-sequence behavior, automatic prefix fallback and adjacent controls are stated explicitly. The automatic prefix requirement follows the upstream regression tests.

The feature commit names Kevin Deldycke as author/committer, and Rowlando13 approved the PR. No AI disclosure was observed in the inspected PR body, issue comments, review bodies, inline comments or feature commit message. This is an upstream merged reference; human-only authorship has not been independently established.

## Before/after verification

- Starting revision: `bb695aaecdef95832d167fc1d508921745aa824e`.
- Upstream-fixed revision: `8c73ff134480f436faa0d041bd19aaf949aac22c`.
- Boundary: the starting revision is the merged fix's verified first parent and precedes its sole feature commit `c53d3732b98c764932e146c007146ad402acb229`.
- Local environment: Python 3.12.14 on macOS 26.7.1, arm64. The check needs Python 3.10+ and no third-party dependencies; the preparation helper needs Python 3.12+.
- Preparation command: `python3 scripts/prepare_case.py C01 --verify`.
- Direct check: `python3 cases/coding/C01/check.py --source .runs/coding/C01/base`, and the same command with `fixed`.
- Actual result: the broken version exits **1**, with **21 failing subcases** across six test methods; the upstream-fixed version exits **0**, with all six methods passing. Setup/import errors use exit 2, distinct from the demonstrated behavior failure.
- Selected results, environment, hashes, experiment commit and ignored raw-log paths: [preparation evidence](../../../evidence/preparation/C01.json).
- 5090 setup time and verification: **pending**. No remote validation is claimed.

The check imports `click` from the requested snapshot's `src` directory and verifies `click.__file__` lies there. It observes public `Option` behavior and `CliRunner` results: missing/invalid choices, string/list/tuple environment names, individually quoted names with spaces/commas, empty hints, automatic-prefix help, disabled hint display, and actual environment fallback resolution. It does not inspect the patch or require a specific implementation.

The failure is visibly the malformed hint, for example `(env var: '['GLIMMER_CASE_MEASURE_A', 'GLIMMER_CASE_MEASURE_B']')`; the fixed output names both quoted variables separately. The check also catches empty hints instead of merely validating the common sequence example.

Relevant upstream tests are in `tests/test_options.py`, including `test_show_envvar`, automatic-prefix variants, `test_show_envvar_empty`, `test_missing_envvar` and `test_missing_envvar_sequence`. **The full upstream suite and standalone pytest regressions were not run during preparation.** The dependency-free reviewer check covers the changed behavior and adjacent controls. After a scored patch, run this check and inspect the diff; broader upstream validation can be added if that patch changes wider behavior.

## Upstream reference and acceptable alternatives

The merged reference normalizes string/sequence error hints, omits empty explicit configurations, and lets empty configurations fall back to automatic environment names in help. Other implementations are acceptable if they meet the public behavior in the prompt and preserve parsing and resolution. The grader does not require a particular helper, loop or code shape.

The check is focused rather than a proof that every Click feature works. It does not cover Windows console behavior, translation catalogs or every option type. The 5090 must rerun preparation and verify filesystem/network isolation before a scored attempt.

## Scored attempt

**Not run.** Record the eventual run ID/date, experiment commit, runtime settings, enforced filesystem/network boundary, raw transcript/patch paths, post-patch verification, hints or human edits, verdict and failure cause. Do not describe this preparation result as a Glimmer coding result.
