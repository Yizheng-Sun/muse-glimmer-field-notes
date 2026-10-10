# Coding cases: local preparation complete

Four cases are **prepared locally**, selected on 9 October 2026 from Click and Packaging. Each unchanged behavior check fails on its pinned starting commit and passes on its upstream fixed commit on this Mac. C01 has also been verified on the 5090; its [first autonomous attempt failed acceptance](../../evidence/coding/C01/attempt-01-analysis.md), and an [assisted continuation produced a partial fix but still failed](../../evidence/coding/C01/assisted-continuation-analysis.md). C02's [first autonomous attempt passed acceptance](../../evidence/coding/C02/attempt-01-analysis.md), with incomplete upstream test maintenance. Linux preparation evidence for C02–C04 remains pending. The owner chose Hermes' local backend; filesystem and public-network isolation are not enforced for these runs.

| Case | Repository | Observable requirement | PR report / merge date | Local check methods | Status |
| --- | --- | --- | --- | --- | --- |
| [C01](C01/prompt.md) | Click | Environment-variable hints handle sequences and empty values | 6 Oct / 6 Oct | 6 | First autonomous FAIL |
| [C02](C02/prompt.md) | Click | Generated short help preserves abbreviations and respects width | 11 Sep / 12 Sep | 5 | First autonomous PASS |
| [C03](C03/prompt.md) | Packaging | Direct-reference requirement URLs reject embedded line breaks | 10 Aug / 1 Oct | 3 | Prepared locally |
| [C04](C04/prompt.md) | Packaging | License-file validation rejects Windows drive-relative paths | 11 Aug / 2 Oct | 4 | Prepared locally |

All dates above are in 2026, UTC. PR creation is the earliest verified report for these four; none has a linked standalone issue. Recent **merges** were the selection criterion, so the older Packaging report dates are disclosed. C02 uses the permitted 30-day expansion to keep two source repositories and add a text-formatting case. These are small calibration problems, not a representative benchmark of general coding ability.

[Candidate ledger](../../results/candidates.csv) records 14 inspected candidates and selection decisions. [Selection notes](../../results/coding-selection.md) cover the five repositories scanned, exclusions and authorship caveats. [Local evidence](../../evidence/preparation/README.md) records actual failures, passes, environment and file hashes. Upstream patches are reference fixes; absence of an AI disclosure does not prove solely human authorship.

[Recorded coding results](../../results/coding-results.md) keep original autonomous outcomes separate from assisted continuations.

For fresh, automated comparisons across budgets and reasoning levels, use the [evaluation runner](../../docs/EVALUATION.md). It preserves these original attempts and records its new matrix under ignored `.runs/evaluation/` folders.

## Files and dependencies

| File | Purpose | Agent input? |
| --- | --- | --- |
| `Cxx/case.json` | Full commit hashes, source URLs/dates and reproducible commands | No |
| `Cxx/prompt.md` | Adapted, sanitized observable requirement | Yes |
| `Cxx/check.py` | Reviewer-side behavioral acceptance check | No |
| `Cxx/review.md` | Upstream solution, preparation evidence and pending run notes | No |
| `scripts/prepare_case.py` | The only preparation helper | No |

Use **Git and Python 3.12+** for the helper. The upstream code supports Python 3.10+, but this helper requires 3.12+ for safe archive extraction. There are **no third-party dependencies** for these checks: they import each pinned source's `src/` directly and verify import provenance. No project build, editable install, Docker setup or changes to the installed Hermes environment are needed.

The helper fetches exact commits into `.runs/cache/`, creates clean `.runs/coding/Cxx/base` and `fixed` snapshots without Git history, and writes raw logs and verification JSON under `.runs/coding/Cxx/logs/<UTC timestamp>/`. Repeating preparation rebuilds only the two reference snapshots and keeps earlier logs. It never overwrites an exported agent copy. Keep all these generated files ignored.

These source snapshots have no `.git` directory. Git commands inside them can discover the enclosing experiment repository, which ignores `.runs/`; its status or diff therefore does not show case source edits. Inspect the saved source and filesystem patch when reviewing an attempt.

## Exact preparation commands on the 5090

Run inside this same repository's clone using its existing GitHub authentication. For the first clone:

```sh
git clone https://github.com/Yizheng-Sun/muse-glimmer-field-notes.git
cd muse-glimmer-field-notes
```

For an existing checkout, pull before starting. Set `CASE_PYTHON` to an **existing Python 3.12+ interpreter**; use `python3.12` instead of `python3` if necessary. It need not be the Hermes interpreter.

