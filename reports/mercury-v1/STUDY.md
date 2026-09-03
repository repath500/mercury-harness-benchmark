# Mercury 2.5 Harness Study — V1

**Study date:** 2026-09-03  
**Benchmark:** `mercury-harness-v1`  
**Model:** `inception/mercury-2.5-preview`  
**Environment:** Harbor + E2B, one fresh single-container sandbox per trial  
**Trials:** 40 canonical trials: 10 tasks × 4 harnesses × 1 run  
**Human intervention:** none

## Abstract

This study measures how four coding harnesses extract useful work from the same
Mercury 2.5 preview model on the same ten frozen FeatBench feature tasks:
CritiqueCode, Claude Code, Oh My Pi, and OpenCode. Harbor created and graded
each trial. E2B supplied the disposable execution environment. The external
FeatBench verifier, rather than an agent's own test claim, determined whether a
task was resolved.

The headline result is **28 of 40 tasks resolved**. CritiqueCode resolved 8/10,
Claude Code 7/10, Oh My Pi 6/10, and OpenCode 7/10. Every easy task in this
sample was resolved by every harness; the meaningful separation appeared on the
five harder tasks, where the harnesses collectively resolved 8/20 trials.

The cost figures are not all direct invoices. Nineteen trials have a complete
OpenRouter generation ledger; the other 21 use a catalog estimate from recorded
token counts. The available credential was shared across harnesses, so this run
does not provide four independent provider billing ledgers. That limitation is
part of the result and is called out wherever cost is used.

## Research question

On a fixed, oracle-validated set of repository feature tasks, how do coding
harnesses differ in:

1. externally verified resolution rate;
2. provider or catalog-estimated cost;
3. token consumption;
4. agent execution time; and
5. false-completion and regression behavior?

The comparison intentionally leaves each harness's normal prompting, tool
strategy, context handling, and termination behavior intact. It asks what the
harness naturally does with Mercury, not what happens after forcing all four
into a common internal agent loop.

This is a descriptive benchmark, not a statistically powered claim that one
harness is universally better. There is one run per task/harness pair, ten
tasks total, no confidence interval, and no significance test.

## What was frozen

The task list was frozen before the agent trials in
[`benchmarks/mercury_v1/tasks/mercury-v1.txt`](../../benchmarks/mercury_v1/tasks/mercury-v1.txt).
It contains five small/easy tasks and five broad/hard tasks, selected using
static complexity criteria rather than CritiqueCode outcomes:

| Difficulty label | Task | Feature request represented by the task |
|---|---|---|
| Easy | `huggingface__smolagents-783` | Respect a user-supplied `final_answer` tool |
| Easy | `encode__starlette-2806` | Accept flexible UUID path formats |
| Easy | `jpadilla__pyjwt-913` | Validate one or many JWT issuers |
| Easy | `tox-dev__tox-3288` | Convert parameterized generic config types |
| Easy | `dynaconf__dynaconf-1295` | Load a file without environment filtering |
| Hard | `stanfordnlp__dspy-7964` | Add failure tolerance to `BestOfN` |
| Hard | `projectmesa__mesa-2296` | Expose named spatial-cell connections |
| Hard | `openai__openai-agents-python-508` | Rename `referenceable_id` to `response_id` |
| Hard | `aiogram__aiogram-1594` | Add `get_value` across storage/FSM/scene APIs |
| Hard | `huggingface__smolagents-1442` | Migrate prompts/parsing to XML and add instructions |

The easy/hard labels are this study's static selection labels. FeatBench V1.0
does not provide an official difficulty column for this selection, and the
source `task.toml` metadata labels these instances as feature tasks. The full
selection rationale and pre-excluded IDs are in
[`selection.json`](../../benchmarks/mercury_v1/selection.json).

The selected tasks are CPU-only, Dockerfile-backed, single-container tasks with
no planned external service dependency. Their checked-in resource declarations
are 2 CPUs/4 GB RAM for eight tasks and 8 CPUs/8 GB RAM for the two
SmolAgents tasks; each declares 10 GB storage. In other words, “ten CPU-only
tasks” was implemented as ten CPU-only tasks, not as a fixed ten-vCPU lease.
This matters when reproducing timing.

## Oracle gate

