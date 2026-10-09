# Coding-case selection — 9 October 2026

Screened five Python repositories using primary GitHub PR metadata, changed-file diffs, merge commit parents and linked reports. The main merge window was **25 September–9 October 2026**; the permitted expansion was **9 September–9 October 2026**. Dates are UTC, inclusive. This is a convenience sample for a one-week blog experiment.

The [candidate ledger](candidates.csv) contains **14 inspected candidate PRs**: 12 in the primary window and two additional Click cases in the expanded window. Only the final four underwent full local behavioral preparation. Raw API responses, discovery snapshots and logs stay under ignored `.runs/discovery/`.

| Repository scanned | Discovery result | Selection |
| --- | --- | --- |
| pallets/click | 2 primary-window merges; 7 across expanded window | C01 #3884 and C02 #3865 |
| pypa/packaging | 17 merges, all within primary window; 10 candidates inspected | C03 #1379 and C04 #1382 |
| pallets/werkzeug | 10 primary-window merges; 24 across expanded window | ProxyFix #3298 retained as a reserve; would add a third repo and dependency |
| python-attrs/attrs | 4 expanded-window merges; docs, developer tooling or CI only | No suitable runtime case |
| Textualize/rich | Zero merges in either window | No eligible case; latest merge #4175 on 23 June, latest code fix #4079 on 12 April |

The final cases require **two source repositories, no third-party check dependencies and one preparation helper**. Every accepted patch changes only one production file. C01 exercises configuration and error/help presentation; C02 covers text summarization; C03 covers requirement parsing; C04 covers cross-platform metadata path validation. A new-feature case was considered (#1376) but the bounded dependency-free cases better fit this week's scope. This small set does not measure broad development work.

C02 expands to 30 days to add a different behavior while staying within two repositories. Three selected merges are in the two-week window. Packaging's PR reports date to August, even though their merges are recent. None of the four has a separate linked issue, so metadata records null issue fields and the actual PR-report dates rather than inventing issue dates.

## Exclusions and limits

- Rich offered no temporally eligible merge. Older April fixes were not substituted. [Latest merge #4175](https://github.com/Textualize/rich/pull/4175) is documentation only.
- The four attrs merges were [#1640](https://github.com/python-attrs/attrs/pull/1640) (contribution-guide typos), [#1635](https://github.com/python-attrs/attrs/pull/1635) (developer lock update), [#1632](https://github.com/python-attrs/attrs/pull/1632) (Actions updates), and [#1625](https://github.com/python-attrs/attrs/pull/1625) (documentation/comment word correction).
- Werkzeug [#3309](https://github.com/pallets/werkzeug/pull/3309) involves native Windows device-name behavior; mocking the platform would provide weaker evidence on Mac/Linux. [#3279](https://github.com/pallets/werkzeug/pull/3279) is an 18-commit, 14-file refactor. [#3308](https://github.com/pallets/werkzeug/pull/3308) is API restructuring. Release/support/type/deprecation changes were also screened out.
- Click [#3877](https://github.com/pallets/click/pull/3877) is a broader seven-file API/deprecation change; [#3876](https://github.com/pallets/click/pull/3876) synchronizes branches, and [#3861](https://github.com/pallets/click/pull/3861) is an internal refactor. #3860 remains a valid reserve but adds another help-section problem.
- Packaging performance-only [#1429](https://github.com/pypa/packaging/pull/1429) and [#1371](https://github.com/pypa/packaging/pull/1371) would need a reliable timing gate; functional output alone cannot fail before and pass after. CI/dependency/documentation changes (#1443, #1433, #1432, #1423, #1414, #1393) were screened out. Additional candidate decisions are in the ledger.

No selected case needed dependency installation or approached the 30-minute troubleshooting limit. Preliminary source-download/import checks established the first case end to end before the common helper was applied to all four. The final helper verification uses fresh Git archives, avoiding installed-package substitution and stale patched checkouts. Setup failures are distinguished from behavioral failures.

## Reference authorship

Call these **upstream merged reference fixes**. No implementation AI disclosure was found in inspected material for selected Click #3884/#3865 or Packaging #1382. Packaging #1379 includes disclosed automated review checks. This does not establish purely human authorship for any case.

Several alternatives explicitly disclose AI involvement: Packaging [#1411](https://github.com/pypa/packaging/pull/1411) and [#1412](https://github.com/pypa/packaging/pull/1412) name Hermes + GLM 5.3, [#1436](https://github.com/pypa/packaging/pull/1436) names Codex, and [#1376](https://github.com/pypa/packaging/pull/1376) discloses AI-assisted review and a suggested patch. #1412's initial body also contradicts the merged case-normalization semantics. These caveats informed selection and remain recorded.

## Preparation versus scored outcomes

All four are `prepared_locally`, with the identical checker failing the pinned base and passing the pinned upstream fixed version on this Mac. Curated evidence is in [evidence/preparation](../evidence/preparation/README.md). The checks exercise public behavior and preserve valid inputs; they do not require a specific implementation. They are focused acceptance checks; full upstream suites have not been run.

5090/Linux setup and the actual agent filesystem/network boundary are **pending**. No model or scored Hermes/Glimmer attempt was invoked, and the existing installation was unchanged. The selected four are frozen for future attempts; preserve failures and do not replace cases based on model performance.
