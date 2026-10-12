# Muse Glimmer versus Claude Haiku 5.5 — reliability, failure mechanisms and API cost

**Haiku passed 48/48 attempts; the recorded Glimmer setup passed 16/48. The clearest explanation in the traces is a gap in completing, repairing and retaining changes. Glimmer often found the right defect but finished with unchanged source. Haiku's recorded API usage cost approximately US$0.48; two additional successful summary requests were not metered, so the complete billed amount remains unverified.**

This compares the completed 10–11 October Glimmer batch on the 5090 with the 11 October Haiku API batch on the Mac. Haiku's exact model ID was **`claude-haiku-5-5`**, confirmed by saved API model metadata and all 48 exported sessions. Glimmer's saved endpoint metadata reported **`muse-glimmer`**, a GGUF model with approximately 27.85 billion parameters and **`Q4_K_M`** quantization. The evidence concerns these deployed agent systems on four small bugs; it does not isolate their underlying model capabilities.

The cases, prompts, external acceptance checkers, job order and budget limits were matched. An audit of all **96 preserved synthetic starting Git commits** found the original source-file fingerprints intact. Each case was attempted once at three budgets and four effort settings: Small **15 iterations / 5 minutes**, Medium **30 / 10 minutes**, Large **60 / 20 minutes**. Twelve attempts on one case are twelve settings of the same bug, rather than twelve independent coding problems.

| Recorded outcome | Muse Glimmer | Claude Haiku 5.5 |
| --- | ---: | ---: |
| Acceptance passes | 16/48 (33.3%) | 48/48 (100%) |
| Small-budget passes | 3/16 | 16/16 |
| Attempts retaining a production change | 17/48 | 48/48 |
| Mean agent time | 240.3 s | 58.7 s |
| Tool calls / iterations | 1,578 | 618 |
| Assistant turns | 1,626 | 666 |
| Read/search share of tool calls | 54.4% | 37.9% |
| Recorded processed tokens | 41,950,334 | 14,689,324 |
| Normal completion / iteration stop / timeout | 6 / 39 / 3 | 46 / 2 / 0 |

Haiku had shorter agent time in **46 of the 48 matched conditions**, averaging **75.6% less time** and **60.8% fewer tool calls**. Its recorded processed-token total was **65.0% lower**. These are execution observations across different hosts and tokenizers, with usage-accounting gaps described below. They do not measure isolated model generation speed.

| Case | Glimmer acceptance | Haiku acceptance | Haiku recorded API-cost estimate, all 12 settings |
| --- | ---: | ---: | ---: |
| C01 — environment-variable hints | 0/12 | 12/12 | $0.1153 |
| C02 — short-help sentence boundaries | 5/12 | 12/12 | $0.1512 |
| C03 — direct-reference URL line breaks | 4/12 | 12/12 | $0.1291 |
| C04 — drive-relative license paths | 7/12 | 12/12 | $0.0848 |

**The largest bottleneck was converting a diagnosis into an artifact.** Of Glimmer's 32 failures, **22 exhausted their iteration allowance without attempting a production edit**, four attempted edits rejected by tools, three timed out without editing, two discarded their edits, and one retained an incorrect patch. Therefore **31/32 failures ended with production code unchanged**. Among the 17 runs that retained a production change, 16 passed acceptance. This locates the failure stage; the retained-edit subset is selected, so its 94.1% pass rate does not prove that forcing an edit would solve the other cases.

C01 illustrates the difference particularly well. Glimmer devoted **372/420 calls (88.6%)** to reads and searches across its twelve attempts, with no retained production change. In the matched **C01 Large/Medium** pair, it identified the list-formatting and empty-value defects by tool call 11, then continued inspecting until call 60. Haiku attempted a production edit at call four, repaired an initial f-string issue, and finished in eleven calls. Glimmer used **444.2 seconds** and left no edit; Haiku used **46.2 seconds** and retained a passing source-and-test patch. [Glimmer trace](../.runs/trace-analysis-20261011/traces/C01-large-medium-r01.md), [Haiku transcript](../.runs/evaluation-haiku/20261011T153903.994222Z/runs/C01-large-medium-r01/transcript.log).

