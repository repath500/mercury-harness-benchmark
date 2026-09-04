# Mercury Harness Benchmark V2 — GLM-5.3-Flash study

**Study date:** 2026-09-04  
**Benchmark:** `mercury-harness-v2`  
**Model:** `z-ai/glm-5.3-flash` through OpenRouter  
**Environment:** Harbor + E2B, one fresh single-container sandbox per trial  
**Trials:** 140/140 canonical trials complete  
**Human intervention:** none

## Abstract

This study compares seven coding harnesses on a frozen, oracle-validated block of 20 FeatBench repository feature tasks. The completed matrix contains **124 externally verified resolutions across 140 trials**. Every trial used the same GLM-5.3-Flash model, Harbor-managed task/evaluator flow, and a disposable E2B single-container environment. The harness—not the repository task, model ID, or verifier—was the experimental variable.

V2 extends the first study with vanilla Pi, Oh My Pi, Claude Code, Codex, the official DeepSeek Harness, CritiqueCode, and OpenCode. It also records first-request and first-tool latency, active-time share, context growth, test-run counts, normalized native-tool activity, verifier-suite gaps, patch size, artifact size, termination taxonomy, and provider-ledger completeness.

This is a descriptive study: one run per task/harness pair, seven harnesses, and a 20-task block. 7 trials required a verifier-only replay after Harbor stalled while collecting artifacts; no model inference was rerun for those recoveries. The difficulty strata are frozen selection labels derived from static task/test/reference-patch surface signals; FeatBench does not supply an official difficulty score for this block. The results should be replicated before being treated as a universal ranking or a procurement claim.

## Research questions

1. How often does each harness satisfy both FeatBench’s Fail-to-Pass (F2P) feature suite and Pass-to-Pass (P2P) regression suite?
2. How do cost, token volume, and agent runtime differ when GLM-5.3-Flash is held constant?
3. Do tool volume, failed tools, context growth, test behavior, or termination claims explain resolution differences?
4. Does the larger V2 block change the V1 observations without pretending the two blocks are a controlled longitudinal comparison?

## Headline results

The table below is computed from completed canonical records only. Costs are direct OpenRouter generation totals only where every captured generation ID in the trial was reconciled; otherwise the result bundle records a transparent catalog estimate from recorded tokens. Codex’s reconciled OpenRouter records reported zero `total_cost` while its native trajectory recorded substantial token usage; that provider response is preserved, but should not be interpreted as proof that inference is universally free.

| Harness | Resolved | Displayed cost | Cost / resolved | Tokens | Median agent time | Regressions | False completions |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pi (vanilla) | 19/20 | $0.662295 | $0.034858 | 17,242,501 | 7:59 | 0 | 0 |
| Oh My Pi | 20/20 | $1.237036 | $0.061852 | 37,057,409 | 8:39 | 0 | 0 |
| Claude Code | 19/20 | $1.236632 | $0.065086 | 30,286,765 | 6:38 | 0 | 1 |
| Codex | 15/20 | $0.000000 | $0.000000 | 20,647,847 | 5:18 | 0 | 5 |
| DeepSeek Harness | 20/20 | $1.033177 | $0.051659 | 3,409,985 | 8:41 | 0 | 0 |
| CritiqueCode | 13/20 | $0.065850 | $0.005065 | 663,906 | 2:24 | 1 | 7 |
| OpenCode | 18/20 | $1.638882 | $0.091049 | 21,644,211 | 5:25 | 0 | 2 |

## Difficulty-stratified results

| Harness | Easy | Hard | Very hard |
|---|---:|---:|---:|
| Pi (vanilla) | 9/10 | 5/5 | 5/5 |
| Oh My Pi | 10/10 | 5/5 | 5/5 |
| Claude Code | 9/10 | 5/5 | 5/5 |
| Codex | 9/10 | 2/5 | 4/5 |
| DeepSeek Harness | 10/10 | 5/5 | 5/5 |
| CritiqueCode | 7/10 | 4/5 | 2/5 |
| OpenCode | 8/10 | 5/5 | 5/5 |

The easy block is a ceiling check, not a complete benchmark: it contains ten focused tasks. The five hard and five very-hard tasks are where the study expects more separation. A missing result in a partial run is never silently converted into a failure; once the matrix is complete, every harness row should contain 20 trials.

