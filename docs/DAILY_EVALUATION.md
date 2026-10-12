# Automated daily-task evaluation

The runner implements the 15 tasks in [the research ledger](../results/daily-task-research-2026-10-11.md), each with `normal`, `update`, and `problem` variants: **45 deterministic fixtures**. Inputs are fictional and inspired by the linked firsthand reports. The suite tests bounded tasks with supplied files and reproducible local web pages. It has not yet been evaluated with Muse Glimmer on the 5090.

The default batch selects **D02 article capture, D06 invitation changes, D09 evening handover, and D12 expense reports**. Three variants and two repeats produce **24 sequential attempts**, each with up to 30 tool-calling iterations and 900 seconds. The maximum configured agent allowance is six hours, plus preparation, session exports, and checks. `--all` selects 90 attempts with a maximum allowance of 22.5 hours. These are upper bounds, not runtime estimates.

## Run on the 5090

Use the existing Hermes installation and working Muse Glimmer server. The runner requires Python 3.12+ on Linux or macOS; its Python code uses only the standard library. It does not download models, install Python packages, fetch source repositories, or change the installed Hermes configuration.

After transferring the repository changes to the 5090 checkout, preview the batch:

```bash
bash scripts/run_daily_evaluation.sh --dry-run
```

Start the default batch:

```bash
bash scripts/run_daily_evaluation.sh
```

The launcher asks privately for `GLIMMER_API_KEY` if it is not exported. Press Enter only if your local server has authentication disabled. Inference starts in the background. Follow its log:

```bash
tail -f .runs/daily-evaluation-launch.log
```

[config/evaluation-daily.json](../config/evaluation-daily.json) defines the endpoint (`http://127.0.0.1:8081/v1`), model alias (`muse-glimmer`), context, sampling, requested reasoning, budgets, and repeats. Adjust the endpoint and alias to match your existing server. Preflight checks Hermes CLI support and the model listing before starting task attempts. Requested reasoning is passed through the same custom-provider setting as the coding evaluation; server behavior is not independently verified.

For one attempt, or the full set:

```bash
bash scripts/run_daily_evaluation.sh --cases D12 --variants normal --repeats 1
bash scripts/run_daily_evaluation.sh --all
```

Options `--cases`, `--variants`, `--efforts`, `--budgets`, and `--repeats` override the selection. `--budgets` selects budget names already present in the config. `--cases` and `--all` are mutually exclusive. Additional effort levels or budgets multiply the number of attempts.

Freeze a batch for inspection without Hermes, credentials, a running server, or model calls:

```bash
bash scripts/run_daily_evaluation.sh --prepare-only
```

The command prints its batch path under `.runs/daily-evaluation/`. Inspect that batch's `config.json`, `jobs.json`, and `inputs/` before using its printed path to run it:

```bash
bash scripts/run_daily_evaluation.sh --resume .runs/daily-evaluation/<printed-timestamp>
```

For foreground execution, use your Python 3.12+ interpreter directly:

```bash
python3.12 scripts/evaluate_daily.py --dry-run
python3.12 scripts/evaluate_daily.py --cases D12 --variants normal --repeats 1
```

For an authenticated server, export the configured key variable before foreground inference; the Bash launcher supplies the private credential prompt. An unauthenticated local server uses a placeholder key. On a machine with a differently named interpreter, set `CASE_PYTHON` to its path for the launcher.

## What is automatically checked

Each prompt documents a JSON output contract and also asks for readable Markdown. The independent checker reads saved artifacts; it never executes agent output and uses no LLM judge. A claimed completion in a transcript does not count as a saved result.

| Case | Task | Objective checks and variant changes |
| --- | --- | --- |
| D01 | Daily schedule | Overlap detection, union of occupied time, workload capacity; moved appointment or unknown task duration |
| D02 | Article capture | Recorded HTTP retrieval, source-linked notes, numerical facts, saved index and deduplication across two sessions; revised page or HTTP 404 |
| D03 | Recall quiz | Factual answer key and note coverage, separate question/answer files; changed fact or unanswerable note |
| D04 | Reading shortlist | Recorded retrieval, topic/date selection and source URLs; new relevant article or missing publication date |
| D05 | Blog draft and revision | Draft saved before feedback, factual counts, required title/section and removal of explicit unsupported text; updated result or superseded scratch figure |
| D06 | Invitation changes | Latest event version, cancellation, deduplication and timezone-aware timestamps; later update or unknown start time |
| D07 | Training review | Topic grouping, timestamp references and factual intervals; corrected interval or inaudible content |
| D08 | Interview preparation | Requirement-to-CV evidence, responsibility wording and missing experience; changed responsibility or distracting project |
| D09 | Evening handover | Correct first-day snapshot and retained state in a fresh second session with the raw log removed; owner change or superseded task/decision |
| D10 | School messages | Dates, actions, cancellations and family-calendar conflicts; moved venue or unconfirmed event |
| D11 | Meals and shopping | Any feasible five-day plan, portions, earlier-dinner leftovers, cooking limits, pantry subtraction, prices and budget; guest or tighter cooking limit |
| D12 | Expenses | Receipt deduplication, report period, categories, refunds and separate currency totals; refund or unreadable amount |
| D13 | Folder organization | Actual file moves, collision avoidance, byte hashes, correct category folders and complete manifest; changed content category or unlabelled file |
| D14 | Trip itinerary | Any feasible chronological route, travel time, opening hours, activity duration, fixed reservation and hotel return; closed attraction or narrower time window |
| D15 | Meeting preparation | Latest relevant decision, open commitments and evidence IDs; changed owner or similarly named unrelated project |