The operational inference is that this Glimmer setup often failed to recognize when it had enough evidence to act. Repeated inspection consumed the bounded tool allowance without advancing to an edit. Wall-clock exhaustion was not the main recorded endpoint: iteration exhaustion was much more common than timeout, and C01 still produced no fix with a 60-call ceiling. A faster server could reduce time spent in the loop; whether it would change the agent's decisions was not tested.

**Recovery from feedback separates the systems more clearly than the presence of mistakes.** Both agents encountered blocked inline scripts, rejected patches and faulty test fixtures. Glimmer recorded 71 unattended terminal-policy blocks; Haiku recorded 36. Glimmer additionally had 41 attempts to read directories with a file-reading tool and 27 refused overwrites of insufficiently read files. These are real environment constraints. Some patch failures involved escaped strings and ambiguous matching; the logs establish unsuitable arguments without identifying whether every defect originated in generation, transport or tool normalization.

In **C03 Large/Low**, Glimmer changed the URL regex and accidentally damaged its neighboring token rule, restored the entire file, and failed to retain the corrected URL change. Haiku applied the URL repair early, discovered that its own supposedly valid environment-marker fixture lacked required whitespace, corrected the fixture, and retained passing changes. Glimmer also demonstrated successful recovery in C03 Large/High by switching to a saved editing script after patch failures. Its capabilities were inconsistent across attempts, rather than uniformly absent. [Matched recovery evidence](../.runs/comparison-analysis-20261011/mechanisms.md).

This suggests a practical difference in how feedback affects the next action. A useful recovery changes the command form, narrows the patch, fixes the fixture, or verifies the current files. Several Glimmer failures instead continued exploring or repeating an unsuccessful operation. Under an unattended budget, each ineffective retry consumes capacity that the agent needs to finish. Tool-contract compatibility and the agent's response to failures both matter; their separate contributions were not experimentally isolated.

**Keeping track of the final files is an essential part of coding reliability.** Glimmer's **C02 Large/Xhigh** applied a plausible change, recognized the old fixture conflict, then discarded the source edit at call 55. Call 60 confirmed an empty diff, but its final answer still described the fix as present; acceptance failed. The earlier probes did not validate the final source. Haiku also accidentally reverted a change while checking a baseline in C01 Medium/Medium, but detected the missing production diff, reapplied the edit and ran post-edit checks. These examples show why a convincing final explanation must be checked against the retained artifact. [Glimmer rollback trace](../.runs/trace-analysis-20261011/traces/C02-large-xhigh-r01.md), [Haiku recovery transcript](../.runs/evaluation-haiku/20261011T153903.994222Z/runs/C01-medium-medium-r01/transcript.log).

**Test editing deserves a quality audit, not an automatic reward.** The statistic “attempts modifying an upstream `tests/` file” counts activity: Haiku 48/48, Glimmer 0/48. Adding a regression is appropriate when it demonstrates the defect and preserves valid behavior. Removing valid cases, loosening assertions without a specification reason, or changing expected values merely to silence failures would undermine that evidence.

The completed audit found **all 48 Haiku acceptance-checker copies unchanged**, matching the frozen checkers used for Glimmer. Thus the primary **48/48 acceptance result was not obtained by editing the grader**. It found no added skips/xfails and no removed, renamed or shadowed original upstream test functions. C01 and C03 preserve the inherited test cases; C04 adds invalid-path parameters while preserving the existing assertion bodies.

C02 deliberately changes sentence-boundary behavior, so one inherited expectation becomes obsolete. For `123 567 9. aaaa bbb` at width ten, the new lowercase-continuation rule produces `123 567...`; the original fixture expects `123 567 9.`. One Haiku attempt updates that expected output directly; eleven migrate the old terminal-period fixture to uppercase `Aaaa` and add relevant new-behavior coverage. Five do not re-add that exact numeric/lowercase input, although they add equivalent continuation/truncation controls. Two omit a regression for shortening at widths below three, while testing text that already fits at width two. C02 Small/Medium also broadens a shared length sanity assertion for the requested short-width ellipsis exception while retaining exact output equality. These are disclosed migrations and coverage limits, rather than evidence of acceptance-check manipulation. [Full test-quality audit](../.runs/comparison-analysis-20261011/test-quality.md).