## Additional telemetry

| Harness | Model requests | Tool calls | Failed tools | Tool calls / request | Test-run events | Median first request | Median first tool | Median context growth | Median active share | Files changed | + / − lines |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Pi (vanilla) | 724 | 855 | 0 | 1.18 | 143 | 0:05 | 0:05 | 8.11× | 79.9% | 59 | 1,573 / 230 |
| Oh My Pi | 776 | 949 | 64 | 1.22 | 105 | 0:01 | — | — | 83.7% | 66 | 1,528 / 408 |
| Claude Code | 711 | 856 | 209 | 1.20 | 123 | 0:00 | — | — | 84.2% | 63 | 1,623 / 273 |
| Codex | 616 | 596 | 117 | 0.97 | 120 | 0:02 | — | — | 77.6% | 63 | 3,052 / 2,086 |
| DeepSeek Harness | 816 | 937 | 0 | 1.15 | 3,596 | 0:01 | 0:07 | 2.02× | 86.0% | 66 | 3,466 / 2,229 |
| CritiqueCode | 445 | 480 | 74 | 1.08 | 7,576 | — | — | 9.45× | 56.4% | 43 | 2,521 / 1,935 |
| OpenCode | 668 | 769 | 132 | 1.15 | 115 | — | — | — | 80.8% | 63 | 3,253 / 2,084 |

These are explanatory telemetry, not quality scores. `context growth` is the maximum observed input-token count divided by the first observed request input, and `active share` is agent runtime divided by setup + agent + verifier wall time. Native tool taxonomies retain the original event data; the normalized categories are READ, SEARCH, EDIT, SHELL, TEST, LSP, SUBAGENT, and OTHER.

## Task selection and oracle gate

The task list was frozen before any V2 agent trial in [`benchmarks/mercury_v2/tasks/mercury-v2.txt`](../../benchmarks/mercury_v2/tasks/mercury-v2.txt). No V1 task was reused. The source dataset was `PGCodeLLM/FeatBench`, revision `v1.0`, through Harbor’s FeatBench adapter.

| Stratum | Task | Static selection rationale |
|---|---|---|
| easy | `stanfordnlp__dspy-8247` | One F2P test, 22-line reference patch, single focused behavior. |
| easy | `stanfordnlp__dspy-8102` | One F2P test, 30-line reference patch, single focused behavior. |
| easy | `projectmesa__mesa-2502` | One F2P test and 17-line reference patch. |
| easy | `projectmesa__mesa-2463` | One F2P test and 37-line reference patch. |
| easy | `projectmesa__mesa-2253` | One F2P test and 70-line reference patch with modest scope. |
| easy | `huggingface__smolagents-1302` | One F2P test and 51-line reference patch. |
| easy | `huggingface__smolagents-1314` | One F2P test and 13-line reference patch. |
| easy | `huggingface__smolagents-1104` | One F2P test and 17-line reference patch. |
| easy | `jpadilla__pyjwt-979` | One F2P test and 66-line reference patch. |
| easy | `slackapi__bolt-python-1104` | Two F2P tests and 19-line reference patch with limited file surface. |
| hard | `stanfordnlp__dspy-8139` | Two F2P tests, broad regression suite, and 97-line reference patch. |
| hard | `stanfordnlp__dspy-7872` | Four F2P tests, broad regression suite, and 136-line reference patch. |
| hard | `openai__openai-agents-python-1198` | Four F2P tests and 310-line cross-cutting reference patch. |
| hard | `aiogram__aiogram-1670` | Three F2P tests, multi-file behavior, and 146-line reference patch. |
| hard | `iterative__dvc-10754` | Three F2P tests, repository-level integration surface, and 75-line reference patch. |
| very hard | `openai__openai-agents-python-1080` | Ten F2P tests and 971 test-patch lines across a broad response surface. |
| very hard | `openai__openai-agents-python-842` | Eight F2P tests and 272 test-patch lines across a broad API surface. |
| very hard | `jpadilla__pyjwt-886` | Twelve F2P tests and 145-line reference patch. |
| very hard | `reflex-dev__reflex-5583` | Six F2P tests, 211-line reference patch, and framework-level scope. |
| very hard | `conan-io__conan-18493` | Eight F2P tests, 160-line reference patch, and a large package/build regression surface. |

