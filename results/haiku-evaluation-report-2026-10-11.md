# Claude Haiku 5.5 coding evaluation — 11 October 2026

**Claude Haiku 5.5 passed all 48 coding attempts: 12/12 for each of C01–C04.** Every final patch also passed the runner's focused upstream tests. All 16 Small-budget attempts passed, so these four cases did not require the larger budgets to achieve functional success in this batch.

The model used was **`claude-haiku-5-5`**, through **Anthropic's direct API at `https://api.anthropic.com`**. The saved Models API response identifies it as **“Claude Haiku 5.5”**, with `created_at: 2026-10-07T18:00:00Z`; all 48 session exports and all 48 result records contain that same model ID. This agrees with [Anthropic's Haiku 5.5 documentation](https://platform.claude.com/docs/en/models/haiku-5-5/overview). Anthropic documents this generation's dateless IDs as fixed model snapshots; no separate dated suffix is needed. [Model versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).

Batch: `.runs/evaluation-haiku/20261011T153903.994222Z`. The recorded attempts span **11 October, 16:39:12–17:29:33 BST: 50m 21s**, including per-attempt setup and grading. Main-agent execution summed to **46m 56s**. Mean agent time was **58.7 seconds**, median **47.8 seconds**, and the range **19.3–167.3 seconds**. Initial batch preparation preceded the first attempt by approximately eight seconds.

The matrix contained four pinned tasks × three budgets × four requested efforts × one repeat, with no missing or duplicate jobs. Budgets capped tool-calling iterations and elapsed agent time: **Small 15 / 300 seconds; Medium 30 / 600 seconds; Large 60 / 1,200 seconds**. Token usage was measured, rather than capped. Each attempt used a fresh source copy, Hermes home and conversation. The source, sanitized prompt, case metadata and acceptance checker matched the original case fingerprints.

| Case and task | Acceptance | Focused upstream checks | Mean agent time | Mean tool calls | Mean assistant turns |
| --- | ---: | ---: | ---: | ---: | ---: |
| C01 — Click environment-variable hints | 12/12 | 12/12 | 59.5 s | 13.8 | 14.8 |
| C02 — Click short-help sentence boundaries | 12/12 | 12/12 | 78.8 s | 12.1 | 13.1 |
| C03 — Packaging direct-reference line breaks | 12/12 | 12/12 | 52.7 s | 12.7 | 13.7 |
| C04 — Packaging drive-relative license paths | 12/12 | 12/12 | 43.6 s | 12.9 | 13.9 |
| **Overall** | **48/48** | **48/48** | **58.7 s** | **12.9** | **13.9** |

The focused upstream selections passed **151–161 tests for C01, 28–39 for C02, 5,341–5,347 for C03, and 14–16 for C04**, depending on the added parametrized cases. These are selected suites, not evidence that every upstream project test passed. All 48 attempts retained a production fix and changed one file under `tests/` to add or maintain regression coverage.

| Requested effort | Acceptance | Mean agent time | Mean tool calls | Mean recorded total tokens | Mean output tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Low | 12/12 | 32.7 s | 9.2 | 160,968 | 3,624 |
| Medium | 12/12 | 41.6 s | 11.8 | 235,128 | 5,316 |
| High | 12/12 | 54.2 s | 12.4 | 272,251 | 7,884 |
| Xhigh | 12/12 | 106.2 s | 18.1 | 555,764 | 18,705 |

**Low was the most efficient observed setting for these cases.** Xhigh took approximately **3.25 times** as long and used **3.45 times** as many recorded tokens, with the same acceptance rate. That supports using Low as the starting point for this small task set; it does not establish that extra reasoning has no value on harder tasks. Requests used adaptive thinking and the native `output_config.effort` field. The local request builder was verified for all four settings, but actual request-wire capture and backend effort behavior were not independently verified. [Anthropic effort guide](https://platform.claude.com/docs/en/build-with-claude/effort).

| Budget | Acceptance | Mean agent time | Mean tool calls |
| --- | ---: | ---: | ---: |
| Small | 16/16 | 48.2 s | 10.8 |
| Medium | 16/16 | 63.4 s | 13.4 |
| Large | 16/16 | 64.4 s | 14.5 |

The larger ceilings allowed some runs to spend more time on verification and test maintenance without improving the measured pass rate. There was one attempt per condition, so these averages also include variation between independently generated fixes.

The traces show a productive pattern: find the relevant implementation, make a bounded edit, add tests, respond to failures, and retain the correction. **C01** normalized environment-variable sequences and empty configurations in both error hints and help. Some attempts initially introduced an undefined helper, incompatible nested f-string syntax, or an incorrectly escaped test insertion, then repaired them. **C02** changed sentence detection, width handling and the obsolete upstream sentence fixtures; four runs initially added a width-two ellipsis case to a shared test whose length assertion rejected that case, then separated or removed the incompatible assertion. These were recovered intermediate errors; the final acceptance and upstream checks passed.

**C03** usually changed the URL token's character class to exclude CR and LF, preserving valid URL and whitespace controls. [C03-medium-xhigh-r01](../.runs/evaluation-haiku/20261011T153903.994222Z/runs/C03-medium-xhigh-r01/source.patch) additionally excluded every `str.splitlines()` boundary, including Unicode separators, but its added tests covered only LF/CR/CRLF. That broader behavior warrants review beyond the passing acceptance result. **C04** used `PureWindowsPath(...).drive` in 11/12 patches, providing host-independent drive detection; [C04-large-xhigh-r01](../.runs/evaluation-haiku/20261011T153903.994222Z/runs/C04-large-xhigh-r01/source.patch) used an explicit ASCII drive-prefix check. The implementations differ beyond the acceptance boundary: a post-run probe confirmed that Small/Low rejects `1:x`, while Large/Xhigh preserves it. The checker does not distinguish those choices. Only the latter patch added a dedicated eager-validation regression. Other patches could satisfy eager validation through the shared validator without adding a separate test for it.

**46 runs finished normally; two reached their 15-iteration limit.** `C01-small-xhigh-r01` and `C04-small-xhigh-r01` exited Hermes with status 1 and an iteration-budget notice, but both retained passing fixes and passing focused tests. Their functional verdict remains PASS under the supplied checks. C04's final message explicitly noted that its dedicated eager-validation test remained unwritten. No run timed out, and no final acceptance failure was recorded.

Total recorded main-agent work was **664 metered API responses, 666 assistant turns and 618 tool calls / iterations**. HTTP logs show **666 successful Messages requests**; the two extra post-budget summaries lack usage accounting. Recorded tokens were:

| Token bucket | Total |
| --- | ---: |
| Uncached input, excluding cache creation | 1,424 |
| Cache creation / writes | 1,082,471 |
| Cache reads | 13,179,086 |
| Output, including provider-metered thinking | 426,343 |
| **Total processed tokens** | **14,689,324** |

Cache reads account for **89.7%** of the total; repeated cached prompts are included each time they are processed. The small uncached-input count therefore does not mean the tasks used only 1,424 input tokens: input plus cache creation was **1,083,895 tokens**. Main-agent usage is reported separately from auxiliary usage, which was recorded as zero. The [comparison and cost report](glimmer-vs-haiku-2026-10-11.md) prices the metered buckets at **US$0.480413635**, with two unmetered summary requests and no captured actual billing amount.

The saved sessions contain **356 assistant messages with exposed thinking text, totaling 198,798 characters**, counted once where export fields duplicate it. The configured API returns summarized thinking. These records support analysis of the exposed decisions and tool behavior; they are not a complete internal reasoning trace. The separate reasoning-token counter is zero with an availability warning and does not demonstrate that reasoning was disabled.

| Same 48-case-condition matrix | Haiku API on Mac | Muse Glimmer on 5090 |
| --- | ---: | ---: |
| Acceptance passes | 48/48 (100%) | 16/48 (33.3%) |
| Mean agent time | 58.7 s | 240.3 s |
| Tool calls / iterations | 618 | 1,578 |
| Assistant turns | 666 | 1,626 |
| Recorded processed tokens | 14,689,324 | 41,950,334 |
| Attempts modifying an upstream `tests/` file | 48/48 | 0/48 |

In these executions, Haiku used **75.6% less agent time**, **60.8% fewer tool calls** and **65.0% fewer recorded processed tokens**. Glimmer also wrote reproduction scripts, so the last row counts changes to an upstream test file. It measures editing activity rather than test quality. The [test-quality audit](../.runs/comparison-analysis-20261011/test-quality.md) found the external grader unchanged and disclosed C02 fixture migrations and remaining coverage limits. Haiku's stronger result combined a passing patch with regression additions; Glimmer's most common failed endpoint was an unchanged production source.

Treat this as a comparison of the two recorded setups. There are **four calibration tasks and one repeat per condition**, not a representative benchmark. Hosts, Hermes versions, provider formatting, system text, tokenizers, caching and generation defaults differ. Haiku used Hermes commit `354724fb085162678964c116ceb4c40fc57c717c` and Anthropic SDK `0.87.0`; the Glimmer matrix's frozen version log records **v0.21.6+529.g6660547**, local commit `66605471e9f0`. The Haiku compatibility wrapper enabled native effort controls and preserved prior thinking blocks. Its hashes and runtime proof are saved. The runner used a 131,072-token context setting and the native adapter's 128,000-token output ceiling; matching effort labels does not imply equivalent reasoning budgets. Three Glimmer usage records are partial after termination, and its counters omit 39 visible post-budget summary episodes.

Filesystem and network isolation were **not enforced**. Review found no recorded tool access to the hidden checker/reference fix and no recorded external-network operation. Some self-written reproduction probes used Hermes scratch directories outside the supplied source. These trace observations do not establish an enforced blind boundary. Passing the supplied checks also does not establish complete behavioral compatibility beyond their coverage.

For the blog, the supported finding is: **Haiku 5.5 consistently produced corrections that passed the supplied acceptance and focused upstream tests on all four small cases, including under the smallest budget. Low effort achieved the same functional score with substantially less time and usage than Xhigh. The recorded Glimmer setup struggled primarily to complete and retain its fixes.**

Evidence: [saved model metadata](../.runs/evaluation-haiku/20261011T153903.994222Z/server-models.json), [frozen configuration](../.runs/evaluation-haiku/20261011T153903.994222Z/config.json), [runtime proof](../.runs/evaluation-haiku/20261011T153903.994222Z/haiku-runtime.json), [all 48 results](../.runs/evaluation-haiku/20261011T153903.994222Z/results.jsonl), [per-condition summary](../.runs/evaluation-haiku/20261011T153903.994222Z/summary.md), [Click trace-review notes](../.runs/haiku-report-analysis-20261011/click-notes.md), [Packaging trace-review notes](../.runs/haiku-report-analysis-20261011/other-notes.md), and [Glimmer report](evaluation-report-2026-10-11.md). Each Haiku `runs/<run-id>/` directory preserves `session.jsonl`, `transcript.log`, `source.patch`, `check.log` and `upstream-check.log`. Raw evidence links are local to this checkout because `.runs/` remains ignored by Git.