```sh
git pull --ff-only
git status --short
git rev-parse HEAD
CASE_PYTHON=python3
"$CASE_PYTHON" -c 'import sys; print(sys.version); assert sys.version_info >= (3, 12), "Use Python 3.12+"'
"$CASE_PYTHON" scripts/prepare_case.py all --verify
```

Resolve unintended checkout edits before pulling. Source download needs internet access. Successful verification reports **base=1, fixed=0** for every case. Exit 1 from a check means behavioral failure; exit 2 means setup/import failure and must not be counted as a reproduced bug. The helper exits 2 if preparation or either expected result fails. Inspect the generated logs, record the Linux Python/OS details and setup duration in the reviews, and save concise 5090 evidence before changing any case's remote-validation status.

The same checks can be run separately:

```sh
"$CASE_PYTHON" -I cases/coding/C01/check.py --source .runs/coding/C01/base
"$CASE_PYTHON" -I cases/coding/C01/check.py --source .runs/coding/C01/fixed
```

Substitute C02, C03 or C04 to inspect another case. The baseline command is deliberately expected to fail. Fixed commands must pass. The checks exercise public behavior and controls; they do not compare the code with the upstream patch.

## Prepare agent inputs, then validate the boundary

After all Linux before/after checks pass, export fresh input copies:

```sh
"$CASE_PYTHON" scripts/prepare_case.py all --export
```

For each case this creates `.runs/coding/Cxx/agent/prompt.md` and `agent/source/`, containing only the sanitized prompt and broken source. Export refuses to overwrite an existing `agent/` folder. Preserve any attempted patch/transcript and give a later attempt a new folder; do not erase it to repeat a scored run.

Export **does not enforce isolation or start an agent**. For the owner's local-backend workflow, start Hermes inside that case's `agent/source/`, provide only its sanitized prompt, and select the `terminal,file` toolsets. Instruct it to stay in that source and avoid the network. These instructions do not enforce a filesystem or network boundary; record that limitation with each attempt. Keep reviewer checks, fixed snapshots and review notes outside the supplied agent inputs.

The prompts invite regression tests in the upstream source. Prepare their test runner inside each exported source, separate from Hermes, before starting the agent. The pytest pin below comes from the selected Click snapshots' `uv.lock`. Click's broader suite also needs an editable install of the local source: `tests/test_deprecations.py` looks up its installed distribution metadata during collection. `PYTHONPATH=src` alone does not provide that metadata. The owner has reported 780 option/argument tests passing on the 5090; the editable-install step below has not been verified here. The four reviewer acceptance checks above do not need pytest or an editable install.

```sh
for CASE_ID in C01 C02 C03 C04; do
  CASE_SOURCE=".runs/coding/$CASE_ID/agent/source"
  "$CASE_PYTHON" -m venv "$CASE_SOURCE/.venv"
  "$CASE_SOURCE/.venv/bin/python" -m pip install pytest==9.0.2
  if [ "$CASE_ID" = C01 ] || [ "$CASE_ID" = C02 ]; then
    "$CASE_SOURCE/.venv/bin/python" -m pip install --no-deps -e "$CASE_SOURCE"
  fi
done
```

From inside a case's exported `source/`, use `PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest` with these focused targets: C01 `tests/test_options.py -k envvar`; C02 `tests/test_utils/test_make_default_short_help.py`; C03 `tests/test_requirements.py`; C04 `tests/test_metadata.py -k license_files`. Confirm the runner works before starting the agent; editable installation may download build requirements, and full upstream suites may need additional dependencies. Existing upstream tests passing does not replace the reviewer acceptance check for the new regression.

After a future attempt, the reviewer can check the edited agent source from outside the agent boundary:

```sh
"$CASE_PYTHON" -I cases/coding/C01/check.py --source .runs/coding/C01/agent/source
```

Also inspect the patch and run relevant upstream tests as appropriate. The preparation checks are bounded acceptance checks, not the full upstream suites. Record assistance and retain failed attempts. The final four are selected; do not replace them because Glimmer struggles. Freeze runtime settings before scoring and apply the plan's 30-minute / 60-tool-call budget.

## Remaining readiness checks

- [x] Four cases pinned; sanitized prompts, behavioral checks and local evidence committed.
- [x] Same check demonstrably fails before and passes after each upstream fix on this Mac.
- [ ] Repeat preparation on the 5090 and record Linux evidence and setup duration.
- [x] Record the chosen local backend and lack of enforced filesystem/network isolation for C01 and C02.
- [ ] Confirm fresh-session behavior for each remaining autonomous case on the 5090.
- [ ] Prepare and confirm upstream test-runner availability inside the agent boundary if using pytest regressions.
- [ ] Record and freeze the existing model/runtime settings.
- [ ] Run C03 and C04, preserving C01's original failure, its separate assisted partial-fix result, and C02's original pass.
