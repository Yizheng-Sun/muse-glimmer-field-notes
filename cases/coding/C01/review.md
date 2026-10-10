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
- 5090 verification: the owner reported `base=1, fixed=0`, with report `.runs/coding/C01/logs/20261009T232712.390823Z/verification.json`. Complete remote environment details, setup duration and the raw preparation report have not been attached.

The check imports `click` from the requested snapshot's `src` directory and verifies `click.__file__` lies there. It observes public `Option` behavior and `CliRunner` results: missing/invalid choices, string/list/tuple environment names, individually quoted names with spaces/commas, empty hints, automatic-prefix help, disabled hint display, and actual environment fallback resolution. It does not inspect the patch or require a specific implementation.

The failure is visibly the malformed hint, for example `(env var: '['GLIMMER_CASE_MEASURE_A', 'GLIMMER_CASE_MEASURE_B']')`; the fixed output names both quoted variables separately. The check also catches empty hints instead of merely validating the common sequence example.

Relevant upstream tests are in `tests/test_options.py`, including `test_show_envvar`, automatic-prefix variants, `test_show_envvar_empty`, `test_missing_envvar` and `test_missing_envvar_sequence`. **The full upstream suite and standalone pytest regressions were not run during preparation.** The dependency-free reviewer check covers the changed behavior and adjacent controls. After a scored patch, run this check and inspect the diff; broader upstream validation can be added if that patch changes wider behavior.

## Upstream reference and acceptable alternatives

The merged reference normalizes string/sequence error hints, omits empty explicit configurations, and lets empty configurations fall back to automatic environment names in help. Other implementations are acceptable if they meet the public behavior in the prompt and preserve parsing and resolution. The grader does not require a particular helper, loop or code shape.

The check is focused rather than a proof that every Click feature works. It does not cover Windows console behavior, translation catalogs or every option type. The owner chose Hermes' local backend for the 5090 attempts; filesystem and public-network isolation are not enforced. Retain this limitation with the results.

## Scored attempt

**First autonomous attempt: FAIL.** Session `20261009_233133_8c1550`, Muse Glimmer with user-reported Hermes `v0.21.6+373.g46d7718`, on the 5090 local backend. The supplied session contains 60 actual tool calls over 218.56 seconds and no source edit. The owner's reviewer check reports six methods and 21 failing subcases. See the [first-attempt analysis](../../../evidence/coding/C01/attempt-01-analysis.md) and its derived summary for counts, raw-evidence hash and limitations. The experiment commit and complete frozen runtime settings remain unprovided.

**Separate assisted continuation: FAIL, partial fix.** A supplied source diff and later acceptance check demonstrate an implementation with four failing subcases. Independent reconstruction of that diff fixes 18 original failures, retains three empty-configuration/automatic-prefix help failures, and introduces one help-formatting failure. The model declared completion after existing upstream tests passed, but the case-specific acceptance check still fails. The latest transcript tail reports an 18-second, three-API-call invocation; the complete assisted history and its total added budget remain unverified. See the [assisted-continuation analysis](../../../evidence/coding/C01/assisted-continuation-analysis.md).

Keep these outcomes separate. Case-specific feedback or a human correction would be further assistance, rather than a revision of the original autonomous result.
