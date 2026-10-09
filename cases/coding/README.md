# Prepare the coding cases

Current status: **no candidates have been selected or verified yet.** First prepare one complete case, then repeat for the other three.

## 1. Find bounded, recent problems

Scan three to five repositories for tools you use or understand. Aim for roughly 12 candidates, with a two-hour discovery budget. Favor selecting the final four from one or two repositories so dependencies can be reused.

Use the recent-merge window in [PLAN.md](../../PLAN.md). Prefer a clear user-visible problem, a small meaningful patch, quick setup and a reproducible symptom. Check the original issue date too. Save exclusions and their reasons. The source repositories can be downloaded into ignored `.runs/cache/` folders; they do not need to become submodules or tracked copies in this project.

## 2. Create a case definition here

Copy `_template/` to `C01/` for the first selected candidate:

```sh
cp -R cases/coding/_template cases/coding/C01
```

Fill these files:

| File | Contents | Give to Glimmer? |
| --- | --- | --- |
| `case.json` | Repository URL, pinned starting/fixed revisions, source links, setup/check commands and selection status | No; human preparation metadata |
| `prompt.md` | Observable problem, expected behavior and allowed scope | Yes |
| `review.md` | Human solution notes, before/after evidence, adaptations and eventual verdict | No |

Use full commit hashes for both versions. If a PR is merged with multiple commits, confirm that the starting revision actually precedes its changes; do not assume the parent of the last PR commit is the broken version.

Keep the prompt free of the human patch, fixed revision, PR solution description, identifying source links and instructions that give away the implementation. Add only the reproduction and success criteria the agent would legitimately receive.

## 3. Pull and verify on the 5090

Push the case definition from here and pull it on the 5090. Before preparation, confirm the checkout has no unintended local edits and record the experiment repository's commit:

```sh
git pull --ff-only
git rev-parse HEAD
```

Inside this same checkout, use ignored `.runs/` directories to:

1. Download the upstream source and generate a clean source snapshot at `base_commit`, without `.git` history.
2. Install dependencies and run the chosen reproduction/check. Save the failure output.
3. Generate a separate temporary reference snapshot at `fixed_commit`, run the same check and save the passing output.
4. Review whether the check proves the required behavior, including relevant existing tests. It should accept a correct alternative patch.

All generated folders live inside the project checkout. Source downloads, dependency installation and human verification can use the network. During Glimmer's scored attempt, block public-internet access and restrict its filesystem to the prompt and pre-fix source. Ensure all tools, including file reads and shell commands, respect the same boundary. Retain the local inference connection.

Use a generated run folder such as `.runs/coding/C01/attempt-01/`. A fresh attempt must start from the pinned broken source, not a previous agent patch. Keep reference snapshots and preparation caches outside the agent's accessible filesystem.

Do not add new infrastructure until one manually prepared case works. A preparation helper can be included in the planned `run_case.py` later if repeating these steps becomes tedious.

## 4. Mark ready, then freeze selection

Update the metadata and review notes after verification. A case is ready only when:

- [ ] The starting and fixed revisions are pinned.
- [ ] Setup works on the 5090 within the preparation budget.
- [ ] The same meaningful check fails before and passes after the human fix.
- [ ] The prompt contains the requirement without the solution.
- [ ] Before/after logs are saved and any prompt adaptation is disclosed.
- [ ] Glimmer's tool boundary excludes reference material and the experiment repository.

Commit the metadata, review notes and selected verification evidence on the 5090, then push and pull here. Never commit dependency environments, full upstream checkouts or raw logs just to move them between machines.

Repeat for `C02`–`C04`, targeting variety where practical. Freeze the four cases before scored attempts. Each attempt has the plan's 30-minute and 60-tool-call budget; retain failures and assistance records.