Before spending model tokens, I ran the official/reference solution for every
selected task through Harbor's external verifier in E2B. All ten final oracle
trials returned reward `1.0`. A task could not enter the frozen list until both
its Fail-to-Pass (F2P) and Pass-to-Pass (P2P) suites passed under the reference
patch.

The final oracle artifacts are under
[`results/mercury-v1/oracle/oracle-v1-final`](../../benchmarks/mercury_v1/results/mercury-v1/oracle/oracle-v1-final).
The task sources, instructions, tests, and reference solutions are under
[`tasks/featbench`](../../benchmarks/mercury_v1/tasks/featbench).

This gate removed known/problematic candidates before the model run rather than
allowing an unrelated deterministic task failure to look like an agent failure.
The excluded IDs are preserved in `selection.json`.

## System and protocol

```text
Frozen FeatBench task
        │
        ▼
Harbor trial start --env e2b --delete
        │
        ▼
Fresh E2B single-container sandbox
        │
        ├── CritiqueCode
        ├── Claude Code
        ├── Oh My Pi
        └── OpenCode
                │
                ▼
       Mercury 2.5 through OpenRouter
                │
                ▼
     Harbor's independent FeatBench verifier
```

For each of the 40 canonical pairs I:

1. started a new Harbor trial with E2B;
2. injected only the provider credentials and model configuration required by
   the selected harness;
3. prepared the repository from the task's frozen starting point;
4. started the agent timer after environment preparation;
5. let the harness inspect, search, edit, run tests, and call Mercury using its
   normal tools;
6. stopped agent control when the harness exited or reached the 60-minute
   limit;
7. ran the external F2P/P2P verifier on the resulting worktree;
8. captured the final diff, trajectory, agent log, verifier log, and metadata;
9. destroyed the E2B sandbox.

The launch script ran two sandboxes concurrently and rotated the first harness
by task so that one harness did not receive every task first. The exact plan is
in [`run-plan.json`](../../benchmarks/mercury_v1/results/mercury-v1/launcher/run-plan.json);
the executable is [`run_v1.py`](../../benchmarks/mercury_v1/scripts/run_v1.py).

The timing boundary is deliberate:

```text
sandbox_setup_ms  = E2B creation + environment/repository setup
agent_ms          = harness start → harness exit/timeout
verification_ms   = harness exit → external verifier completion
```

Only `agent_ms` is the headline execution-time metric. Setup and verification
are retained for operational analysis.

## Versions and configuration

| Component | Version/configuration used |
|---|---|
| Harbor | 0.22.0, installed with E2B support |
| E2B Python SDK | 2.46.4 |
| Model | `inception/mercury-2.5-preview` |
| Model provider | OpenRouter |
| CritiqueCode | `0.1.13+bench` adapter/runtime |
| Claude Code | 2.1.259 |
| Oh My Pi | `@oh-my-pi/pi-coding-agent` 18.1.5 |
| Oh My Pi runtime | Bun 1.3.14 |
| OpenCode | 1.18.27 |
| Agent timeout | 3,600 seconds |
| Agent setup timeout | 1,800 seconds |
| Concurrency | 2 |
| Runs per task/harness | 1 |

The model ID was kept unchanged for all four harnesses. Claude Code used its
Anthropic-compatible environment variable names pointed at OpenRouter's
compatible endpoint; it did not fall back to an Anthropic model. A separate
compatibility field was recorded for the Claude/OpenRouter path.

I did **not** build a pre-warmed shared E2B base image for V1. Harness and
repository setup happened in each sandbox, before `agent_ms`, so installation
work is excluded from agent performance but remains visible in setup logs.

## Harness implementation

The benchmark uses Harbor's built-in Claude Code and OpenCode integrations and
two local adapters:

- [`critique_code.py`](../../benchmarks/mercury_v1/agents/critique_code.py)
  launches the CritiqueCode author/repair runtime and captures its native
  telemetry.
- [`oh_my_pi.py`](../../benchmarks/mercury_v1/agents/oh_my_pi.py) installs the
  pinned Oh My Pi package in the sandbox and runs it headlessly.
- [`run_v1.py`](../../benchmarks/mercury_v1/scripts/run_v1.py) maps the Claude
  Code environment to OpenRouter while retaining the Mercury model ID.

