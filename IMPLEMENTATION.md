# Project implementation and repository structure

Updated: **10 October 2026**. Preparation baseline: commit `3c77a5e` in the private [muse-glimmer-field-notes repository](https://github.com/Yizheng-Sun/muse-glimmer-field-notes). The automated evaluation framework was added on 10 October.

The project provides pinned preparation and automated evaluation for **four coding experiments**. Muse Glimmer and Hermes are already installed, as confirmed by the owner. All four cases have been verified on this Mac. Original autonomous results on the 5090 are **C01 FAIL and C02 PASS**; C01's assisted continuation also failed acceptance. The new budget/reasoning matrix has not been run on the GPU.

## What has been implemented

### One shared project repository

The project is designed for the authoring computer and the 5090 to use clones of the same GitHub repository. Case definitions and selected evidence move between them through commits, pushes and pulls. The 5090 checkout and preparation remain to be verified. Upstream source snapshots, caches and raw logs are generated inside each clone's ignored `.runs/` directory; they are not a second manually maintained project.

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

All four cases remain marked `prepared_locally` for preparation provenance. C01/C02 scored-attempt metadata now records their original results; C03/C04 remain pending. Complete remote preparation reports and frozen runtime records are still incomplete. [Recorded coding results](results/coding-results.md) distinguish autonomous and assisted attempts.

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

The exported local inputs were inspected to match the broken source and sanitized prompt, without Git history or generated bytecode. An independent read-only audit confirmed the four before/after results and artifact consistency. Full upstream test suites and the optional pytest installation have not been run.

### Automated budget and reasoning evaluation

[scripts/evaluate_coding.py](scripts/evaluate_coding.py) wraps the installed Hermes CLI; [scripts/eval_metrics.py](scripts/eval_metrics.py) extracts native usage and writes JSONL, CSV and Markdown reports. Both use the standard library. [config/evaluation.json](config/evaluation.json) specifies cases, reasoning strengths, budgets, repeats, endpoint, context and sampling. The default is 48 sequential runs: four cases, three budgets and four reasoning levels, with one repeat.

Each attempt uses a fresh pinned source, virtual environment, synthetic one-commit Git baseline, Hermes home and session database. Dependencies are downloaded once per batch and installed offline into each source. Model iterations and elapsed time are capped; the unchanged acceptance checker grades the final or partial source. Functional verdicts, process stops, focused upstream results and missing metrics remain separate.

The requested llama.cpp reasoning strength is supplied through a named Hermes provider's `extra_body.chat_template_kwargs.reasoning_strength`. Main and auxiliary token counters are recorded separately, including cache buckets. Compression child sessions use additive database usage and occurrence identifiers for accounting. Completed attempts are preserved on resume; abandoned directories are archived before infrastructure retries.

Local tests cover matrix orchestration, timeout cleanup, acceptance versus process status, fresh sources, interruption, resume, reporting, native token accounting and compression lineage. Real offline dependency installation, editable installation and focused test collection have also passed for Click and Packaging. Real Hermes/Glimmer matrix execution remains to be verified on the 5090. The backend is local and does not enforce filesystem or network isolation. See [the evaluation guide](docs/EVALUATION.md) for launch commands and limits.

## Current repository structure

The tracked project files are arranged as follows. The case directories share the four-file layout shown for C01.

```text
muse-glimmer-field-notes/
├── .gitignore
├── README.md                          # Entry point and shared GitHub workflow
├── PLAN.md                            # One-week experiment plan
├── IMPLEMENTATION.md                  # This implementation/structure overview
├── cases/
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
│   └── eval_metrics.py                # Usage extraction and reports
├── config/
│   └── evaluation.json                # Matrix and local endpoint settings
├── docs/
│   └── EVALUATION.md                  # Setup, overnight launch and metrics
├── tests/
│   ├── test_evaluate_coding.py         # Fake-Hermes orchestration checks
│   └── test_eval_metrics.py            # Native exports, accounting and reports
├── results/
│   ├── candidates.csv                 # 14 inspected candidates and decisions
│   ├── coding-selection.md            # Discovery scope, exclusions and limits
│   └── coding-results.md              # Original autonomous/assisted results
└── evidence/
    ├── coding/C01/, coding/C02/        # Selected session analyses and results
    └── preparation/
        ├── README.md                  # Local verification summary
        ├── C01.json
        ├── C02.json
        ├── C03.json
        └── C04.json
```

Generated local data currently lives under the ignored `.runs/` directory. It is regenerated on the 5090 rather than transferred through Git:

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

Automated batches are generated under ignored `.runs/evaluation/<timestamp>/`; their frozen inputs, wheels, individual run artifacts and aggregate reports are described in the evaluation guide. Earlier manual `.runs/coding/` attempts are preserved.

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
| 5090/Linux preparation | Repeat the four before/after checks and record the remote environment/setup duration |
| Agent isolation | Owner selected the local backend; filesystem/network isolation is not enforced and is recorded as a limitation |
| Upstream test runner | Offline setup and focused collection verified locally for Click/Packaging; runner checks collection on the 5090 before each attempt |
| Runtime record | `config/run-settings.md` is planned but does not exist yet; record and freeze the existing working settings |
| Scored coding attempts | Original C01 failed, C02 passed; C03/C04 and the new automated matrix remain to run |
| Daily workflows | W01 morning briefing, W02 article capture, W03 blog assistance and W04 evening handover are planned; their case files and input fixtures are not implemented |
| Scheduled observation and usage diary | Scheduling, observation logs and `runs.csv`, `schedule.csv`, `diary.csv` are planned; no such results are recorded yet |
| Final blog results | `results/summary.md` and the final evidence narrative remain to be produced after experiments |
| Evaluation wrappers | Implemented as `evaluate_coding.py` and `eval_metrics.py`; real GPU integration still needs the documented smoke run |

Local preparation establishes case reproducibility. Local-backend runs retain the stated isolation limitation; native exports and acceptance checks support the recorded outcomes without establishing broad model performance.
