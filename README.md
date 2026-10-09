# Living With Muse Glimmer

One repository for preparing and recording a week of Muse Glimmer experiments. **Muse Glimmer and Hermes are already set up. Four coding cases are prepared and verified on this Mac.** Next, pull on the 5090, repeat preparation there, and validate the agent boundary before scoring.

Private GitHub repository: [Yizheng-Sun/muse-glimmer-field-notes](https://github.com/Yizheng-Sun/muse-glimmer-field-notes).

Edit this repository on the authoring computer, push to GitHub, and pull the same repository on the 5090 machine to run the experiments. Use repository-relative paths so both checkouts work without path changes.

See [PLAN.md](PLAN.md) for the experiment scope and [the coding cases](cases/coding/README.md) for the comparison table, local evidence and exact 5090 commands. Preparation uses one standard-library Python helper; no scored experiments have run.

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the implemented components, current repository structure and remaining work.

## What belongs in Git

- Case metadata, sanitized prompts, verification instructions and review notes.
- The recorded runtime settings, without secrets or machine-specific paths.
- Selected, redacted evidence and result summaries.

Generated source snapshots, dependencies and raw logs belong under ignored `.runs/` folders within this checkout. Model files and the installed Hermes runtime stay in their existing locations. Credentials and private daily data are excluded from Git.

## GitHub workflow

Clone the private repository on the 5090 using your existing GitHub authentication:

```sh
git clone https://github.com/Yizheng-Sun/muse-glimmer-field-notes.git
cd muse-glimmer-field-notes
```

If you already use SSH for GitHub, the equivalent clone URL is `git@github.com:Yizheng-Sun/muse-glimmer-field-notes.git`. Keep the repository private while collecting personal material and review tracked files before making it public.

After the initial setup, use this sequence:

1. **Here:** edit the case files, commit the intended changes and `git push`.
2. **5090:** `git pull --ff-only`; prepare the pinned source snapshot and run the case.
3. **5090:** save selected evidence and review results, commit those paths and `git push`.
4. **Here:** `git pull --ff-only` before analyzing the results or editing those files.

Pull before each new editing session. Keep the two computers' edits sequential for this short project. Generated agent edits happen inside `.runs/`, so pulling the experiment repository does not overwrite a run's working source.

## Coding-case boundary

The whole repository is available to you on both computers. Glimmer should see only the sanitized prompt and the pre-fix working source for its current case.

Use filesystem isolation in the existing agent runtime to keep the experiment checkout, review notes, cached source Git history and reference checkouts outside the run. Working in a subdirectory does not itself restrict tools. Verify that the agent's tools cannot read the review files before describing an experiment as blind.

Record each run's experiment-repository commit and upstream starting commit. That connects the result to the exact prompt, settings and source used.
