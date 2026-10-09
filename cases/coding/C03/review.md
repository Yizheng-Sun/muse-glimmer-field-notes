# C03 — preparation and review

Reviewer reference only. Keep this file, `case.json`, `check.py`, source caches, fixed snapshots and the experiment repository history outside the coding agent's accessible filesystem. Give the agent only the sanitized prompt and broken source snapshot.

## Selection and provenance

The requirement parser accepts CR/LF in direct-reference URLs and can serialize an extra dependency line. This is a small, observable parsing problem with no network or runtime dependency requirements.

- Upstream repository: [pypa/packaging](https://github.com/pypa/packaging).
- Report and accepted fix: [PR #1379](https://github.com/pypa/packaging/pull/1379).
- Earliest directly verified report: PR opened **2026-08-10 11:43:04 UTC**. No separate issue was linked in GitHub's closing-issue references or identified in the PR body.
- Merge: **2026-10-01 13:47:32 UTC**, within the requested 14-day merge window. The report itself is older.
- Starting revision: `23669b1b69fb5fffbc773a68fc099166fc847356`.
- Fixed revision: `2602dd07d8bd5d6c54a3ce0e212f52eb2e127f3e`.
- The fixed revision is a squash commit with the starting revision as its sole parent. The starting version excludes the entire accepted patch.
- Changed files: `src/packaging/_tokenizer.py` and `tests/test_requirements.py`.
- The PR body does not disclose AI implementation usage; one review describes automated checks. Authorship is not independently established. Use “upstream merged fix” when describing the reference.

The prompt keeps the observable newline symptom and expected exception. It removes the PR's tokenizer expression, implementation suggestion, source links, authors, dates and fixed revision. It adds valid URL, horizontal-whitespace, marker and ordinary-requirement preservation requirements. These controls are already consistent with the starting API.

## Before/after verification

Prepared locally on macOS arm64 with **CPython 3.12.14**. The reviewer check imports directly from the chosen snapshot's `src/` and confirms the exact package and requirement module paths. No package installation or external request is required.

```sh
python3 scripts/prepare_case.py C03 --verify
python3 cases/coding/C03/check.py --source .runs/coding/C03/base
python3 cases/coding/C03/check.py --source .runs/coding/C03/fixed
```

The local before/after check has three test methods. The starting version exits **1**, with six expected `InvalidRequirement not raised` assertion failures: LF, CR and CRLF, each both trailing and followed by injected text. The fixed version exits **0**. Valid direct URLs, file URLs, fragments, trailing horizontal whitespace, markers and ordinary version requirements pass on both versions.

The preparation helper saves full logs and `verification.json` under `.runs/coding/C03/logs/<UTC timestamp>/`. Curated preparation evidence is in [C03.json](../../../evidence/preparation/C03.json). Exit **2** means invalid arguments, missing/incorrect source, unsupported Python or import/provenance setup failure; it must not be counted as a coding failure.

Relevant upstream coverage is in `tests/test_requirements.py`, including trailing-line-break handling, URL parsing and marker behavior. The custom check is reviewer-side and is not part of the agent bundle.

**5090 validation is pending.** After pulling, repeat the preparation command, record Python/OS and check output, and verify the agent's filesystem and network boundary before scored execution. No Glimmer attempt has been run. Record the experiment repository commit at that point.

## Reference and acceptable alternatives

The accepted patch changes URL-token whitespace handling and adds regression tests. The check does not inspect that implementation, patch text, token definitions or source formatting. A tokenizer change, parser validation, or another bounded correction can pass if it raises the public exception for the specified invalid inputs and preserves valid behavior.

This check covers the concrete CR/LF issue and preservation controls; it is not a complete URL validator or a security audit. No URL is fetched. These cases remain small calibration problems, so a successful result should not be extrapolated to large refactors.

## Scored attempt record

Not run. Record run ID/date, experiment repository commit, frozen runtime settings, boundary verification, elapsed time/tool calls, raw transcript and patch, reviewer check result, relevant upstream-test results, assistance and final outcome when the experiment is performed. Preserve failure or timeout evidence.
