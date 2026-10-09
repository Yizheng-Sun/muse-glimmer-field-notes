# Coding cases: local preparation complete

Four cases are **prepared locally**, selected on 9 October 2026 from Click and Packaging. Each unchanged behavior check fails on its pinned starting commit and passes on its upstream fixed commit on this Mac. **5090/Linux preparation and agent isolation remain pending. No scored Glimmer attempt has been run.**

| Case | Repository | Observable requirement | PR report / merge date | Local check methods | Status |
| --- | --- | --- | --- | --- | --- |
| [C01](C01/prompt.md) | Click | Environment-variable hints handle sequences and empty values | 6 Oct / 6 Oct | 6 | Prepared locally |
| [C02](C02/prompt.md) | Click | Generated short help preserves abbreviations and respects width | 11 Sep / 12 Sep | 5 | Prepared locally |
| [C03](C03/prompt.md) | Packaging | Direct-reference requirement URLs reject embedded line breaks | 10 Aug / 1 Oct | 3 | Prepared locally |
| [C04](C04/prompt.md) | Packaging | License-file validation rejects Windows drive-relative paths | 11 Aug / 2 Oct | 4 | Prepared locally |

All dates above are in 2026, UTC. PR creation is the earliest verified report for these four; none has a linked standalone issue. Recent **merges** were the selection criterion, so the older Packaging report dates are disclosed. C02 uses the permitted 30-day expansion to keep two source repositories and add a text-formatting case. These are small calibration problems, not a representative benchmark of general coding ability.

[Candidate ledger](../../results/candidates.csv) records 14 inspected candidates and selection decisions. [Selection notes](../../results/coding-selection.md) cover the five repositories scanned, exclusions and authorship caveats. [Local evidence](../../evidence/preparation/README.md) records actual failures, passes, environment and file hashes. Upstream patches are reference fixes; absence of an AI disclosure does not prove solely human authorship.

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

Export **does not enforce isolation or start an agent**. Before a scored attempt, use the existing runtime's filesystem/container boundary to expose only that case's `agent/` folder. Verify that every agent tool cannot access the shared checkout, metadata/review/check files, fixed source, cache or other cases. Disable browsing and public-internet access while retaining the local inference connection. A changed working directory or a prompt instruction is insufficient. Do not mark a case ready for a blind run until this boundary is verified.

The prompts invite regression tests in the upstream source. Before isolation, prepare their test runner inside each exported source, separate from Hermes. The minimal pin below comes from the selected Click snapshots' `uv.lock`. These optional upstream-test commands have **not** been executed here; availability and execution inside the 5090 boundary remain a preflight check. The four reviewer acceptance checks above do not need pytest.

```sh
for CASE_ID in C01 C02 C03 C04; do
  CASE_SOURCE=".runs/coding/$CASE_ID/agent/source"
  "$CASE_PYTHON" -m venv "$CASE_SOURCE/.venv"
  "$CASE_SOURCE/.venv/bin/python" -m pip install pytest==9.0.2
done
```

From inside a case's exported `source/`, use `PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest` with these focused targets: C01 `tests/test_options.py -k envvar`; C02 `tests/test_utils/test_make_default_short_help.py`; C03 `tests/test_requirements.py`; C04 `tests/test_metadata.py -k license_files`. Confirm the runner works before blocking downloads; the full upstream suites may need additional dependencies.

After a future attempt, the reviewer can check the edited agent source from outside the agent boundary:

```sh
"$CASE_PYTHON" -I cases/coding/C01/check.py --source .runs/coding/C01/agent/source
```

Also inspect the patch and run relevant upstream tests as appropriate. The preparation checks are bounded acceptance checks, not the full upstream suites. Record assistance and retain failed attempts. The final four are selected; do not replace them because Glimmer struggles. Freeze runtime settings before scoring and apply the plan's 30-minute / 60-tool-call budget.

## Remaining readiness checks

- [x] Four cases pinned; sanitized prompts, behavioral checks and local evidence committed.
- [x] Same check demonstrably fails before and passes after each upstream fix on this Mac.
- [ ] Repeat preparation on the 5090 and record Linux evidence and setup duration.
- [ ] Verify agent filesystem/network isolation and fresh-session behavior on the 5090.
- [ ] Prepare and confirm upstream test-runner availability inside the agent boundary if using pytest regressions.
- [ ] Record and freeze the existing model/runtime settings.
- [ ] Run the four scored attempts later, preserving all outcomes.
