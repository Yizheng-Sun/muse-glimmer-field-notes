# Project implementation and repository structure

Updated: **11 October 2026**. Preparation baseline: commit `3c77a5e` in the private [muse-glimmer-field-notes repository](https://github.com/Yizheng-Sun/muse-glimmer-field-notes). The automated evaluation framework was added on 10 October.

The project provides pinned preparation and automated evaluation for **four coding experiments**. Muse Glimmer and Hermes are installed, and all four cases have been verified on this Mac and during 5090 batch preparation. The [completed 48-run matrix](results/evaluation-report-2026-10-11.md) recorded **16 PASS and 32 FAIL**: C01 0/12, C02 5/12, C03 4/12 and C04 7/12. Earlier individual results remain **C01 FAIL and C02 PASS**; C01's assisted continuation also failed acceptance.

## What has been implemented

### One shared project repository

The authoring computer and the 5090 use clones of the same GitHub repository. Case definitions and selected evidence move between them through commits, pushes and pulls. The 5090 checkout completed preparation and all 48 evaluation runs. Upstream source snapshots, caches and raw logs are generated inside each clone's ignored `.runs/` directory; they are not a second manually maintained project.

The working model installation, Hermes configuration, credentials and model weights remain outside this preparation package. No runtime configuration was changed while preparing these cases.

### Candidate discovery and selection

Five Python repositories were screened: Click, Packaging, Werkzeug, attrs and Rich. The [candidate ledger](results/candidates.csv) contains **14 inspected PR candidates**, with source links, report/merge dates, exact revisions, decisions and provenance notes.

The main merge window was 25 September–9 October 2026. Twelve candidates fall within it; two additional Click candidates use the permitted 9 September–9 October expansion. C02 was selected from that expanded window to add text-processing behavior while keeping the final cases in two source repositories. Packaging's selected PRs were reported in August but merged in October; their actual report dates are retained.

[Selection notes](results/coding-selection.md) explain reserves, exclusions and authorship caveats. Reference patches are described as **upstream merged fixes**: their authorship has not been independently established as exclusively human.

### Four prepared coding cases

| Case | Source PR | Requirement and check coverage | Local result |
| --- | --- | --- | --- |
| C01 | [Click #3884](https://github.com/pallets/click/pull/3884) | Readable environment-variable hints for strings, lists and tuples; empty configurations, automatic prefixes, hidden hints and normal value resolution | Base: 21 assertion failures; fixed passes all 6 test methods |
| C02 | [Click #3865](https://github.com/pallets/click/pull/3865) | Short help preserves abbreviations; sentence boundaries, paragraph/whitespace handling, word-aware width limits and explicit-summary controls | Base: 8 assertion failures; fixed passes all 5 methods |
| C03 | [Packaging #1379](https://github.com/pypa/packaging/pull/1379) | Requirement URLs reject LF, CR and CRLF; valid URLs, fragments, horizontal whitespace, markers and ordinary requirements still work | Base: 6 assertion failures; fixed passes all 3 methods |
| C04 | [Packaging #1382](https://github.com/pypa/packaging/pull/1382) | License-file validation rejects drive-relative paths in lazy and eager validation; preserves valid relative paths and existing invalid-path rejection | Base: 5 assertion failures; fixed passes all 4 methods |

Failure counts include parameterized scenarios within test methods as well as whole-method failures, so they can exceed method counts. Each upstream fix changes one production file. These are bounded calibration cases for the blog, rather than a representative benchmark of all coding tasks.

Every case directory contains four files:

| File | Implemented purpose |
| --- | --- |
| `case.json` | Case ID/status, upstream URL, full starting/fixed commit hashes, report/merge dates, commands, adaptations, provenance and validation status |
| `prompt.md` | A sanitized request describing reproduction, expected behavior and preservation requirements, without the reference patch or identifying solution links |
| `check.py` | A standalone reviewer acceptance check using standard-library `unittest` and the selected source's public API |
| `review.md` | Selection rationale, reference implementation notes, acceptable alternatives, evidence links, limits and the future scored-attempt record |

The identical checker is run against both pinned revisions. Import guards confirm that the requested snapshot supplies the package, rather than an installed copy. Checks examine observable behavior, not patch text or implementation shape, so valid alternative fixes can pass.

All four cases retain `prepared_locally` metadata for the original preparation provenance. C01/C02 scored-attempt metadata records their earlier individual results. The completed matrix has 12 per-run records for every case, including C03/C04, plus frozen configuration, inputs and environment information under `.runs/evaluation/20261010T204407.924852Z/`. [Recorded coding results](results/coding-results.md) distinguish the matrix, earlier individual attempts and assisted continuation.

### One preparation helper

[scripts/prepare_case.py](scripts/prepare_case.py) uses **Python 3.12+ and Git**, with no third-party Python dependencies. It implements:

1. Reading a case definition and validating its repository URL, ID and full commit hashes.
2. Fetching missing pinned commits into a reusable bare Git cache under `.runs/cache/`.
3. Building fresh `base/` and `fixed/` source snapshots using Git archives, without `.git` history.
4. Optionally running both checks with isolated Python imports and bytecode writing disabled, with a 120-second timeout per check.
5. Saving timestamped raw logs and a JSON report containing commits, environment, file hashes, exit codes and timings.
6. Optionally exporting an `agent/` folder containing only the sanitized prompt and a separate broken-source copy. Existing exports are preserved; overwriting them is refused.

`--verify` requires **base exit 1 and fixed exit 0**. Check exit 2 identifies argument/import/source setup errors. The helper exits 2 if preparation or its expected before/after result fails.

The helper prepares files and verifies cases. It does not launch Hermes, call a model, run scored attempts, install test dependencies or enforce filesystem/network isolation.

### Recorded local evidence

[evidence/preparation](evidence/preparation/README.md) contains concise JSON evidence for all four cases. The actual verification environment was **CPython 3.12.14, macOS 26.7.1 arm64 and Git 2.50.1**. No third-party dependencies were needed for the reviewer checks.

Evidence includes exact upstream commits, timestamps, commands, actual failure excerpts/passing summaries, environment details and SHA-256 hashes for the check, prompt, helper, metadata and raw evidence. Verification occurred while the new preparation files were uncommitted; that fact is recorded, and hashes identify the artifacts subsequently committed in `3c77a5e`. The recorded final preparation timings use a warm source cache and are not first-download benchmarks.

The exported local inputs were inspected to match the broken source and sanitized prompt, without Git history or generated bytecode. An independent read-only audit confirmed the four before/after results and artifact consistency. The completed 5090 batch also verified each failing base and passing reference, installed pytest, and ran focused upstream tests. Full upstream suites have not been run.

### Automated budget and reasoning evaluation

[scripts/evaluate_coding.py](scripts/evaluate_coding.py) wraps the installed Hermes CLI; [scripts/eval_metrics.py](scripts/eval_metrics.py) extracts native usage and writes JSONL, CSV and Markdown reports. Both use the standard library. [config/evaluation.json](config/evaluation.json) specifies cases, reasoning strengths, budgets, repeats, endpoint, context and sampling. The default is 48 sequential runs: four cases, three budgets and four reasoning levels, with one repeat.

[scripts/run_evaluation.sh](scripts/run_evaluation.sh) launches that matrix in the background with one command. It discovers Python 3.12+, validates the matrix, reads the server key privately when needed, recreates `.runs/`, preserves timestamped launch logs and guards against duplicate launcher starts. Existing runner options, including `--resume`, pass through; inspection commands stay in the foreground.

Each attempt uses a fresh pinned source, virtual environment, synthetic one-commit Git baseline, Hermes home and session database. Dependencies are downloaded once per batch and installed offline into each source. Model iterations and elapsed time are capped; the unchanged acceptance checker grades the final or partial source. Functional verdicts, process stops, focused upstream results and missing metrics remain separate.

The requested llama.cpp reasoning strength is supplied through a named Hermes provider's `extra_body.chat_template_kwargs.reasoning_strength`. Main and auxiliary token counters are recorded separately, including cache buckets. Compression child sessions use additive database usage and occurrence identifiers for accounting. Completed attempts are preserved on resume; abandoned directories are archived before infrastructure retries.

Local tests cover matrix orchestration, timeout cleanup, acceptance versus process status, fresh sources, interruption, resume, reporting, native token accounting and compression lineage. Launcher checks cover detached startup, a hidden credential prompt, no-auth input, frozen resume credentials, stale Python fallback, log preservation and duplicate prevention. The 5090 completed the full Hermes/Glimmer matrix with no missing results or recorded metrics/evidence errors. The backend is local and does not enforce filesystem or network isolation; requested server reasoning strength remains independently unverified. See [the evaluation guide](docs/EVALUATION.md) for launch commands and limits.

### Claude Haiku API comparison

[config/evaluation-haiku.json](config/evaluation-haiku.json) runs `claude-haiku-5-5` through native Anthropic requests with the same 48 jobs, budgets, order, case inputs, and acceptance checks. Original 5090 input fingerprints are checked before inference. [scripts/run_haiku_evaluation.sh](scripts/run_haiku_evaluation.sh) starts it on this Mac with a privately supplied API key, separate launch logs, and optional idle-sleep prevention. Batches are saved under `.runs/evaluation-haiku/`. No GPU is required.

[scripts/hermes_haiku.py](scripts/hermes_haiku.py) supplies process-local compatibility for adaptive effort, prior thinking-block replay, and loading installed Hermes dependencies with a fresh evaluation home. The pinned API SDK is stored inside each ignored batch. Preflight validates all four request settings locally and checks model access without inference; runtime hashes and provenance are retained. Existing installed Hermes files are unchanged. The same usage and timing reports apply, with unavailable reasoning counters left unknown. All 69 available tests passed; one optional evidence test was skipped. Actual Mac case setup and isolated Hermes/SDK checks also passed. No paid Haiku run was performed during implementation. [The Haiku guide](docs/HAIKU_EVALUATION.md) describes commands and the Mac/runtime differences that limit the comparison.

### Automated daily-task evaluation

[cases/daily](cases/daily/README.md) contains **15 researched task types, each with normal, update, and problem variants: 45 synthetic fixtures**. [The research ledger](results/daily-task-research-2026-10-11.md) retains firsthand source links and limitations. [scripts/daily_cases.py](scripts/daily_cases.py) defines deterministic inputs and prompts; [scripts/prepare_daily.py](scripts/prepare_daily.py) regenerates or verifies the tracked JSON definitions.

[scripts/evaluate_daily.py](scripts/evaluate_daily.py) uses the installed Hermes CLI and shares backend configuration, process supervision, session metrics, credentials, and reporting helpers with the coding runner. [scripts/run_daily_evaluation.sh](scripts/run_daily_evaluation.sh) supplies the same private key prompt and detached launcher. The default [daily configuration](config/evaluation-daily.json) selects D02, D06, D09, and D12 with three variants and two repeats: **24 attempts**, capped at 30 iterations and 900 seconds each. All 15 tasks can be selected for 90 attempts.

Each attempt receives fresh input files. Article capture, editorial revision, and handover use two fresh Hermes sessions sharing only task files. Editorial feedback arrives before the second session; the handover's raw first-day log is removed. Declared first-phase artifacts are snapshotted for independent grading. Article capture and reading selection use reproducible loopback HTTP pages with recorded retrievals, including a deliberate unavailable page.

[scripts/daily_checks.py](scripts/daily_checks.py) grades structured facts, source references, totals, saved files, input preservation, and actual filesystem operations without executing agent output or calling an LLM judge. Meal plans and itineraries accept alternative feasible solutions. Frozen case/checker/configuration fingerprints protect the recorded specification; resume preserves completed results and archives unfinished attempts. Per-attempt checks and session evidence feed JSONL, CSV, and Markdown reports.

**All 25 daily harness tests pass**, including reference and incorrect outputs for all 45 fixtures, subprocess supervision, loopback retrieval, fresh sessions, delayed feedback, timeout recovery, tamper detection, and resume. The existing coding/Haiku regression suite also passed, with one optional evidence test skipped. These checks use a fake Hermes process and do not measure model capability. No daily-task model inference has been performed during implementation. Prose quality, personal-material trials, live integrations, and scheduled observation remain separate work. See [the daily guide](docs/DAILY_EVALUATION.md) for commands and scope.

## Current repository structure

The tracked project files are arranged as follows. The case directories share the four-file layout shown for C01.

```text
muse-glimmer-field-notes/
├── .gitignore
├── README.md                          # Entry point and shared GitHub workflow
├── PLAN.md                            # One-week experiment plan
├── IMPLEMENTATION.md                  # This implementation/structure overview
├── cases/
│   ├── daily/
│   │   ├── README.md                  # Task catalog and evaluation boundary
│   │   └── D01.json ... D15.json      # Synthetic fixtures and acceptance checks
│   └── coding/
│       ├── README.md                  # Comparison, commands and readiness checks
│       ├── _template/
│       │   ├── case.json
│       │   ├── prompt.md
│       │   └── review.md
│       ├── C01/
│       │   ├── case.json
│       │   ├── prompt.md
│       │   ├── check.py
│       │   └── review.md
│       ├── C02/                       # Same four files
│       ├── C03/                       # Same four files
│       └── C04/                       # Same four files
├── scripts/
│   ├── prepare_case.py                # Pinned source preparation
│   ├── evaluate_coding.py             # Sequential Hermes matrix runner
│   ├── run_evaluation.sh              # One-command background launcher
│   ├── run_daily_evaluation.sh        # Daily-task background launcher
│   ├── evaluate_daily.py             # Daily-task orchestration and evidence
│   ├── daily_checks.py               # Independent artifact acceptance checks
│   ├── daily_cases.py                # Deterministic fixture definitions
│   ├── prepare_daily.py              # Fixture generation/consistency check
│   ├── run_haiku_evaluation.sh        # Mac/API matrix launcher
│   ├── hermes_haiku.py               # Process-local native Haiku compatibility
│   └── eval_metrics.py                # Usage extraction and reports
├── config/
│   ├── evaluation.json                # Matrix and local endpoint settings
│   ├── evaluation-daily.json          # Daily-task selection and budgets
│   └── evaluation-haiku.json          # API matrix and original input fingerprints
├── docs/
│   ├── EVALUATION.md                  # Setup, overnight launch and metrics
│   ├── DAILY_EVALUATION.md            # Daily fixtures, execution and limitations
│   └── HAIKU_EVALUATION.md            # Mac/API comparison, metrics and resume
├── tests/
│   ├── test_evaluate_coding.py         # Fake-Hermes orchestration checks
│   ├── test_daily_evaluation.py       # Daily artifacts, sessions and runner checks
│   ├── daily_test_support.py          # Reviewer-only reference artifacts for tests
│   ├── test_run_evaluation.py          # Bash launch, auth, logs and duplicate checks
│   ├── test_run_haiku_evaluation.py    # API launcher without inference calls
│   ├── test_haiku_evaluation.py        # Native configuration and frozen input checks
│   ├── test_hermes_haiku.py           # Native request compatibility and replay
│   └── test_eval_metrics.py            # Native exports, accounting and reports
├── results/
│   ├── candidates.csv                 # 14 inspected candidates and decisions
│   ├── coding-selection.md            # Discovery scope, exclusions and limits
│   ├── coding-results.md              # Current matrix and earlier individual results
│   └── evaluation-report-2026-10-11.md # Full 48-run outcomes and metrics
└── evidence/
    ├── coding/C01/, coding/C02/        # Selected session analyses and results
    └── preparation/
        ├── README.md                  # Local verification summary
        ├── C01.json
        ├── C02.json
        ├── C03.json
        └── C04.json
```

Generated data lives under the ignored `.runs/` directory and is excluded from Git. The completed 5090 batch artifacts have also been made available in this authoring checkout. The original preparation layout is:

```text
.runs/
├── cache/
│   ├── pallets-click.git/             # Cached upstream commits; reviewer only
│   └── pypa-packaging.git/
├── discovery/                         # Raw research, trial snapshots and logs
├── setup/                             # Local repository-setup evidence
└── coding/
    ├── C01/
    │   ├── base/                      # Recreated broken reference source
    │   ├── fixed/                     # Recreated upstream-fixed reference
    │   ├── agent/
    │   │   ├── prompt.md              # Sanitized agent input
    │   │   └── source/                # Separate broken-source working copy
    │   └── logs/<UTC timestamp>/
    │       ├── base.log
    │       ├── fixed.log
    │       └── verification.json
    ├── C02/                           # Same generated layout
    ├── C03/
    └── C04/
```

`.gitignore` also excludes machine-specific `.codex/` state, environment files, virtual environments, bytecode/test caches and the planned private `workspace/daily/` data. Selected evidence is tracked separately so large source trees and raw logs do not enlarge the shared repository.

Automated Glimmer coding batches are generated under ignored `.runs/evaluation/<timestamp>/`; Haiku batches use `.runs/evaluation-haiku/<timestamp>/`, and daily-task batches use `.runs/daily-evaluation/<timestamp>/`. Their frozen inputs, individual run artifacts and aggregate reports are described in the evaluation guides. Coding batches also retain dependency wheels. Earlier manual `.runs/coding/` attempts are preserved.

## How to use the implemented preparation

From the repository root, choose an existing Python 3.12+ interpreter. `python3` below must meet that requirement; substitute `python3.12` if necessary.

```sh
CASE_PYTHON=python3
"$CASE_PYTHON" scripts/prepare_case.py all --verify
```

Use `C01`, `C02`, `C03` or `C04` instead of `all` for one case. After verification, export fresh inputs:

```sh
"$CASE_PYTHON" scripts/prepare_case.py all --export
```

Repeating preparation rebuilds the reference snapshots and retains older logs. Export refuses to overwrite an existing agent copy. Preserve any attempted patch and transcript before preparing a later attempt in a new folder.

After a future agent edit, the reviewer can check that working source:

```sh
"$CASE_PYTHON" -B -I cases/coding/C01/check.py --source .runs/coding/C01/agent/source
```

The [coding README](cases/coding/README.md) contains the complete clone/pull instructions, optional upstream test-runner setup and 5090 readiness checklist.

## What remains to be implemented or verified

| Remaining work | Current status |
| --- | --- |
| 5090/Linux preparation | Completed for all four cases during batch setup; preparation logs and environment record are available |
| Agent isolation | Owner selected the local backend; filesystem/network isolation is not enforced and is recorded as a limitation |
| Upstream test runner | Installed and used for all 48 attempts; focused checks exited successfully in 42 runs, while six C02 runs retained failures; full suites were not run |
| Runtime record | `config/run-settings.md` is planned but does not exist yet; record and freeze the existing working settings |
| Scored coding attempts | Completed: 48 matrix runs across C01–C04, with 16 PASS and 32 FAIL; earlier individual attempts are preserved |
| Haiku API comparison | Implemented for the same 48 jobs and pinned inputs; paid evaluation remains to be launched on the Mac |
| Daily workflows | Automated 15-task/45-fixture synthetic suite implemented and verified; daily model runs, personal-material W01–W04 trials, and full morning briefing remain outstanding |
| Scheduled observation and usage diary | Scheduling, observation logs and `runs.csv`, `schedule.csv`, `diary.csv` are planned; no such results are recorded yet |
| Final blog results | `results/summary.md` and the final evidence narrative remain to be produced after experiments |
| Evaluation wrappers | Implemented and exercised across the full 5090 batch; independent verification of server reasoning behavior remains outstanding |

Local preparation establishes case reproducibility. Local-backend runs retain the stated isolation limitation; native exports and acceptance checks support the recorded outcomes without establishing broad model performance.