Before model spending, Harbor ran the official/reference solution for every candidate in a fresh E2B sandbox and then ran the external verifier. All 20 selected tasks returned reward `1.0`, which means both the feature and regression suites passed under the reference patch. The gate decision is recorded in [`oracle-gate.json`](../../benchmarks/mercury_v2/oracle-gate.json); the public bundle indexes omitted raw Harbor directories in [`raw-trials-manifest.json`](../../benchmarks/mercury_v2/results/mercury-v2/raw-trials-manifest.json).

## Experimental protocol

Every canonical trial followed this lifecycle:

```text
Frozen task ID + natural-language request
        ↓
Harbor trial start
        ↓
Fresh E2B single-container sandbox
        ↓
Repository checkout + harness installation/configuration
        ↓
agent_started_at
        ↓
Harness uses z-ai/glm-5.3-flash through OpenRouter
        ↓
Agent exit or 60-minute agent timeout
        ↓
Harbor runs the external FeatBench verifier
        ↓
Capture result, F2P/P2P counts, patch, logs, trajectory, telemetry
        ↓
Destroy the E2B sandbox
```

The launcher used concurrency two and rotated harness order by task index. Setup time is separate from agent time. No harness was placed into a sandbox previously used by another harness. Human intervention was disabled. The generated FeatBench declarations used 2 CPUs for 17 tasks and 8 CPUs for 3 tasks; the planned 10-CPU override was not applied, so this run must not be described as a fixed-10-CPU comparison.

### Harnesses

| Harness | Adapter / execution path |
|---|---|
| Pi (vanilla) | Harbor’s Pi adapter, OpenAI-compatible OpenRouter API, harness defaults |
| Oh My Pi | Custom Harbor adapter around the installed OMP CLI, preserving its native model/tool behavior |
| Claude Code | Harbor Claude Code adapter with Mercury routed through the OpenRouter Anthropic-compatible endpoint; compatibility events are recorded, never silently replaced |
| Codex | Harbor Codex adapter with the full `openrouter/z-ai/glm-5.3-flash` model path preserved |
| DeepSeek Harness | Official [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) package, `dsh --profile headless`, OpenRouter configured through its Pi-compatible provider bundle |
| CritiqueCode | Critique’s author agent adapter, using its implementation → review/verified-repair behavior and the same external FeatBench verifier |
| OpenCode | Harbor OpenCode adapter in headless/non-interactive mode, OpenRouter provider, Mercury model |

Each harness retained its normal prompt, context handling, temperature, tool strategy, and termination behavior. The benchmark measures the harness/model combination as it naturally operates, not a forced common agent loop.

## Independent verification and outcome definitions

A trial is resolved only when both suites pass:

- **F2P (Fail-to-Pass):** tests for the requested new functionality.
- **P2P (Pass-to-Pass):** existing tests that must continue passing.

An agent saying that work is done does not affect `resolved`. `false completion` is a post-hoc heuristic: completion language was found in the retained agent output while the independent verifier reported failure. Timeouts and crashes remain distinct from verifier failures. A timeout patch is still verified when Harbor produces a verifier phase.

## Cost and provider accounting

The canonical records contain 99 completed trials with complete OpenRouter generation-ledger reconciliation. The remaining records use the GLM catalog rates stored in the benchmark runner and report `cost_source=estimated_from_openrouter_catalog`. The available credential was shared across harnesses; there were not independent per-harness OpenRouter keys in this run. Therefore provider totals are authoritative when present, but aggregate cost comparisons must be read with that limitation.

The accounting pass is reproducible with [`fetch_openrouter_usage.py`](../../benchmarks/mercury_v2/scripts/fetch_openrouter_usage.py). It queries the OpenRouter generation endpoint using IDs captured in raw harness artifacts and writes a secret-free usage file; no API key is committed.

## V1 comparison

V1 used a different model (`inception/mercury-2.5-preview`), a different ten-task block, and four harnesses. Comparing raw percentages across V1 and V2 is therefore a descriptive cross-study comparison, not a model-effect estimate.

