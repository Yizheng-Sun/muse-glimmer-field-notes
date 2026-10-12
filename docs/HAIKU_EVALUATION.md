# Claude Haiku API evaluation on the Mac

Run **`claude-haiku-5-5`** through the same Hermes coding harness on your Mac. The model runs through Anthropic's API; the Mac prepares the source and executes agent tools and tests. A GPU and a local model server are unnecessary. The model ID follows [Anthropic's Haiku 5.5 documentation](https://platform.claude.com/docs/en/models/haiku-5-5/overview).

[config/evaluation-haiku.json](../config/evaluation-haiku.json) preserves the original **48-run matrix**: C01–C04 × three budgets × `low`, `medium`, `high`, `xhigh` × one repeat. Seed 42 preserves the same shuffled job order.

| Budget | Maximum tool-calling iterations | Maximum agent seconds |
| --- | ---: | ---: |
| small | 15 | 300 |
| medium | 30 | 600 |
| large | 60 | 1200 |

The total agent-time ceiling is 9 hours 20 minutes, plus setup and grading. These are iteration and time limits; token usage is measured rather than capped. Actual inference calls use your API account.

## Start with one command

Prerequisites are Git, Python 3.12+ with `pip`/`venv`, an installed `hermes` command, internet access, and an Anthropic API key with access to this model. The launcher finds a usable Python automatically, including the bundled Codex runtime when present. Set `CASE_PYTHON` if you prefer a particular interpreter. It uses your existing Hermes installation without installing or updating it. The pinned Anthropic client is prepared under each batch's `hermes-sdk/`; its files are frozen and its import is checked against Hermes' dependency environment before inference.

From this repository's root, preview all 48 jobs without a key, downloads, generated files, or API calls:

```bash
bash scripts/run_haiku_evaluation.sh --dry-run
```

Launch the whole evaluation:

```bash
bash scripts/run_haiku_evaluation.sh
```

The launcher uses an already exported `ANTHROPIC_API_KEY`, or asks for it privately before detaching. The key is required; an empty answer stops the launch. It is passed through the environment and its value is excluded from configuration and launch logs. For a noninteractive launch, export the key beforehand.

The evaluation continues in the background. Follow its progress and printed batch path with:

```bash
tail -f .runs/haiku-evaluation-launch.log
```

On macOS, the launcher uses `caffeinate` when available to prevent idle sleep while the evaluator is alive. Keep the Mac powered and its lid open; closing the lid or shutting it down can interrupt the run.

For a short API smoke test, use one case and condition:

```bash
bash scripts/run_haiku_evaluation.sh --cases C02 --efforts low --budgets small
```

Inspect that batch's `runs/C02-small-low-r01/result.json`, `transcript.log`, and `check.log`. After it finishes, launch the full matrix as a new batch. An explicit `--config` overrides the default Haiku configuration.

## Preserve the original inputs

The default launch freshly prepares each pinned broken source and verifies the failing base and passing reference. SHA-256 fingerprints then require the **same source file tree, sanitized case prompt, case metadata, and acceptance checker** as the original 5090 evaluation. A mismatch stops the comparison before model inference. [input_fingerprints](../config/evaluation-haiku.json) stores these original fingerprints, and `input-provenance.json` records the prepared inputs.

Every attempt gets a fresh source, virtual environment, synthetic Git baseline, Hermes home, and session database. The agent sees the same case request and harness instructions, with its current source path substituted. The acceptance verdict, focused upstream selections, dependency versions, timeout handling, and metric definitions use the existing [evaluation framework](EVALUATION.md).

Optionally supply a complete earlier batch to reuse its verified frozen inputs:

```bash
bash scripts/run_haiku_evaluation.sh --inputs-from /absolute/path/to/completed-glimmer-batch
```

Only `inputs/` is imported; prior agent patches and conversations are excluded. If a copied batch fails its checksum checks, use the default fresh preparation instead. Keep the original Glimmer results unchanged.

This controls the task inputs. The Mac's absolute paths, operating system, Python, and installed Hermes version differ from the 5090. Hermes can consequently generate different system text or tool behavior. Runtime versions and hashes are saved for interpretation; this comparison does not establish an identical runtime or equal latency conditions. The local tool backend retains the original absence of enforced filesystem/network isolation.

## Native reasoning settings

The native Anthropic Messages request uses:

```json
{
  "thinking": {"type": "adaptive", "display": "summarized"},
  "output_config": {"effort": "low"}
}
```

The effort changes for each condition. Haiku 5.5 supports all four selected efforts; they are model-specific behavioral settings, so matching labels do not imply equal reasoning budgets across models. See [Anthropic's effort guide](https://platform.claude.com/docs/en/build-with-claude/effort).

Glimmer's `temperature`, `top_p`, and `top_k` fields are omitted for Haiku. Adaptive thinking and replaying prior thinking blocks follow the [Haiku migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide). Parallel tool use is disabled, matching the Glimmer configuration. The installed native adapter defaults to a 128,000-token output ceiling per response, recorded in `haiku-runtime.json`; this provider-specific limit differs from the local server's generation settings.

The compatibility wrapper [hermes_haiku.py](../scripts/hermes_haiku.py) handles older Hermes adapters inside the evaluation process and leaves installed files intact. Preflight checks the API client, all four locally built requests, and thinking-block replay, then checks model access through the read-only Models API. These checks send no inference request. `haiku-runtime.json` preserves the checks and runtime hashes; unsupported or changed runtimes stop the batch. Actual request-wire capture remains unverified.

## Results and resume

Haiku batches are saved separately under **`.runs/evaluation-haiku/<timestamp>/`**. Each run retains its exported session, console transcript, source patch, acceptance/upstream logs, and `result.json`. Aggregate `results.jsonl`, `results.csv`, and `summary.md` record acceptance, process status, token/cache counters, API calls, assistant turns, tool iterations/calls, and setup/agent/check timing. Native output tokens include thinking; a separately unavailable reasoning-token counter stays unknown and is never added to output twice. Exported summarized thinking is the reasoning content the API exposes, rather than a complete internal reasoning trace.

Resume a prepared or interrupted Haiku batch using its printed path:

```bash
bash scripts/run_haiku_evaluation.sh --resume .runs/evaluation-haiku/REPLACE_WITH_BATCH_TIMESTAMP
```

Resume preserves completed results, including failures, and retains the frozen matrix and inputs. Use a new batch to repeat completed runs. The Haiku launcher refuses to resume a Glimmer batch. Its `.runs/haiku-evaluation-launch.pid` and logs are separate from the Glimmer launcher. Preserve the whole batch directory for analysis; generated data stays ignored by Git.

Validation on this Mac: **69 tests passed, with one optional evidence test skipped**. All four original input fingerprints matched, their real case virtual environments and upstream test collection succeeded, and each broken base failed acceptance as expected. The actual Hermes runtime and pinned SDK passed local request construction, CLI configuration checks, and reuse of one frozen runtime proof across two fresh session homes. Model-access responses were mocked during implementation. **No paid Haiku evaluation has been run as part of implementing this framework.**

The subsequent full API experiment completed on **11 October 2026** with **48/48 acceptance passes and 48/48 focused upstream passes**. See the [Haiku performance report](../results/haiku-evaluation-report-2026-10-11.md) for the exact recorded model version, metrics and limitations.