During adapter smoke validation I had to fix a missing positive-budget helper
in the CritiqueCode E2B extension. The five-line tracked change is preserved in
the working repository and as a patch in the public benchmark bundle; it is
not a hidden change to a task repository. I also made the Harbor E2B runner use
an explicit current template tag, enforce the one-hour E2B lease, and capture a
best-effort final `git diff` when Harbor's normal capture was absent. These are
benchmark plumbing changes and are documented in the source history/artifacts.

The normalization layer maps native tool names to stable categories:
`READ`, `SEARCH`, `EDIT`, `SHELL`, `TEST`, `LSP`, `SUBAGENT`, and `OTHER`, while
preserving native trajectories. This allows comparisons without throwing away
the harness-specific detail.

## Metrics

- **Resolved:** Harbor/FeatBench reward `1.0`; both F2P and P2P suites pass.
- **F2P:** tests for the requested new behavior.
- **P2P:** existing tests that must continue to pass.
- **Cost:** complete OpenRouter generation total when all captured generation
  IDs reconcile; otherwise `(input × $0.04/M + output × $0.15/M)` as a catalog
  estimate. No harness-reported figure overrides a complete provider ledger.
- **Total tokens:** recorded input plus output tokens; cached and reasoning
  fields remain separately available when supplied by a harness.
- **Median agent time:** median of the ten `agent_ms` values per harness.
- **Regression:** F2P is complete but P2P is incomplete. A task that fails F2P
  and also loses P2P coverage is a feature failure, not a regression by this
  definition.
- **False completion:** the normalized agent text contains a completion claim,
  but the independent verifier says unresolved.
- **Compatibility error:** a harness/provider interaction fails in a way that
  is specific to the model/provider compatibility path. The verifier still
  runs when a worktree is available.

The normalizer is [`normalize_v1.py`](../../benchmarks/mercury_v1/scripts/normalize_v1.py).
The provider reconciliation pass is [`fetch_openrouter_usage.py`](../../benchmarks/mercury_v1/scripts/fetch_openrouter_usage.py).

## Results

### Headline comparison

Costs below are provider-reconciled or token-catalog-estimated as described
above, not four independent invoices.

| Harness | Resolved | Cost | Cost / resolved | Total tokens | Median agent time | Regressions | False completions |
|---|---:|---:|---:|---:|---:|---:|---:|
| CritiqueCode | **8/10** | $0.236291 | $0.029536 | 5,584,876 | 1:29 | 0 | 2 |
| Claude Code | 7/10 | $0.537726 | $0.076818 | 15,609,408 | **1:03** | 0 | 3 |
| Oh My Pi | 6/10 | $0.373359 | $0.062226 | 16,671,057 | 1:16 | 0 | 3 |
| OpenCode | 7/10 | $0.684547 | $0.097792 | 17,082,376 | 1:07 | 0 | 3 |
| **All harnesses** | **28/40** | **$1.831922** | — | **54,947,717** | — | **0** | **11** |

The all-harness cost is the sum of per-trial values and is rounded to six
decimal places. The normalized JSON retains greater precision per record.

### Difficulty split

| Difficulty label | Trials | Resolved | Resolution rate | Cost | Tokens | Agent time |
|---|---:|---:|---:|---:|---:|---:|
| Easy | 20 | **20** | **100%** | $0.687020 | 21,054,012 | 28:49.8 |
| Hard | 20 | **8** | **40%** | $1.144902 | 33,893,705 | 34:39.4 |

The split is descriptive only: “hard” here is the study's fixed selection
label, not a calibrated FeatBench difficulty score.

### Task-by-task resolution matrix

`✓` means the full F2P and P2P suites passed. A fraction shows the verifier
counts for a failed trial as `F2P passed/total; P2P passed/total`.

