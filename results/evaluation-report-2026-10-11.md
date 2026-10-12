# Muse Glimmer coding evaluation — 11 October 2026

**All 48 planned runs completed: 16 PASS, 32 FAIL (33.3% pass rate).** Each of four pinned cases was attempted once at three budgets and four requested reasoning strengths. Larger budgets had the highest observed success rate; requested Low reasoning scored highest in this batch.

The batch ran from **10 October, 21:44:08 to 11 October, 01:00:41 BST**: **3h 16m 33s** including preparation and grading. Summed agent execution was **3h 12m 16s**. Batch: `.runs/evaluation/20261010T204407.924852Z`; execution commit: `4e64a47`.

Each budget cell below lists outcomes in **Low / Medium / High / Xhigh** order. **P = acceptance PASS; F = acceptance FAIL.** These cells cover all 48 runs.

| Case and task | Small | Medium | Large | Passed |
| --- | --- | --- | --- | ---: |
| C01 — Click environment-variable hints | F / F / F / F | F / F / F / F | F / F / F / F | 0/12 (0%) |
| C02 — Click short-help sentence boundaries | P / F / F / F | P / F / F / F | P / P / P / F | 5/12 (41.7%) |
| C03 — Packaging direct-reference line breaks | F / F / F / F | P / P / F / F | F / P / P / F | 4/12 (33.3%) |
| C04 — Packaging drive-relative license paths | P / P / F / F | P / F / F / F | P / P / P / P | 7/12 (58.3%) |

Budget limits were **Small: 15 iterations / 5 minutes; Medium: 30 / 10 minutes; Large: 60 / 20 minutes**. The following are two separate views of the same 48 runs.

| Group | Setting | Passed | Pass rate | Mean agent time |
| --- | --- | ---: | ---: | ---: |
| Budget | Small | 3/16 | 18.8% | 114.9 s |
| Budget | Medium | 4/16 | 25.0% | 255.6 s |
| Budget | Large | 9/16 | 56.3% | 350.5 s |
| Requested reasoning | Low | 7/12 | 58.3% | 171.5 s |
| Requested reasoning | Medium | 5/12 | 41.7% | 216.5 s |
| Requested reasoning | High | 3/12 | 25.0% | 269.2 s |
| Requested reasoning | Xhigh | 1/12 | 8.3% | 304.1 s |

Recorded main-agent usage totaled **41,950,334 tokens**, including **39,723,632 cache-read tokens** (94.7%). Uncached input was **1,491,403 tokens** and output was **735,299**, totaling **2,226,702 uncached input-plus-output tokens**. Cache writes and recorded auxiliary usage were zero. Recorded work counts were **1,584 metered API calls, 1,626 assistant turns, and 1,578 tool iterations / tool calls**. The later [comparison audit](glimmer-vs-haiku-2026-10-11.md) found 39 visible post-budget summary episodes omitted from usage/API counters; actual HTTP request totals were not logged.

**39 runs reached their iteration budget, six finished normally, and three timed out.** Ten of the 16 passing patches came from iteration-budget stops. The nonzero Hermes exits in those 39 runs coincide with budget notices; functional success is determined by the acceptance checker.

Failure artifacts point mainly to unfinished implementation: **31 of 32 failing runs left files under `src/` unchanged**, including all 12 C01 attempts. C02's sole failing production patch was Medium budget / Medium reasoning. All five passing C02 runs also failed known stale upstream sentence-boundary fixtures; their acceptance results remain PASS.

Interpret this as a small calibration experiment: **one attempt per combination and four cases do not establish a general ranking**. Reasoning strength was configured but not independently verified at the server; zero reported reasoning tokens do not prove that reasoning was disabled. Usage for the three timeout runs may be incomplete. Execution used a local backend without enforced filesystem/network isolation, and the starting worktree was recorded as dirty; the runner and metrics hashes match the current repository files.

Source: all 48 per-run `result.json` records, acceptance/upstream logs, and the batch's frozen configuration and environment record. No jobs or result records are missing, and no metrics/evidence errors were recorded. Earlier individual attempts remain documented separately in [coding-results.md](coding-results.md).
