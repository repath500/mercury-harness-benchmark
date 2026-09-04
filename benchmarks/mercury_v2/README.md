# Mercury Harness Benchmark V2

V2 compares seven coding harnesses on a new, frozen 20-task FeatBench block
using `z-ai/glm-5.3-flash` through OpenRouter:

`pi`, `oh-my-pi`, `claude-code`, `codex`, the official DeepSeek Harness
(`deepseek-ai/deepseek-harness` headless `dsh`), `critique-code`, and
`opencode`.

The matrix is 20 tasks × 7 harnesses = 140 trials. Every trial gets a fresh,
single-container E2B sandbox. Tasks are stratified before agent runs into ten
easy, five hard, and five very hard instances using static test/patch surface
signals. FeatBench has no official difficulty column; those labels are V2
study strata.

The oracle/reference solution must pass both F2P and P2P before a task enters
the frozen V2 block. Raw Harbor trials remain separate from normalized
canonical results. Provider accounting is authoritative where generation IDs
are available; estimates are clearly marked otherwise.

V2 retains V1's resolution, F2P/P2P, cost, tokens, timing, tool and patch
metrics and adds first-request/first-tool latency, active-time share, context
growth, tool efficiency, test-run classification, verifier suite gaps,
termination taxonomy, artifact sizes, and provider-ledger completeness.