| Task | CritiqueCode | Claude Code | Oh My Pi | OpenCode |
|---|---:|---:|---:|---:|
| SmolAgents 783 · easy | ✓ | ✓ | ✓ | ✓ |
| Starlette 2806 · easy | ✓ | ✓ | ✓ | ✓ |
| PyJWT 913 · easy | ✓ | ✓ | ✓ | ✓ |
| Tox 3288 · easy | ✓ | ✓ | ✓ | ✓ |
| Dynaconf 1295 · easy | ✓ | ✓ | ✓ | ✓ |
| DSPy 7964 · hard | ✓ `2/2; 208/208` | ✓ `2/2; 208/208` | `0/2; 206/208` | `1/2; 208/208` |
| Mesa 2296 · hard | ✓ `10/10; 204/204` | `8/10; 203/204` | `0/10; 204/204` | ✓ `10/10; 204/204` |
| OpenAI Agents 508 · hard | ✓ `29/29; 186/186` | ✓ `29/29; 186/186` | ✓ `29/29; 186/186` | ✓ `29/29; 186/186` |
| aiogram 1594 · hard | `1/3; 717/717` | `1/3; 717/717` | `1/3; 717/717` | `1/3; 717/717` |
| SmolAgents 1442 · hard | `0/7; 297/321` | `0/7; 320/321` | `5/7; 320/321` | `4/7; 303/321` |

The per-trial canonical records, trajectories, patches, agent logs, and
verifier logs are under
[`results/mercury-v1/canonical`](../../benchmarks/mercury_v1/results/mercury-v1/canonical).

### Efficiency and activity

| Harness | Input tokens | Output tokens | Total tokens | Cached tokens | Reasoning tokens | Model requests | Tool calls | Failed tools | Files changed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CritiqueCode | 5,467,644 | 117,232 | 5,584,876 | 0 | 101,787 | 502 | 562 | 139 | 63 |
| Claude Code | 15,519,295 | 90,113 | 15,609,408 | 2,682,293 | 0 | 323 | 383 | 101 | 32 |
| Oh My Pi | 16,466,788 | 204,269 | 16,671,057 | 9,099,766 | 185,438 | 403 | 467 | 40 | 47 |
| OpenCode | 17,070,994 | 11,382 | 17,082,376 | 11,182,918 | 0 | 355 | 438 | 65 | 41 |
| **Total** | **54,524,721** | **422,996** | **54,947,717** | — | — | **1,583** | **1,850** | **345** | **183** |

The total-token column is input plus output. The exact output-token sum is
**422,996**. The authoritative per-record values are retained in the JSON
artifacts:

- input: 54,524,721;
- output: 422,996;
- input + output: 54,947,717.

The per-harness totals and all canonical records are authoritative. The source
JSON reports `total_tokens = input + output`; cached and reasoning counts are
provider/harness telemetry fields and should not be added to that total.

### Patch and runtime totals

Across the 40 canonical trials:

- agent runtime: 3,809,020 ms, or about 63 minutes 29 seconds;
- sandbox setup: 84,046 ms, or about 1 minute 24 seconds;
- external verification: 5,557,402 ms, or about 92 minutes 37 seconds;
- model requests: 1,583;
- normalized tool calls: 1,850;
- failed tool calls: 345;
- files changed: 183;
- lines added: 2,684;
- lines deleted: 1,921.

The timing totals are sums across trials; because two trials ran concurrently,
they are not wall-clock elapsed time.

## Failure analysis

### The separation was on hard tasks

All 20 easy trials passed. The five hard tasks produced the observed spread:

- **OpenAI Agents 508:** all four harnesses passed. This was a cross-cutting
  rename, but its 29 F2P tests and 186 P2P tests were all satisfied by every
  harness.
- **DSPy 7964:** CritiqueCode and Claude Code passed; Oh My Pi missed all F2P
  tests and OpenCode passed only one of two F2P tests. P2P remained complete
  for OpenCode and CritiqueCode, while Oh My Pi lost two P2P tests.
- **Mesa 2296:** CritiqueCode and OpenCode passed; Claude Code and Oh My Pi
  did not complete all ten F2P tests. Claude also missed one P2P test.
- **aiogram 1594:** all four harnesses passed all 717 P2P tests but only one
  of three F2P tests. This is a shared task-level feature difficulty signal,
  not a harness-specific regression.
- **SmolAgents 1442:** none of the four harnesses passed the seven F2P tests.
  CritiqueCode and Claude Code passed none; Oh My Pi passed five; OpenCode
  passed four. P2P coverage was also incomplete for all four.

### False completions

The completion-claim detector found 11 runs where an agent's text suggested it
was done while the external verifier still failed:

