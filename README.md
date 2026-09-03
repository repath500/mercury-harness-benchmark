# Mercury 2.5 Harness Benchmark V1

This is the public, reproducible artifact for a 40-trial coding-harness study
using `inception/mercury-2.5-preview` through OpenRouter.

**Result:** 28/40 task resolutions across ten frozen FeatBench tasks, four
harnesses, and one fresh E2B sandbox per trial.

| Harness | Resolved | Displayed cost* | Cost / resolved* | Median agent time | False completions |
|---|---:|---:|---:|---:|---:|
| CritiqueCode | **8/10** | $0.236291 | $0.029536 | 1:29 | 2 |
| Claude Code | 7/10 | $0.537726 | $0.076818 | **1:03** | 3 |
| Oh My Pi | 6/10 | $0.373359 | $0.062226 | 1:16 | 3 |
| OpenCode | 7/10 | $0.684547 | $0.097792 | 1:07 | 3 |

\* Nineteen trial costs are complete OpenRouter generation totals; 21 are
catalog estimates from recorded token counts. One shared provider credential
was available, so this is not an independent four-ledger billing comparison.

## Read the study

- [Full study report](reports/mercury-v1/STUDY.md)
- [Compact JSON report](reports/mercury-v1/mercury-v1.json)
- [Compact Markdown report](reports/mercury-v1/mercury-v1.md)
- [Lieflat Charts visual companion](https://github.com/repath500/lieflat-charts/tree/main/templates/reports/mercury-harness-v1)

## What is included

```text
benchmarks/mercury_v1/
├── benchmark.yaml                  # V1 protocol
├── selection.json                  # task selection rationale and exclusions
├── tasks/mercury-v1.txt            # frozen ten-task list
├── tasks/featbench/                # task instructions, tests, solutions
├── agents/                         # CritiqueCode and Oh My Pi adapters
├── scripts/                        # launcher, normalization, accounting, charts
├── patches/                        # Harbor/E2B and CritiqueCode support patches
├── charts/data/                    # secret-free chart input data
└── results/mercury-v1/
    ├── canonical/                 # 40 result/trajectory/patch/log bundles
    ├── oracle/oracle-v1-final/    # ten oracle validation trials
    ├── launcher/                  # rotated run plan and launcher logs
    └── openrouter-generation-usage.json
e2b-templates/critique-pi-v1/       # runtime files used by the CritiqueCode adapter
reports/mercury-v1/                 # full study and machine-readable report
```

The raw Harbor directory contained 46 trial directories, including setup and
adapter retries, and about 148 MB of regenerated container/package data. It is
not duplicated in Git. [`raw-trials-manifest.json`](benchmarks/mercury_v1/results/mercury-v1/raw-trials-manifest.json)
indexes every raw directory. The canonical bundles retain the evidence needed
to audit the benchmark: trajectories, patches, agent logs, verifier logs, and
metadata.

## Reproduce

The run requires an E2B API key, an OpenRouter API key, and a Harbor checkout
with E2B support. Harbor 0.22.0 and E2B SDK 2.46.4 were used for V1.

```bash
uv tool install harbor
export E2B_API_KEY=…
export OPENROUTER_API_KEY=…
export HARBOR_SOURCE_DIR=/path/to/harbor

# V1 uses two small, auditable Harbor plumbing changes:
git -C "$HARBOR_SOURCE_DIR" apply benchmarks/mercury_v1/patches/harbor-e2b-v1.patch

PYTHONPATH=. uv run --no-dev --extra e2b --project "$HARBOR_SOURCE_DIR" \
  python3 benchmarks/mercury_v1/scripts/run_v1.py --concurrency 2
python3 benchmarks/mercury_v1/scripts/fetch_openrouter_usage.py
python3 benchmarks/mercury_v1/scripts/normalize_v1.py
python3 benchmarks/mercury_v1/scripts/build_chart_data.py
```

The launcher creates one `harbor trial start --env e2b --delete` process per
task/harness pair, rotates harness order by task, and uses a 3,600-second agent
timeout. Never place an API key in a task, result, chart, or committed config
file.

## Scope

V1 is deliberately limited to CPU-only, Dockerfile-backed, single-container
FeatBench tasks because Harbor's E2B environment does not support Compose or
multi-container tasks. There is no claim here about web applications requiring
databases, queues, or other external services. The study has one run per pair,
so its conclusion is descriptive rather than a variance estimate or universal
ranking.

## License

Original benchmark code, scripts, and study prose are released under the MIT
License in [LICENSE](LICENSE). See [NOTICE.md](NOTICE.md) for the separate
licenses and provenance of FeatBench task repositories, Harbor, E2B, the
CritiqueCode runtime, and the Lieflat Charts visual companion.
