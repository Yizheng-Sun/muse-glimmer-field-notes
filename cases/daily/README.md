# Daily-task cases

**15 tasks × three variants = 45 deterministic fixtures**, inspired by [firsthand daily-task reports](../../results/daily-task-research-2026-10-11.md). All input people, projects, numbers, receipts, messages, and web pages are synthetic.

Each `Dxx.json` contains provenance, scope, input files, local web content where needed, phased prompts, and reviewer-side acceptance checks. Only the inputs and current phase prompt are supplied to the agent. Reviewer data remains outside its workspace; the local Hermes backend does not enforce an access boundary.

| ID | Task | Sessions per attempt |
| --- | --- | ---: |
| D01 | Daily schedule | 1 |
| D02 | Article capture and deduplication | 2 |
| D03 | Learning recall quiz | 1 |
| D04 | Research reading shortlist | 1 |
| D05 | Blog drafting and editorial revision | 2 |
| D06 | Meeting invitation changes | 1 |
| D07 | Training review material | 1 |
| D08 | Interview preparation | 1 |
| D09 | Evening handover and next-day continuity | 2 |
| D10 | School-message action extraction | 1 |
| D11 | Meals and shopping | 1 |
| D12 | Receipt expense report | 1 |
| D13 | Folder organization | 1 |
| D14 | Feasible trip itinerary | 1 |
| D15 | Meeting preparation | 1 |

`normal` exercises the basic request, `update` changes a relevant fact or constraint, and `problem` introduces missing, ambiguous, superseded, or constrained input. Each variant starts independently. D02, D05, and D09 additionally test saved files across fresh sessions.

Run from the repository root:

```bash
bash scripts/run_daily_evaluation.sh --dry-run
bash scripts/run_daily_evaluation.sh
```

The default is 24 attempts covering D02, D06, D09, and D12. Add `--all` for 90 attempts covering every task. See [the complete guide](../../docs/DAILY_EVALUATION.md) for filtering, configuration, budgets, reports, resume, and limitations.

Edit [scripts/daily_cases.py](../../scripts/daily_cases.py), then regenerate these JSONs with `python3.12 scripts/prepare_daily.py`. `--check` verifies that the tracked JSONs match the generator. Objective checks are implemented in [scripts/daily_checks.py](../../scripts/daily_checks.py), with no LLM judge. Prose quality requires human review.