| Harness | False completions | Rate |
|---|---:|---:|
| CritiqueCode | 2/10 | 20% |
| Claude Code | 3/10 | 30% |
| Oh My Pi | 3/10 | 30% |
| OpenCode | 3/10 | 30% |

This is a text heuristic, not a self-reported structured field from every
harness. The verifier result remains the source of truth.

### Compatibility and infrastructure events

- One Claude Code run on SmolAgents 1442 received an HTTP 200 response from
  the OpenRouter-compatible path that was empty or malformed for the Claude
  runtime. It was recorded as both `api_error` and `compatibility_error`; the
  run was not silently switched to another model, and the external verifier
  still ran on the available worktree.
- One Oh My Pi Dynaconf setup attempt lost its E2B sandbox during installation.
  It was rerun in a fresh sandbox and succeeded. The failed setup attempt is
  retained in raw Harbor output; the successful retry is the canonical trial.
- Early CritiqueCode/Oh My Pi smoke/setup retries were retained for auditability
  but not counted as additional benchmark pairs. Raw Harbor has 46 result
  directories; canonical V1 has exactly 40 unique task/harness pairs.
- No canonical trial timed out or crashed. This does not mean no tool command
  failed; 345 failed tool calls were recorded and normalized.

### Regressions

There were zero strict F2P-complete/P2P-incomplete regressions. That result
should not be over-read: several feature attempts also had incomplete P2P
coverage, but they did not satisfy the F2P-complete condition required for the
study's regression metric.

## Cost accounting

I added a provider reconciliation pass that extracted generation IDs from raw
agent logs and queried OpenRouter's generation endpoint. The final ledger had
725 generation IDs: 724 provider responses were available and one returned
HTTP 404. The selected canonical records break down as:

| Cost source | Trials |
|---|---:|
| Complete OpenRouter generation totals | 19 |
| OpenRouter catalog estimates | 21 |
| Harness fallback | 0 |

By harness, all ten CritiqueCode and all ten OpenCode costs are catalog
estimates because those native traces did not expose a complete generation-ID
ledger. Claude Code has ten provider-reconciled trials. Oh My Pi has nine
provider-reconciled trials and one catalog estimate.

The original V1 design called for one OpenRouter key per harness. That was not
available in the execution environment, so all four harnesses used the one
available shared credential. I did not fabricate four independent billing
ledgers. The public artifacts therefore expose the accounting method and
source flag per record, but not a provider-authoritative per-harness invoice.

## Study interpretation

Within this small fixed sample, CritiqueCode had the highest resolution rate
(8/10) and the lowest displayed cost per resolved task ($0.029536). Claude Code
had the shortest median agent runtime (1:03). Oh My Pi used fewer failed tool
calls than the other harnesses but resolved 6/10. OpenCode resolved 7/10 and
used the highest displayed aggregate cost in this run.

The responsible conclusion is narrower: on these ten oracle-valid tasks, under
this exact run configuration, CritiqueCode produced the strongest observed
resolution/cost combination, while Claude Code was fastest by median agent
runtime. The cost caveat, one-run-per-pair design, shared provider key, and
Claude compatibility event prevent a universal ranking claim.

## Threats to validity

1. **Small sample:** ten tasks and one trial per pair cannot estimate variance.
2. **Selection:** the easy/hard split is a hand-defined static mix, not a
   random or calibrated difficulty sample.
3. **Repository mix:** all tasks are library-style CPU-only tasks; results may
   not transfer to multi-service web applications.
4. **Harness defaults differ:** preserving natural harness behavior improves
   ecological validity but means prompts, tool APIs, and context strategies are
   not identical.
5. **Provider accounting:** 21 costs are estimates, and the shared key prevents
   independent provider ledgers.
6. **Model/provider compatibility:** Claude Code's Anthropic-specific behavior
   may be a genuine harness/model interaction, but it also means Claude's path
   is not a neutral generic OpenAI client.
7. **Infrastructure noise:** E2B startup, package installation, concurrency,
   and network/provider load can affect setup or agent time.
8. **Version drift:** harnesses, Harbor, E2B, and the preview model can change.
9. **Completion detector:** false-completion counts use normalized text
   matching, so they are useful telemetry rather than a gold-standard label.
