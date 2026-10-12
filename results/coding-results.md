# Coding results

The **Claude Haiku 5.5 API comparison completed on 11 October 2026: 48/48 acceptance passes and 48/48 focused upstream passes**. The exact recorded model ID was `claude-haiku-5-5`. See the [Haiku performance report](haiku-evaluation-report-2026-10-11.md) for model confirmation, effort/budget comparisons, token/time/turn accounting, recovered errors and comparison limits.

The [Glimmer-versus-Haiku analysis](glimmer-vs-haiku-2026-10-11.md) explains the completion/recovery gap, audits upstream test changes and estimates recorded Haiku API usage at **US$0.48**, with two unmetered summary requests and actual billing unavailable.

The **Muse Glimmer evaluation** also completed on **11 October 2026**. All four cases ran at three budgets and four requested reasoning strengths, with one attempt per combination: **48 completed runs, 16 PASS and 32 FAIL**.

| Case | Completed runs | PASS | FAIL | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| C01 | 12 | 0 | 12 | 0.0% |
| C02 | 12 | 5 | 7 | 41.7% |
| C03 | 12 | 4 | 8 | 33.3% |
| C04 | 12 | 7 | 5 | 58.3% |
| **Total** | **48** | **16** | **32** | **33.3%** |

The [concise evaluation report](evaluation-report-2026-10-11.md) includes every combination, budget/reasoning comparisons, token/time/turn totals and limitations. Functional outcomes use the unchanged acceptance checks; process exits are recorded separately.

The [agent trace analysis](agent-trace-analysis-2026-10-11.md) reviews all 48 recorded sessions, reasoning text, tool use, edits and failure modes, with links to full saved traces.

**Earlier individual attempts.** These C01/C02 runs preceded the automated matrix and retain their original outcomes. The owner supplied the 5090 results; selected evidence includes reviewer reconstruction where stated. Tool counts below are actual calls counted from session exports.

| Case | Original individual result | Acceptance | Tool calls | Session duration | Evidence |
| --- | --- | --- | --- | --- | --- |
| C01 | FAIL | Six methods; 21 failing subcases; no source edit | 60 | 218.56 s | [Analysis](../evidence/coding/C01/attempt-01-analysis.md) |
| C02 | PASS | All five methods pass; one source patch | 60 | 331.83 s | [Analysis](../evidence/coding/C02/attempt-01-analysis.md) |

C01's separate [assisted continuation](../evidence/coding/C01/assisted-continuation-analysis.md) produced a partial fix but still failed four subcases. It does not replace the first autonomous result.

C02 exhausted its tool budget after producing a passing fix. Its remaining focused upstream failure is an old expectation incompatible with the requested new sentence rule; Glimmer identified the conflict but did not update the test. Record functional success and incomplete test maintenance separately.

The chosen Hermes backend is local. Filesystem and public-network isolation were not enforced; the analyses describe the observed scope deviations. The completed matrix's frozen inputs, configuration, per-run records and raw artifacts are available under ignored `.runs/evaluation/20261010T204407.924852Z/`. Server reasoning behavior has not been independently verified.