Glimmer's existing focused suites passed in **42/48 runs**, including many unfixed cases; Haiku's final focused selections passed in **48/48**, using its edited tests. Those figures therefore concern different final test contents. C03's original 5,332 requirement tests all passed even when the line-break defect remained. C02 shows the converse: an obsolete expectation can fail a correct implementation of the new requirement. The unchanged external acceptance checks are the strongest common outcome measure; upstream results add compatibility and maintenance evidence that must be interpreted with the diff.

Haiku's score also has a coverage ceiling. C03 Medium/Xhigh rejects extra Unicode/control line boundaries without adding cases for those extra characters. Most C04 patches reject `1:x`, while Large/Xhigh preserves it; the acceptance checker does not distinguish that boundary. A perfect score on these checks establishes the requested tested behaviors, rather than complete compatibility across every input.

**More requested reasoning did not repair the workflow gap.** Glimmer's Low/Medium/High/Xhigh scores were **7/5/3/1 passes out of twelve**, with progressively longer mean times. Haiku passed all twelve at every effort, but Xhigh took about **3.25 times** as long as Low. This is consistent with unproductive deliberation or investigation consuming a finite budget in some Glimmer attempts. The requested effort controls were not independently verified at the server, so the experiment cannot establish a causal effect of increasing actual reasoning.

| Requested effort | Glimmer passes | Haiku passes | Haiku mean agent time | Haiku recorded cost for 12 runs |
| --- | ---: | ---: | ---: | ---: |
| Low | 7/12 | 12/12 | 32.7 s | $0.0582 |
| Medium | 5/12 | 12/12 | 41.6 s | $0.0829 |
| High | 3/12 | 12/12 | 54.2 s | $0.1088 |
| Xhigh | 1/12 | 12/12 | 106.2 s | $0.2305, plus unmetered summary usage |

The exposed reasoning text cannot settle how much useful internal thinking each model performed: Haiku returns summarized thinking, while Glimmer exposes longer reasoning text. Both separate reasoning-token counters report zero with availability warnings. Tool sequences, retained diffs and post-edit checks provide firmer evidence of progress than comparing the lengths of those texts.