10. **No inferential statistics:** no p-values, confidence intervals, or causal
    effect sizes are appropriate for this V1 run.

## Reproducibility and artifacts

The benchmark source of record contains:

- `benchmark.yaml`: frozen protocol configuration;
- `selection.json`: task rationale and exclusions;
- `tasks/mercury-v1.txt`: frozen ten-task list;
- `tasks/featbench/`: generated task environments, tests, and oracle patches;
- `agents/`: custom Harbor adapters;
- `scripts/`: launcher, normalizer, provider reconciliation, and chart-data
  builders;
- `results/mercury-v1/oracle/`: oracle validation evidence;
- `results/mercury-v1/canonical/`: 40 normalized result/trajectory/patch/log
  bundles;
- `results/mercury-v1/openrouter-generation-usage.json`: safe provider usage
  metadata with no API key;
- `reports/mercury-v1/mercury-v1.json`: machine-readable aggregate;
- `reports/mercury-v1/mercury-v1.md`: compact result table;
- `benchmarks/mercury_v1/charts/data/`: chart input data derived from the
  canonical report.

To rerun from a configured machine with E2B and OpenRouter credentials:

```bash
uv tool install harbor
set -a; source .env.local; set +a
PYTHONPATH=. uv run --no-dev --extra e2b --project "$HARBOR_SOURCE_DIR" \
  python3 benchmarks/mercury_v1/scripts/run_v1.py --concurrency 2
python3 benchmarks/mercury_v1/scripts/fetch_openrouter_usage.py
python3 benchmarks/mercury_v1/scripts/normalize_v1.py
python3 benchmarks/mercury_v1/scripts/build_chart_data.py
```

Do not commit `.env.local` or any API key. The public bundle contains variable
names and accounting metadata only; secrets are not part of the artifacts.

The complete raw Harbor directory is retained locally for audit. The public
bundle publishes the canonical per-trial trajectories, patches, logs, verifier
evidence, oracle artifacts, and all source code. It omits duplicated raw
container/package caches from the public Git history because they add roughly
150 MB of regenerated installation data without adding benchmark evidence.

## Chart/report design record

For the visual companion I used the Lieflat Charts system from
[`larashero3-dotcom/lieflat-charts`](https://github.com/larashero3-dotcom/lieflat-charts).
I compared these report templates before choosing one:

| Template | Fit | Decision |
|---|---|---|
| R01 Survey One-Pager | Good research tone, but only three chart slots and less room for a matrix plus KPI rail | Rejected |
| R04 Monthly Ops | Strong operational review structure, but its time-period framing implies a recurring monthly report | Rejected |
| R09 Data Story Dashboard | Four chart slots plus KPI rail, 1080px study-page format, and the right density for harness/task comparison | **Selected** |
| R11 Research Brief Card | Strong fixed social/card output, but too constrained for 40 trials and per-task caveats | Rejected |

The visual report uses one Porcelain color system and adapts four data-backed
views from the Lieflat catalog/gallery rather than retaining demo values:

| Study view | Lieflat source grammar | Claim shown |
|---|---|---|
| Resolved by harness | F1/Rung Bars | Resolution count/rate by harness |
| Task × harness matrix | Basics dot/matrix grammar | Where each harness passed or failed |
| Cost versus median time | F12/Dumbbell comparison grammar | Cost/time tradeoff |
| Token and tool activity | F5/Tick Rows grammar | Work volume and failure telemetry |

The chart input JSON is generated by
[`build_chart_data.py`](../../benchmarks/mercury_v1/scripts/build_chart_data.py)
from the canonical report; it is not hand-entered presentation data.

## Conclusion

V1 completed the requested 40-run architecture: Harbor chose and graded the
work, each trial received a fresh E2B sandbox, Mercury was kept constant, and
the harness remained the experimental variable. The benchmark found a clear
easy-task ceiling and meaningful hard-task separation, with 28/40 total
resolutions and 11 text-detected false completions. It also surfaced an actual
Claude/OpenRouter compatibility failure and the cost-ledger limitation that
must be fixed before making stronger cost claims.

The next scientifically useful iteration is not a larger aggregate first. It
is to repeat the same frozen ten tasks several times with dedicated
per-harness OpenRouter keys, then add a second pre-registered task block only
after the replicated V1 variance is known.
