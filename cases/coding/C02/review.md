# C02 — preparation and human review

This is evaluator reference material. Keep this file, `case.json`, the check, fixed source, discovery notes and experiment Git history outside the coding agent's accessible filesystem. Give the agent only its sanitized prompt and clean broken source.

## Selection

The case fixes command summaries that stop at abbreviations such as `vs.` and `e.g.`. It is bounded text processing with an obvious public symptom, one production file and a quick setup. This differs from C01's environment configuration/error handling, although both belong to the same lightweight source project.

The two-week Click window supplied one suitable bounded behavior fix. Selection therefore used the permitted **30-day merge window** for this independent case. The PR itself is the original report: created **2026-09-11 06:25:50 UTC**, merged **2026-09-12 02:35:08 UTC**. No separate issue is linked; `case.json` records the PR creation date rather than inventing an issue date.

The sanitized prompt replaces the brief report with a public `Command.get_short_help_str`/group-help reproduction. It explicitly states the sentence, first-paragraph, whitespace, word-width, hyphenated-word and narrow-width behavior checked by upstream regressions. These are disclosed prompt adaptations, not hidden grading expectations. It removes the private helper name, suggested `textwrap` implementation, source links, PR number and fixed revision.

The feature commit names Kevin Deldycke as author/committer, and Rowlando13 approved the PR. No AI disclosure was observed in the inspected PR body, issue comments, review bodies, inline comments or feature commit message. This is an upstream merged reference; human-only authorship has not been independently established.

## Before/after verification

- Starting revision: `d036881798e34289a49b18a5c550c7cf687e5a7a`.
- Upstream-fixed revision: `70689853e39c30e36eb0d83d586cc914a74db9d3`.
- Boundary: the starting revision is the merged fix's verified first parent and precedes its sole feature commit `f67c2bb6c2f055c1c7a57cd46c3697fc26a7742e`. The PR API's base SHA differed from that merge parent and was not used.
- Local environment: Python 3.12.14 on macOS 26.7.1, arm64. The check needs Python 3.10+ and no third-party dependencies; the preparation helper needs Python 3.12+.
- Preparation command: `python3 scripts/prepare_case.py C02 --verify`.
- Direct check: `python3 cases/coding/C02/check.py --source .runs/coding/C02/base`, and the same command with `fixed`.
- Actual result: the broken version exits **1**, with **eight failing subcases** across five test methods; the upstream-fixed version exits **0**, with all five methods passing. Setup/import errors use exit 2, distinct from the demonstrated behavior failure.
- Selected results, environment, hashes, experiment commit and ignored raw-log paths: [preparation evidence](../../../evidence/preparation/C02.json).
- 5090 setup time and verification: **pending**. No remote validation is claimed.

The check imports `click` from the requested snapshot's `src` directory and verifies `click.__file__` lies there. It uses public command summaries and group help, rather than calling a private helper or inspecting an implementation. Controls cover ordinary first sentences, digits/uppercase/lowercase following periods, embedded dots, whitespace, paragraph boundaries, no-rewrap markers, word-aware truncation, hyphenated/long words, widths below the ellipsis length, explicitly supplied summaries and empty help.

The broken public summary is `Compare apples vs.`; the fixed summary is `Compare apples vs. pears.`. The same complete summary also appears in group help. Additional failures demonstrate that the check distinguishes the specified sentence and width rules rather than accepting a patch hardcoded to one abbreviation.

Relevant upstream regression coverage is `tests/test_utils/test_make_default_short_help.py`. **The full upstream suite and standalone pytest regressions were not run during preparation.** The dependency-free reviewer check covers the changed behavior and adjacent controls. After a scored patch, run this check and inspect the diff; broader upstream validation can be added if that patch changes wider behavior.

## Upstream reference and acceptable alternatives

The merged reference identifies sentence boundaries using the next word's first character, preserves the first paragraph and whitespace normalization, and uses a standard-library shortening routine with hyphen splitting disabled. None of those implementation choices is required by the grader: a correct manual scanner/word-shortening implementation is equally acceptable if it produces the specified public behavior.

The sentence rule is deliberately a small predictable heuristic, not complete linguistic abbreviation detection. The focused check does not establish all Click formatting behavior or translation behavior. The 5090 must rerun preparation and verify filesystem/network isolation before a scored attempt.

## Scored attempt

**Not run.** Record the eventual run ID/date, experiment commit, runtime settings, enforced filesystem/network boundary, raw transcript/patch paths, post-patch verification, hints or human edits, verdict and failure cause. Do not describe this preparation result as a Glimmer coding result.