**The API-cost figure is an auditable usage estimate.** All 664 captured Haiku usage responses used standard service, global routing and five-minute cache writes; no one-hour writes or server tools were recorded. The largest captured request prompt was **77,780 tokens**. Each metered call therefore falls below the 100,000-token higher-price threshold. These were regular Messages API requests. [Anthropic pricing and request-length tiers](https://platform.claude.com/docs/en/about-claude/pricing).

| Recorded token bucket | Tokens | USD per million tokens | Estimated USD |
| --- | ---: | ---: | ---: |
| Uncached input | 1,424 | $0.10 | $0.000142400 |
| Five-minute cache writes | 1,082,471 | $0.125 | $0.135308875 |
| Cache reads | 13,179,086 | $0.01 | $0.131790860 |
| Output, including provider-metered thinking | 426,343 | $0.50 | $0.213171500 |
| **Total** | **14,689,324** | — | **$0.480413635** |

Rates were checked against [Anthropic's Haiku 5.5 price table](https://platform.claude.com/docs/en/models/haiku-5-5/overview) on 11 October 2026. Each row is `tokens × rate / 1,000,000`; their sum exactly reconciles with Hermes's saved estimates. Approximately **89.7% of processed tokens were cache reads**, which receive a different rate from new input. Multiplying all 14.69 million tokens by a single input or output rate would misstate the cost.

That recorded total is about **one US cent per evaluated attempt**. The four **Small/Low** attempts alone all passed and totaled **$0.01707635**, approximately **1.7 US cents for those four attempts**. Those observed costs apply to these short tasks and settings. Xhigh accounted for almost half the metered spend without improving the acceptance score.

There were actually **666 successful HTTP Messages requests**, including two post-budget summaries for **C01 Small/Xhigh** and **C04 Small/Xhigh** whose usage was omitted from the counters. They generated responses but retained neither token usage nor a cost. All session exports have `actual_cost_usd: null` and `cost_status: estimated`; database zero defaults are not billing receipts. Consequently, **$0.4804 covers the recorded usage, and the complete experiment's account charge requires provider billing data**. It excludes taxes, credit/account adjustments and unrelated account activity. No inference evidence was found in the earlier local preparation/runtime-proof directories. [Response-by-response cost audit](../.runs/comparison-analysis-20261011/cost-audit.json).

Glimmer's usage counters likewise omit **39 visible post-budget summary episodes**, and three timeout records are partial. Its actual HTTP request count is unknown. These gaps qualify token/request totals without affecting the measured acceptance verdicts or supervisor elapsed times. The local Glimmer setup incurred no Anthropic API charge for this batch; GPU rental, electricity and hardware costs were not supplied and have not been assigned a dollar value.

The economic implication for these coding cases is that local inference still needs reliable completion to save work. Dividing the entire measured agent time by accepted patches yields approximately **12m 01s per accepted Glimmer attempt**, versus **58.7 seconds for Haiku**, including time spent on failed attempts. These are descriptive matrix totals, not predictions for unrelated projects. At the observed API prices, modest human diagnosis or rerun effort could dominate the model charge. Privacy, offline operation and control remain reasons to investigate a local agent, but this experiment has not assigned monetary values to them.

**Several deployment differences could contribute to the gap, and their effects remain unmeasured.** Glimmer's saved Hermes version is **v0.21.6+529.g6660547**, local `66605471e9f0`; Haiku used **v0.21.5+8892.g354724f**, commit `354724fb085162678964c116ceb4c40fc57c717c`, with a native-API compatibility wrapper. Glimmer's system text includes an additional tool-enforcement/discipline block; Haiku includes explicit replacement-patch guidance and its native adapter changes the provider-facing system framing. Identical case prompts therefore did not create identical complete model inputs.

Glimmer used a local quantized llama.cpp deployment with temperature 1.0, top-p 0.95 and top-k 64. Haiku used Anthropic's serving system and native adaptive effort controls. Quantization, model training, chat-template handling, tool-call parsing and provider formatting are possible contributors, but this comparison cannot assign them causal shares. Meta explicitly documents the importance of the model's chat template and native tool-call format, making rendered-template and parser verification a necessary follow-up before attributing the entire result to model ability. [Meta prompting guide](https://dev.meta.ai/docs/muse-glimmer/prompting).

Both setups had unenforced filesystem/network boundaries and conflicting source-only versus system-scratch instructions. Glimmer sometimes reused shared `/tmp` probe files; Haiku mainly used fresh per-run scratch, with a few temporary baseline copies. Review found no recorded access to the supplied reference fix or hidden checker and no recorded external-network operation. That is an observation of saved tools, not proof of enforced blindness. Each current copied Glimmer Click baseline contains two empty example files, but all preserved starting Git commits retain the original contents; the copy anomaly does not establish differing scored starts. [Provenance and runtime audit](../.runs/comparison-analysis-20261011/confounds.md).

A lightweight follow-up should keep these results intact, standardize the Hermes/tool instructions, verify Glimmer's rendered template and requested effort, use unique scratch directories, and account for every summary response. Run the four cases at Small/Low with three fresh repeats per model: **24 attempts total**. Record the first production-edit iteration, retained diff and final verification. This would test whether removing interface friction improves Glimmer's completion rate and whether the observed Haiku ceiling survives repetition. Architectural explanations would still require a separate controlled comparison of model/deployment variants.

The evidence supports a strong practical judgment for the blog: **this Glimmer deployment is substantially less ready for unattended coding than the tested Haiku 5.5 setup. Its recurring weakness is turning a correct diagnosis into a durable, verified change, recovering from tool feedback and tracking the final state.** The four selected tasks and one generation per condition support that account of these runs; they do not establish a universal model ranking.

Numerical sources: [Glimmer evaluation](evaluation-report-2026-10-11.md), [Glimmer trace analysis](agent-trace-analysis-2026-10-11.md), [Haiku evaluation](haiku-evaluation-report-2026-10-11.md), and the frozen `.runs/evaluation/20261010T204407.924852Z/` and `.runs/evaluation-haiku/20261011T153903.994222Z/` batches. Local audit links require this checkout; generated traces and audits remain ignored by Git. No new model inference was run to write this report.
