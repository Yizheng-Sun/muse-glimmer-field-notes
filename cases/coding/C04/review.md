# C04 — preparation and review

Reviewer reference only. Keep this file, `case.json`, `check.py`, source caches, fixed snapshots and the experiment repository history outside the coding agent's accessible filesystem. Give the agent only the sanitized prompt and broken source snapshot.

## Selection and provenance

License-file metadata accepts Windows drive-relative paths that are not scoped to the project directory. The reproduction is pure path validation and works on macOS and Linux without a Windows filesystem. It offers a bounded cross-platform input case with no runtime dependencies.

- Upstream repository: [pypa/packaging](https://github.com/pypa/packaging).
- Report and accepted fix: [PR #1382](https://github.com/pypa/packaging/pull/1382).
- Earliest directly verified report: PR opened **2026-08-11 14:09:58 UTC**. No separate issue was linked in GitHub's closing-issue references or identified in the PR body.
- Merge: **2026-10-02 02:15:17 UTC**, within the requested 14-day merge window. The report itself is older.
- Starting revision: `1f334c04c6918789974207733f194e11a47698f5`.
- Fixed revision: `022ae6c6fe5c2ef9615875d0ecfab1ae4024720f`.
- The fixed revision is a squash commit with the starting revision as its sole parent. The starting version excludes the entire accepted patch.
- Changed files: `src/packaging/metadata.py` and `tests/test_metadata.py`.
- No implementation AI disclosure was found in the retrieved PR body, comments or review bodies. Authorship is not independently established. Use “upstream merged fix” when describing the reference.

The prompt preserves the drive-relative path symptom and public validation contract. It removes the PR's path-library implementation suggestion, source links, authors, dates and fixed revision. It adds eager/lazy consistency, spelling preservation and pre-existing invalid-path controls.

## Before/after verification

Prepared locally on macOS arm64 with **CPython 3.12.14**. The reviewer check imports directly from the chosen snapshot's `src/` and confirms the exact package and metadata module paths. No package installation, network or filesystem escape is required.

```sh
python3 scripts/prepare_case.py C04 --verify
python3 cases/coding/C04/check.py --source .runs/coding/C04/base
python3 cases/coding/C04/check.py --source .runs/coding/C04/fixed
```

The local before/after check has four test methods. The starting version exits **1**, with five expected assertion failures: three drive-relative lazy-validation inputs and two eager-validation inputs. The fixed version exits **0**. Valid relative paths and existing rejection of traversal, absolute Windows/POSIX paths, backslashes and glob patterns pass on both versions.

Lazy validation must raise public `InvalidMetadata` identifying the `license-file` field. Eager validation must include that invalid field in the public aggregate error. Tests do not require exact error-message wording.

The preparation helper saves full logs and `verification.json` under `.runs/coding/C04/logs/<UTC timestamp>/`. Curated preparation evidence is in [C04.json](../../../evidence/preparation/C04.json). Exit **2** means invalid arguments, missing/incorrect source, unsupported Python or import/provenance setup failure; it must not be counted as a coding failure.

Relevant upstream coverage is in `tests/test_metadata.py`, particularly `test_valid_license_files` and `test_invalid_license_files`. The custom check is reviewer-side and is not part of the agent bundle.

**5090 validation is pending.** After pulling, repeat the preparation command, record Python/OS and check output, and verify the agent's filesystem and network boundary before scored execution. No Glimmer attempt has been run. Record the experiment repository commit at that point.

## Reference and acceptable alternatives

The accepted patch adds a drive-presence check to the existing path validation and regression inputs to upstream metadata tests. The reviewer check does not inspect that implementation or require the same library call. Any bounded correction can pass if it consistently rejects drive-relative paths and preserves the specified valid/invalid controls.

This is a metadata parser check; it does not attempt file access, packaging, archive extraction or a Windows system integration test. Its guarantee is limited to the declared input-validation behavior. Native 5090 preparation remains to be verified.

## Scored attempt record

Not run. Record run ID/date, experiment repository commit, frozen runtime settings, boundary verification, elapsed time/tool calls, raw transcript and patch, reviewer check result, relevant upstream-test results, assistance and final outcome when the experiment is performed. Preserve failure or timeout evidence.