| Harness | V1 resolved | V1 median time | V2 resolved | V2 median time |
|---|---:|---:|---:|---:|
| CritiqueCode | 8/10 | 1:29 | 13/20 | 2:24 |
| Claude Code | 7/10 | 1:03 | 19/20 | 6:38 |
| Oh My Pi | 6/10 | 1:16 | 20/20 | 8:39 |
| OpenCode | 7/10 | 1:07 | 18/20 | 5:25 |

## Reproduction recipe

Use your own credentials and keep them outside the repository:

```bash
git clone https://github.com/repath500/mercury-harness-benchmark.git
cd mercury-harness-benchmark
uv tool install harbor
export E2B_API_KEY="your-e2b-key"
export OPENROUTER_API_KEY="your-openrouter-key"
export HARBOR_SOURCE_DIR="/path/to/harbor-checkout"
export PYTHONPATH="$PWD"
python3 benchmarks/mercury_v2/scripts/freeze_oracle.py
python3 benchmarks/mercury_v2/scripts/run_v2.py --mode oracle --concurrency 2
python3 benchmarks/mercury_v2/scripts/run_v2.py --mode agents --concurrency 2
python3 benchmarks/mercury_v2/scripts/fetch_openrouter_usage.py
python3 benchmarks/mercury_v2/scripts/normalize_v2.py --mode agents
python3 benchmarks/mercury_v2/scripts/build_chart_data.py
python3 benchmarks/mercury_v2/scripts/render_study.py
```

The run uses the Harbor patches in [`benchmarks/mercury_v2/patches`](../../benchmarks/mercury_v2/patches), covering model-path preservation, E2B transfer/template handling, artifact-collection timeouts, and the Debian mirror workaround. The exact frozen configuration is [`benchmark.yaml`](../../benchmarks/mercury_v2/benchmark.yaml); the adapter and runner source is under [`benchmarks/mercury_v2`](../../benchmarks/mercury_v2).

## Open-source artifact map

- [`README.md`](../../benchmarks/mercury_v2/README.md) — scope, variables, and metric definitions.
- [`benchmark.yaml`](../../benchmarks/mercury_v2/benchmark.yaml) — frozen model, environment, harness, timeout, and telemetry configuration.
- [`mercury-v2.txt`](../../benchmarks/mercury_v2/tasks/mercury-v2.txt) — frozen 20-task list.
- [`selection.json`](../../benchmarks/mercury_v2/selection.json) — static strata rationale and exclusions.
- [`oracle-gate.json`](../../benchmarks/mercury_v2/oracle-gate.json) — pre-run reference-solution gate.
- [`run_v2.py`](../../benchmarks/mercury_v2/scripts/run_v2.py) — rotated Harbor/E2B launcher.
- [`normalize_v2.py`](../../benchmarks/mercury_v2/scripts/normalize_v2.py) — canonical result and telemetry normalization.
- [`charts/data`](../../benchmarks/mercury_v2/charts/data) — secret-free chart inputs.
- [`results/mercury-v2/canonical`](../../benchmarks/mercury_v2/results/mercury-v2/canonical) — per-trial result bundles: result, trajectory, patch, agent log, verifier log, and metadata.
- [`raw-trials-manifest.json`](../../benchmarks/mercury_v2/results/mercury-v2/raw-trials-manifest.json) — secret-free index of the omitted raw Harbor directories and their evidence flags.

## Limitations and next study

- One run per task/harness pair does not support confidence intervals or significance tests.
- The three difficulty strata are study labels, not FeatBench’s official labels.
- Harbor’s E2B integration is single-container; this V2 block excludes multi-container/Compose tasks.
- A shared provider credential prevents independent per-harness billing ledgers; Codex’s provider rows also reported zero cost despite nonzero native token counts.
- Seven verifier outcomes were recovered after Harbor artifact-collection stalls; the agent evidence was retained and the verifier was rerun in a fresh sandbox, but those rows are not identical to an uninterrupted single Harbor process.
- The selected task declarations used 2 or 8 CPUs rather than a fixed 10-CPU override.
- Harness-native transcript formats differ; normalized categories improve comparison but do not erase semantic differences in tools or prompts.
- The output-claim detector is a heuristic and should not be read as a calibrated honesty classifier.
- V1 and V2 use different models and task blocks, so cross-version deltas are not causal.

The next rigorous replication should retain the V2 task list, use dedicated provider keys, run repeated trials per pair, and pre-register any change to the harness configuration or difficulty policy.
