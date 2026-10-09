# Muse Glimmer blog experiment: one-week project plan

Prepared: 9 October 2026

Target article: **Living With Muse Glimmer: A Local Always-On Agent With a Single 5090**

Current status: **Muse Glimmer and Hermes are fully set up. C01–C04 are prepared and verified locally on this Mac; 5090 validation remains pending.** Use one GitHub repository, edited on this computer and pulled on the 5090 machine. Runtime installation is complete; record the existing settings rather than rebuilding the setup. The next step is to repeat case preparation on the 5090 and verify the agent boundary before scored attempts.

Private repository: [Yizheng-Sun/muse-glimmer-field-notes](https://github.com/Yizheng-Sun/muse-glimmer-field-notes).

## 1. Goal and scope

Build a small, repeatable experiment that answers: **Would I reach for this local assistant first, and where would I still take over?** Use the attached experiment outline as the scope. Budget roughly **28–32 hours across seven calendar days**, including preparation, observation and assembling the evidence.

The week should produce:

- Four coding cases based on recent public issues and merged PRs.
- Four daily workflows using your own material: morning briefing, article capture, blog assistance and evening handover.
- Morning and evening scheduled runs observed for at least three consecutive days: six scheduled opportunities, with successes and misses recorded.
- An unfiltered diary of actual assistant requests, including requests Glimmer could not attempt.
- A concise results summary and examples ready to use in the blog.

Completion means the experiments are attempted and documented. It does not require Glimmer to succeed at everything.

Use the same GitHub repository and relative paths on both computers. Author the case definitions, prompts and review notes here, commit and push, then pull on the 5090 to prepare and run them. Run inference and Hermes on the 5090 using the existing setup. Avoid absolute paths tied to either computer.

## 2. Use an existing agent, with a small evidence wrapper

Recommended stack:

| Part | Choice | Purpose |
| --- | --- | --- |
| Model server | CUDA-enabled llama.cpp with a ready-made four-bit Muse Glimmer GGUF | Local inference on the 5090 |
| Agent | Hermes Agent, connected to the local endpoint | Existing tool loop, CLI sessions and scheduled tasks |
| Inputs and memory | Local Markdown and CSV files | Easy to inspect, update and back up |
| Evidence | Native transcripts, text logs, patches and CSV result tables | Enough detail for the article |
| Custom code | At most two small Python scripts using the standard library | Launch cases consistently and summarize results |

Meta's [model card](https://huggingface.co/meta-models/Muse-Glimmer-30B/blob/main/README.md) provides quantized variants intended for 24/32 GB hardware. Use quantized weights rather than the full-precision checkpoint. NVIDIA lists the [RTX 5090 as having 32 GB VRAM](https://developer.nvidia.com/blog/run-local-agentic-ai-workflows-with-metas-muse-glimmer-on-nvidia).

The runtime setup is complete. Retain the working deployment and use Meta's [llama.cpp recipe](https://github.com/meta-models/meta-oss-cookbook/blob/main/inference-server/llama-cpp.md) and the [Hermes quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/) as references only when needed. The recipe describes server-side tool-call parsing, so we should not write a Glimmer-specific agent loop.

Architecture:

```text
CLI request or scheduled job
          |
          v
    Hermes Agent <----> local Muse Glimmer server
          |
          v
 files / shell / public article retrieval
          |
          v
 saved output + transcript + human verification
```

Use Hermes' [built-in cron and gateway](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/) for scheduling. Keep the model server and gateway running between requests. Here, “always-on” means available and able to execute scheduled work while you are away.

### Record the existing configuration

The following are the original suggested defaults, not a request to change the working setup. Record the actual configuration and freeze it before scored runs.

- Bind the inference endpoint to loopback, for example `http://127.0.0.1:8080/v1`; use a stable model alias.
- Run one task at a time. Keep coding sessions outside the morning/evening job windows.
- Start with a 32K context and one server slot. If preparation reveals truncation, try 64K only if it fits. Freeze the working setting before scored runs.
- Use `high` reasoning initially and the model-card sampling defaults: temperature 1.0, top-p 0.95, top-k 64. Record the settings actually supported and applied.
- For llama.cpp, configure reasoning through `chat_template_kwargs.reasoning_strength`; the cookbook notes that `reasoning_effort` is not implemented there.
- Leave DFlash and performance tuning out of the initial build. Add them only if needed to make the experiment practical, before freezing settings.
- Route any enabled helper/compression model calls to the same local Glimmer endpoint, and disable cloud fallbacks. Check the [Hermes configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration), including auxiliary model overrides.
- Enable only the tools needed for the experiments. Use CLI interaction and local file delivery during this week.

Record exact model artifact/revision, quantization, runtime and agent versions, launch command, context, reasoning and sampling settings, OS, CPU, RAM and GPU in `config/run-settings.md`. Measure actual VRAM use and elapsed task time; do not substitute published throughput for your own results.

## 3. Keep the project small

One repository, with the same layout on both computers:

```text
PLAN.md
README.md                       # push/pull workflow and preparation steps
.gitignore                      # machine-specific and generated files
config/run-settings.md          # frozen environment and settings
cases/coding/README.md           # selection and preparation checklist
cases/coding/_template/          # copy to C01 ... C04 when selecting cases
cases/coding/<case-id>/
  case.json                     # source and pinned revisions; human metadata
  prompt.md                     # sanitized request to give Glimmer
  check.py                      # reviewer-side behavioral acceptance check
  review.md                     # references, verification and human verdict
cases/workflows/W01.md ... W04.md
.runs/coding/<case-id>/<run-id>/  # ignored, generated source and raw evidence
workspace/daily/
  inputs/                       # calendar, tasks, activity, articles, notes
  memory.md                     # preferences, decisions, unfinished work
  outputs/                      # dated briefings, reading notes, drafts
evidence/<run-id>/               # selected, redacted output, patch and checks
results/
  candidates.csv                # inspected coding sources and selection decisions
  coding-selection.md           # discovery scope and exclusions
  runs.csv                      # curated experiment outcomes
  schedule.csv                  # every expected scheduled execution
  diary.csv                     # actual usage, separate from curated tasks
  summary.md                    # tables and examples for the blog
scripts/
  prepare_case.py                # existing stdlib source preparation/verification
  run_case.py                    # optional later thin CLI wrapper
  summarize.py                   # optional CSV-to-Markdown summary
```

Case metadata and human review notes belong in this same repository and will be pulled onto the 5090. During a coding run, expose only that case's sanitized prompt and generated pre-fix source to Glimmer. The repository's metadata, review notes, Git history, source cache and other cases must remain outside the agent's accessible filesystem. Use the existing runtime's filesystem/container isolation for this; changing the current directory or adding a prompt instruction does not enforce isolation. Check the boundary before claiming a run was blind; if it cannot be enforced, record possible solution exposure as a limitation.

Generated sources, dependency environments, source caches and raw logs live inside ignored `.runs/` directories in the checkout. They are regenerated from pinned revisions and are not another manually maintained project. Commit selected, redacted evidence and result summaries. Keep model weights, credentials, machine-specific Hermes settings and private daily inputs out of Git.

### Synchronize through GitHub

1. Here: edit case files, review the diff, commit the intended files and push.
2. On the 5090: run `git pull --ff-only`, record the experiment repository's current commit, and generate the selected case workspace.
3. Run Glimmer on that generated workspace. Collect raw evidence under `.runs/`, then save selected evidence and a verdict in tracked project files.
4. On the 5090: review those result files, commit and push them.
5. Here: pull with `git pull --ff-only` before continuing analysis or editing the same files.

Keep this sequential during the experiment to avoid both computers editing the same files simultaneously. Avoid broad `git add .` when recording results; add the intended paths explicitly. Use `https://github.com/Yizheng-Sun/muse-glimmer-field-notes.git` as this project's shared remote; the 5090 clone needs GitHub authentication to access the private repository.

`run_case.py`, if needed, should invoke the installed Hermes CLI, enforce a timeout, and save its transcript and run metadata. `summarize.py` should turn CSV records into a Markdown table. Reuse native exports when they cover this already. Neither script needs its own agent, database or scheduler.

## 4. Prepare the coding cases

Scan three to five familiar repositories, aiming for roughly 12 candidates. Prefer taking the final four from one or two repositories to reduce setup work. Time-box discovery to two hours; record a smaller pool if necessary.

Search recently merged fixes with the outline's two-week window (`merged:>=2026-09-25` if collecting now). If the project starts later, move the window accordingly. Expand to one month only if needed. Prefer a visible bug, input edge case, configuration problem and small feature, with roughly 1–5 meaningful changed files. Record issue dates as well as merge dates.

Before selection, each candidate needs:

1. A specific starting commit, issue/PR links, dates and a bounded user requirement.
2. A reproduction or meaningful test that fails on the starting version and passes on the human-fixed version.
3. Dependencies prepared ahead of the agent run. Exclude candidates needing more than about 30 minutes of installation/debugging.
4. A sanitized prompt without implementation hints from the PR. Record any adaptation of the original request.

Give Glimmer a clean pre-fix source snapshot without Git history, generated under `.runs/` from the case's pinned starting commit. Preinstall dependencies, disable browsing tools, and block public-internet access for the coding run while retaining access to the local model server. Keep the shared repository and human reference material outside the agent's filesystem boundary, and use fresh coding sessions without daily-workflow memory. Source downloads and verification happen before or after this isolated run.

The preparation checklist and reusable files are in `cases/coding/`. Local preparation is complete: four cases from two repositories, with actual failure/pass evidence and one helper. See `results/candidates.csv` and `results/coding-selection.md` for selection, including the 30-day expansion for C02 and upstream authorship caveats. Use “upstream reference fix” rather than asserting purely human authorship. A case marked `prepared_locally` still needs Linux and agent-boundary validation before scoring.

Freeze the final four before testing. Allow one autonomous run per case, capped at **30 minutes and 60 tool calls**, with self-correction allowed inside that budget. Verify the resulting patch against the reproduction and relevant existing tests, and inspect whether it actually meets the requirement. A valid alternative to the human patch can pass.

Log hints or edits you supply as assistance. Keep timeouts and failures in the results; do not replace selected cases because Glimmer struggles. An infrastructure retry may be reported separately, with both attempts retained.

## 5. Implement the four daily workflows

Use the source posts in the attachment to collect roughly 12 workflow candidates, again within a two-hour discovery budget. Save source URL, author/date, frequency, inputs, reported difficulties and how the need maps to your life. These posts are inspiration, not independent reliability measurements.

Starting sources: [Sajal Sharma](https://sajalsharma.com/posts/openclaw-experiments/), [Gordon Qian](https://guochengqian.github.io/blog/hermes-agent/) and [Kenny Trinh](https://kennytrinh.com/blog/from-chatbot-to-co-worker).

Use these four as the default final selection:

| Workflow | Minimal implementation | Checkable success conditions |
| --- | --- | --- |
| W01: Morning briefing | Read current `calendar.csv`, `tasks.md`, selected reading links and `memory.md`; save a dated briefing | Correct commitments/times, sensible priorities, accurate carry-over tasks and source links |
| W02: Article capture | Accept a URL, retrieve public text, save a short source-linked note and update a reading index | Working link, faithful summary, correct saved location and no duplicate entry for the same article |
| W03: Blog assistance | Turn your rough notes into a Markdown draft, then apply your editorial comments | Preserved factual claims and meaning, traceable sources, requested edits and retained voice |
| W04: Evening handover | Read your activity/task updates; save a dated handover and update `memory.md` | Completed and unfinished work distinguished, decisions preserved, tomorrow's starting point accurate |

Use exported or manually copied calendar data rather than building a live calendar integration. Include timezone and last-updated time in the input. Refresh it before each briefing and disclose the manual work. Use public-page retrieval that does not require external model processing; if retrieval fails, record it, then label any attempt using supplied article text as an adaptation.

Every daily session should receive the current date, `Europe/London` timezone, input paths and explicit instructions to read persistent memory. Start a fresh session for each scheduled run so next-day continuity depends on saved information. Keep memory concise and preserve its daily revisions for review.

Schedule W01 at **08:00** and W04 at **20:00 Europe/London**, starting no later than day three. Pin both jobs to the local model. Use dated output filenames to avoid duplicate notes. Cap daily runs at **15 minutes**. Test file delivery and scheduler timezone once before observation.

Observe both jobs for at least three consecutive days. Capture expected time, actual start/end, output path, input freshness, status and any intervention. Missed or manually triggered jobs remain visible. Ordinary changes—an appointment moved, a task postponed, a repeated article or revised writing instruction—provide useful evidence as they occur.

## 6. Record enough evidence to support the article

Keep evaluation manual and based on the success criteria written before each run. Do not add an LLM judge.

For each curated run, save: case/run ID, exact prompt, input snapshot, settings reference, start/end time, transcript, output or patch, verification result, human help and failure explanation. Native token/tool counts are useful when available; leave unavailable values blank.

Use four outcome labels: **autonomous success**, **assisted success**, **failed**, **unavailable**. Separately tag the cause where known: model work, tool/integration, scheduler/runtime or input/setup. This prevents a calendar-export problem from becoming a claim about model reasoning.

The usage diary should take under a minute per request: request, attempted with Glimmer, outcome, time spent helping, and why you took over or used another tool. Include unavailable tools and skipped requests.

Report:

- Coding results as a count out of four, with verification evidence.
- Daily workflow results with both output quality and human effort.
- Scheduled completions versus all expected executions, distinguishing timely, late, failed and missed runs.
- Diary autonomous successes divided by **all recorded assistant requests**, alongside the attempted-only rate. Keep assisted outcomes separate.
- Setup/maintenance hours and measured run times. Add GPU utilization/power snapshots only if easy; they are not whole-system electricity measurements.

Four selected workflows show capability on those examples. Any “most of my daily tasks” statement should be limited to the requests recorded during this observation week.

## 7. Seven-day delivery schedule

| Day | Work | End-of-day checkpoint |
| --- | --- | --- |
| 1 — setup complete | Muse Glimmer and Hermes are already installed and working; record the actual settings | Move directly to coding-case preparation |
| 2 — about 6 hours; active phase | Configure the shared repository remote; collect candidates; reproduce one case end to end, then select/prepare all four; prepare the workflow inputs/prompts | Cases frozen; failure/fix checks saved; morning/evening schedules ready |
| 3 — about 4 hours | Start scheduled observation; exercise article capture and blog drafting/revision; add a thin wrapper only if needed | Two daily jobs active; all four workflows attempted |
| 4 — about 4 hours | Run and verify the four coding cases; continue daily usage and scheduled observation | All coding attempts have transcripts, patches and verdicts |
| 5 — about 3 hours | Continue real use; inspect next-day continuity and record failures/interventions | At least three days and six scheduled opportunities observed |
| 6 — about 3 hours | Continue observation if useful; review evidence, redact examples and generate summary tables | Results complete, with causes and adaptations explained |
| 7 — about 3 hours | Assemble the blog's setup/method/results/experience outline and selected examples | Reproducible project notes and a publishable evidence bundle |

Allow roughly four hours of contingency within the 32-hour ceiling. Protect the three-day observation window by cutting optional work first.

## 8. Rules that protect the one-week deadline

- No dashboard, custom agent framework, vector database, fine-tuning, multi-agent system, phone interface or custom OAuth integrations this week.
- No model-comparison tournament or large benchmark suite. The human-fixed coding version is the reference for verification.
- Preserve the working runtime. Only troubleshoot a blocker that prevents preparing or running the selected experiments; record any change to the frozen configuration.
- Use file-based substitutes for unavailable integrations and disclose their limitations. Record manual refresh/setup time.
- Freeze settings before scored runs. If a material change becomes necessary, label affected runs and preserve the earlier evidence.
- Keep unsuccessful experiments. If preparation leaves fewer reproducible cases, report the shortfall rather than inventing results or extending the build indefinitely.

The next milestone is **repeat the four pinned cases on the 5090 and verify the agent boundary**. The cases are synchronized through the shared repository; Linux verification and scored Glimmer results must be recorded separately from the completed local preparation.