Most tasks compare structured facts, ignoring record order and accepting equivalent timezone-aware instants. Extra JSON fields, duplicate JSON keys, missing facts, and invented values fail. Meals, itineraries, and file organization use constraint checks so valid alternative solutions can pass. Read-only fixture inputs must remain unchanged.

`update` is a separately initialized variant with changed inputs, not an extra live event delivered during every task. D02, D05, and D09 explicitly run two phases. Each phase has a fresh Hermes home and session database; only task files persist. D05's editor feedback is introduced before the second phase. D09's first-day raw log is removed before the second phase, and the first output is snapshotted before the second session can change it. Turn limits are divided across phases; the remaining task time is divided among remaining phases. A timeout stops further phases, and missing phases cannot pass the whole task.

D02 and D04 receive temporary loopback HTTP pages served from an in-memory route map. The server never serves the repository or reviewer files. Retrieval is recorded, including D02's deliberate 404. This tests retrieval and source handling with fixed content; it does not measure open-web discovery or the ability to bypass paywalls.

## Results and resume

Each batch contains:

```text
.runs/daily-evaluation/<timestamp>/
├── config.json, jobs.json, manifest.json, environment.json
├── inputs/D02.json, ...             # Frozen reviewer-side case definitions
├── tools/daily_checks.py            # Frozen independent checker
├── runs/<run-id>/
│   ├── workspace/                  # Agent inputs and saved final outputs
│   ├── phases/phase-01/             # Prompt, command, transcript, export, metrics
│   ├── phases/phase-02/             # Present for two-phase tasks
│   ├── snapshots/                  # Declared artifacts captured between phases
│   ├── web-requests.json            # Reviewer-side retrieval evidence
│   ├── check.json, check.log
│   └── result.json
├── incomplete/                     # Archived unfinished attempts, if any
├── results.jsonl, results.csv
└── summary.md
```

Reports update after each attempt. `check.json` lists each acceptance check and its failure reason. JSONL retains nested evidence; CSV includes verdicts, process status, elapsed agent time, and available usage counters. Main session usage is summed across fresh phases, including compression children, with auxiliary usage recorded separately. Missing counters stay unknown. `elapsed_seconds` sums agent subprocess time; `total_seconds` also includes setup, exports, and checking.

Artifact verdict and process status are separate: a budget stop can still pass when all required artifacts already exist and every required phase was attempted. `SETUP_ERROR`, `CHECK_ERROR`, `EVIDENCE_ERROR`, and `UNKNOWN` retain infrastructure/evidence problems rather than presenting them as model success. The summary includes all recorded attempts in its denominator, including archived interruptions.

Resume uses the frozen matrix and cannot accept selection overrides. It preserves every completed `result.json`, including failures; it archives an unfinished directory before a fresh retry. Case, checker, configuration, job-list, and runner dependency fingerprints are verified. Changing frozen data or relevant scripts requires a new batch. To intentionally repeat a completed failure, start another batch rather than editing its result.

## Validate or extend the cases

The tracked JSON files are generated from [scripts/daily_cases.py](../scripts/daily_cases.py). Change that source, regenerate, inspect the diff, and validate:

```bash
python3.12 scripts/prepare_daily.py
python3.12 scripts/prepare_daily.py --check
python3.12 -m unittest discover -s tests -p 'test_daily_evaluation.py' -v
```

The 25 daily tests exercise reference and incorrect artifacts for all 45 fixtures, valid alternative plans, corrupt or missing files, input changes, real subprocess orchestration with a fake Hermes CLI, loopback retrieval, fresh sessions, timeout handling, evidence tampering, resume, and launcher selection. They make no model calls. HTTP tests need permission to bind a temporary loopback port. The existing coding/Haiku regression suite was also checked during implementation.

To recheck one saved attempt without making model calls, use its frozen case, workspace, recorded fixture URL, snapshots, and retrieval log. For example, replace both placeholders with values from the attempt's `result.json`:

```bash
python3.12 -B -I .runs/daily-evaluation/<batch>/tools/daily_checks.py \
  --case .runs/daily-evaluation/<batch>/inputs/D02.json --variant normal \
  --workspace .runs/daily-evaluation/<batch>/runs/<run-id>/workspace \
  --base-url http://127.0.0.1:<recorded-port> \
  --snapshots .runs/daily-evaluation/<batch>/runs/<run-id>/snapshots \
  --requests .runs/daily-evaluation/<batch>/runs/<run-id>/web-requests.json
```

The old HTTP server does not need to be running for rechecking; the URL identifies saved source references, and the retrieval log records what was fetched. Checker exits are 0 for pass, 1 for unmet requirements, and 2 for configuration errors.

## How to use the evidence in a blog

An automated PASS establishes the documented structured facts and file operations. Markdown checks cover existence, length, and selected explicit strings; they do **not** establish useful prose, faithful summaries in every sentence, good quiz questions, interview quality, or retained writing voice. Read the final human-facing outputs before describing a task as useful. Keep that human assessment alongside the automatic result.

These are small calibration fixtures, with no live mail/calendar integration, receipt OCR, speech recognition, booking, nutrition assessment, or actual scheduled multi-day observation. They support concrete examples of successes and failure modes, not a representative score for all daily tasks or a claim about time saved. The installed local backend does not enforce filesystem or network isolation. Reviewer data stays outside the task workspace, and prompts prohibit reading it, but that boundary is not enforced. Audit transcripts before claiming blind evaluation. Real personal-material trials and the original scheduled observation remain separate work.
