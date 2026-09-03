# Mercury Harness Benchmark V1

Reader-friendly visual study: [`reports/mercury-v1/index.html`](../../reports/mercury-v1/index.html)  
Full technical study: [`reports/mercury-v1/STUDY.md`](../../reports/mercury-v1/STUDY.md)  
Compact machine-readable report: [`reports/mercury-v1/mercury-v1.json`](../../reports/mercury-v1/mercury-v1.json)

This benchmark compares CritiqueCode, Claude Code, Oh My Pi, and OpenCode on
the same frozen FeatBench tasks with `inception/mercury-2.5-preview` through
OpenRouter.

Each trial is a fresh Harbor E2B sandbox. V1 is intentionally limited to
single-container, CPU-only task images because Harbor's E2B environment does
not support multi-container task deployments.

The task list is frozen in `tasks/mercury-v1.txt`. The selection labels are
static metadata labels, not labels derived from CritiqueCode performance.

Oracle validation must pass before the list becomes eligible for the 40
harness trials. Runtime artifacts belong under `results/mercury-v1/` and keep
the Harbor trial output alongside canonical normalized results.

The canonical result set contains exactly 40 task/harness pairs. The raw Harbor
directory also contains setup and adapter retries; those are indexed in
`results/mercury-v1/raw-trials-manifest.json`. Never commit `.env.local` or
provider credentials.
