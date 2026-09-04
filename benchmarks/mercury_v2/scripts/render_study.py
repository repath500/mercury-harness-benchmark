#!/usr/bin/env python3
"""Render the reader-facing V2 technical study from canonical records."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "mercury-v2" / "mercury-v2.json"
SELECTION = ROOT / "benchmarks" / "mercury_v2" / "selection.json"
V1_REPORT = ROOT / "reports" / "mercury-v1" / "mercury-v1.json"
OUT = ROOT / "reports" / "mercury-v2" / "STUDY.md"
TASK_LIST = ROOT / "benchmarks" / "mercury_v2" / "tasks" / "mercury-v2.txt"
HARNESS_ORDER = (
    "pi", "oh-my-pi", "claude-code", "codex", "deepseek-harness", "critique-code", "opencode"
)
LABELS = {
    "pi": "Pi (vanilla)", "oh-my-pi": "Oh My Pi", "claude-code": "Claude Code",
    "codex": "Codex", "deepseek-harness": "DeepSeek Harness", "critique-code": "CritiqueCode",
    "opencode": "OpenCode",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def fmt_usd(value: Any) -> str:
    return "—" if not isinstance(value, (int, float)) else f"${value:,.6f}"


def fmt_int(value: Any) -> str:
    return "—" if not isinstance(value, (int, float)) else f"{int(value):,}"


def fmt_ms(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    seconds = int(value // 1000)
    return f"{seconds // 60}:{seconds % 60:02d}"


def rows_for(records: list[dict[str, Any]], harness: str) -> list[dict[str, Any]]:
    return [r for r in records if r.get("harness") == harness and r.get("status") == "complete"]


def mean_or_none(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.mean(numbers) if numbers else None


def median_or_none(values: list[Any]) -> float | None:
    numbers = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.median(numbers) if numbers else None


def summary(records: list[dict[str, Any]], harness: str) -> dict[str, Any]:
    rows = rows_for(records, harness)
    solved = sum(bool(r["result"].get("resolved")) for r in rows)
    costs = [r.get("cost_usd") for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    return {
        "runs": len(rows), "solved": solved, "cost": sum(costs),
        "cost_per_resolved": sum(costs) / solved if solved else None,
        "tokens": sum(r["tokens"].get("total") or 0 for r in rows),
        "input": sum(r["tokens"].get("input") or 0 for r in rows),
        "output": sum(r["tokens"].get("output") or 0 for r in rows),
        "cached": sum(r["tokens"].get("cached") or 0 for r in rows),
        "reasoning": sum(r["tokens"].get("reasoning") or 0 for r in rows),
        "median_ms": median_or_none([r["timing"].get("agent_ms") for r in rows]),
        "first_request_ms": median_or_none([r["timing"].get("first_model_request_ms") for r in rows]),
        "first_tool_ms": median_or_none([r["timing"].get("first_tool_call_ms") for r in rows]),
        "active_share": median_or_none([r["timing"].get("active_time_share") for r in rows]),
        "context_growth": median_or_none([r["timing"].get("context_growth", {}).get("ratio") for r in rows]),
        "model_requests": sum(r.get("model_requests") or 0 for r in rows),
        "tool_calls": sum(r["tools"].get("total") or 0 for r in rows),
        "failed_tools": sum(r["tools"].get("failed") or 0 for r in rows),
        "test_runs": sum(r["observations"].get("test_runs") or 0 for r in rows),
        "files": sum(r["patch"].get("files_changed") or 0 for r in rows),
        "added": sum(r["patch"].get("lines_added") or 0 for r in rows),
        "deleted": sum(r["patch"].get("lines_deleted") or 0 for r in rows),
        "regressions": sum(r["result"].get("verifier_suite_gap") == "regression_p2p_failure" for r in rows),
        "false_completions": sum(bool(r["termination"].get("claimed_success") and not r["result"].get("resolved")) for r in rows),
        "timeouts": sum(bool(r["termination"].get("timeout")) for r in rows),
        "crashes": sum(bool(r["termination"].get("crash")) for r in rows),
        "compatibility": sum(bool(r["termination"].get("compatibility_error")) for r in rows),
        "provider": sum(bool(r.get("provider_accounting", {}).get("complete")) for r in rows),
    }


def markdown(records: list[dict[str, Any]], selection: dict[str, Any], v1: dict[str, Any] | None) -> str:
    completed = [r for r in records if r.get("status") == "complete"]
    solved = sum(bool(r["result"].get("resolved")) for r in completed)
    all_runs = len(records)
    provider = sum(bool(r.get("provider_accounting", {}).get("complete")) for r in completed)
    recoveries = sum(bool(r.get("recovery")) for r in completed)
    lines = [
        "# Mercury Harness Benchmark V2 — GLM-5.3-Flash study",
        "",
        "**Study date:** 2026-09-04  ",
        "**Benchmark:** `mercury-harness-v2`  ",
        "**Model:** `z-ai/glm-5.3-flash` through OpenRouter  ",
        "**Environment:** Harbor + E2B, one fresh single-container sandbox per trial  ",
        f"**Trials:** {len(completed)}/{all_runs} canonical trials complete  ",
        "**Human intervention:** none",
        "",
        "## Abstract",
        "",
        f"This study compares seven coding harnesses on a frozen, oracle-validated block of 20 FeatBench repository feature tasks. The completed matrix contains **{solved} externally verified resolutions across {len(completed)} trials**. Every trial used the same GLM-5.3-Flash model, Harbor-managed task/evaluator flow, and a disposable E2B single-container environment. The harness—not the repository task, model ID, or verifier—was the experimental variable.",
        "",
        "V2 extends the first study with vanilla Pi, Oh My Pi, Claude Code, Codex, the official DeepSeek Harness, CritiqueCode, and OpenCode. It also records first-request and first-tool latency, active-time share, context growth, test-run counts, normalized native-tool activity, verifier-suite gaps, patch size, artifact size, termination taxonomy, and provider-ledger completeness.",
        "",
        f"This is a descriptive study: one run per task/harness pair, seven harnesses, and a 20-task block. {recoveries} trials required a verifier-only replay after Harbor stalled while collecting artifacts; no model inference was rerun for those recoveries. The difficulty strata are frozen selection labels derived from static task/test/reference-patch surface signals; FeatBench does not supply an official difficulty score for this block. The results should be replicated before being treated as a universal ranking or a procurement claim.",
        "",
        "## Research questions",
        "",
        "1. How often does each harness satisfy both FeatBench’s Fail-to-Pass (F2P) feature suite and Pass-to-Pass (P2P) regression suite?",
        "2. How do cost, token volume, and agent runtime differ when GLM-5.3-Flash is held constant?",
        "3. Do tool volume, failed tools, context growth, test behavior, or termination claims explain resolution differences?",
        "4. Does the larger V2 block change the V1 observations without pretending the two blocks are a controlled longitudinal comparison?",
        "",
        "## Headline results",
        "",
        "The table below is computed from completed canonical records only. Costs are direct OpenRouter generation totals only where every captured generation ID in the trial was reconciled; otherwise the result bundle records a transparent catalog estimate from recorded tokens. Codex’s reconciled OpenRouter records reported zero `total_cost` while its native trajectory recorded substantial token usage; that provider response is preserved, but should not be interpreted as proof that inference is universally free.",
        "",
        "| Harness | Resolved | Displayed cost | Cost / resolved | Tokens | Median agent time | Regressions | False completions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    sums = {h: summary(records, h) for h in HARNESS_ORDER}
    for h in HARNESS_ORDER:
        s = sums[h]
        lines.append(f"| {LABELS[h]} | {s['solved']}/{s['runs']} | {fmt_usd(s['cost'])} | {fmt_usd(s['cost_per_resolved'])} | {fmt_int(s['tokens'])} | {fmt_ms(s['median_ms'])} | {s['regressions']} | {s['false_completions']} |")
    lines += [
        "",
        "## Difficulty-stratified results",
        "",
        "| Harness | Easy | Hard | Very hard |",
        "|---|---:|---:|---:|",
    ]
    for h in HARNESS_ORDER:
        cells = []
        for difficulty in ("easy", "hard", "very-hard"):
            rows = [r for r in rows_for(records, h) if r.get("difficulty") == difficulty]
            cells.append(f"{sum(bool(r['result'].get('resolved')) for r in rows)}/{len(rows)}")
        lines.append(f"| {LABELS[h]} | {' | '.join(cells)} |")
    lines += [
        "",
        "The easy block is a ceiling check, not a complete benchmark: it contains ten focused tasks. The five hard and five very-hard tasks are where the study expects more separation. A missing result in a partial run is never silently converted into a failure; once the matrix is complete, every harness row should contain 20 trials.",
        "",
        "## Additional telemetry",
        "",
        "| Harness | Model requests | Tool calls | Failed tools | Tool calls / request | Test-run events | Median first request | Median first tool | Median context growth | Median active share | Files changed | + / − lines |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for h in HARNESS_ORDER:
        s = sums[h]
        efficiency = s["tool_calls"] / s["model_requests"] if s["model_requests"] else None
        efficiency_text = f"{efficiency:.2f}" if isinstance(efficiency, (int, float)) else "—"
        context_text = f"{s['context_growth']:.2f}×" if isinstance(s["context_growth"], (int, float)) else "—"
        share_text = f"{s['active_share']:.1%}" if isinstance(s["active_share"], (int, float)) else "—"
        lines.append(f"| {LABELS[h]} | {fmt_int(s['model_requests'])} | {fmt_int(s['tool_calls'])} | {fmt_int(s['failed_tools'])} | {efficiency_text} | {fmt_int(s['test_runs'])} | {fmt_ms(s['first_request_ms'])} | {fmt_ms(s['first_tool_ms'])} | {context_text} | {share_text} | {fmt_int(s['files'])} | {fmt_int(s['added'])} / {fmt_int(s['deleted'])} |")
    lines += [
        "",
        "These are explanatory telemetry, not quality scores. `context growth` is the maximum observed input-token count divided by the first observed request input, and `active share` is agent runtime divided by setup + agent + verifier wall time. Native tool taxonomies retain the original event data; the normalized categories are READ, SEARCH, EDIT, SHELL, TEST, LSP, SUBAGENT, and OTHER.",
        "",
        "## Task selection and oracle gate",
        "",
        "The task list was frozen before any V2 agent trial in [`benchmarks/mercury_v2/tasks/mercury-v2.txt`](../../benchmarks/mercury_v2/tasks/mercury-v2.txt). No V1 task was reused. The source dataset was `PGCodeLLM/FeatBench`, revision `v1.0`, through Harbor’s FeatBench adapter.",
        "",
        "| Stratum | Task | Static selection rationale |",
        "|---|---|---|",
    ]
    for difficulty in ("easy", "hard", "very_hard"):
        for item in selection.get(difficulty, []):
            lines.append(f"| {difficulty.replace('_', ' ')} | `{item['instance_id']}` | {item['reason']} |")
    lines += [
        "",
        "Before model spending, Harbor ran the official/reference solution for every candidate in a fresh E2B sandbox and then ran the external verifier. All 20 selected tasks returned reward `1.0`, which means both the feature and regression suites passed under the reference patch. The gate decision is recorded in [`oracle-gate.json`](../../benchmarks/mercury_v2/oracle-gate.json); the public bundle indexes omitted raw Harbor directories in [`raw-trials-manifest.json`](../../benchmarks/mercury_v2/results/mercury-v2/raw-trials-manifest.json).",
        "",
        "## Experimental protocol",
        "",
        "Every canonical trial followed this lifecycle:",
        "",
        "```text",
        "Frozen task ID + natural-language request",
        "        ↓",
        "Harbor trial start",
        "        ↓",
        "Fresh E2B single-container sandbox",
        "        ↓",
        "Repository checkout + harness installation/configuration",
        "        ↓",
        "agent_started_at",
        "        ↓",
        "Harness uses z-ai/glm-5.3-flash through OpenRouter",
        "        ↓",
        "Agent exit or 60-minute agent timeout",
        "        ↓",
        "Harbor runs the external FeatBench verifier",
        "        ↓",
        "Capture result, F2P/P2P counts, patch, logs, trajectory, telemetry",
        "        ↓",
        "Destroy the E2B sandbox",
        "```",
        "",
        "The launcher used concurrency two and rotated harness order by task index. Setup time is separate from agent time. No harness was placed into a sandbox previously used by another harness. Human intervention was disabled. The generated FeatBench declarations used 2 CPUs for 17 tasks and 8 CPUs for 3 tasks; the planned 10-CPU override was not applied, so this run must not be described as a fixed-10-CPU comparison.",
        "",
        "### Harnesses",
        "",
        "| Harness | Adapter / execution path |",
        "|---|---|",
        "| Pi (vanilla) | Harbor’s Pi adapter, OpenAI-compatible OpenRouter API, harness defaults |",
        "| Oh My Pi | Custom Harbor adapter around the installed OMP CLI, preserving its native model/tool behavior |",
        "| Claude Code | Harbor Claude Code adapter with Mercury routed through the OpenRouter Anthropic-compatible endpoint; compatibility events are recorded, never silently replaced |",
        "| Codex | Harbor Codex adapter with the full `openrouter/z-ai/glm-5.3-flash` model path preserved |",
        "| DeepSeek Harness | Official [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) package, `dsh --profile headless`, OpenRouter configured through its Pi-compatible provider bundle |",
        "| CritiqueCode | Critique’s author agent adapter, using its implementation → review/verified-repair behavior and the same external FeatBench verifier |",
        "| OpenCode | Harbor OpenCode adapter in headless/non-interactive mode, OpenRouter provider, Mercury model |",
        "",
        "Each harness retained its normal prompt, context handling, temperature, tool strategy, and termination behavior. The benchmark measures the harness/model combination as it naturally operates, not a forced common agent loop.",
        "",
        "## Independent verification and outcome definitions",
        "",
        "A trial is resolved only when both suites pass:",
        "",
        "- **F2P (Fail-to-Pass):** tests for the requested new functionality.",
        "- **P2P (Pass-to-Pass):** existing tests that must continue passing.",
        "",
        "An agent saying that work is done does not affect `resolved`. `false completion` is a post-hoc heuristic: completion language was found in the retained agent output while the independent verifier reported failure. Timeouts and crashes remain distinct from verifier failures. A timeout patch is still verified when Harbor produces a verifier phase.",
        "",
        "## Cost and provider accounting",
        "",
        f"The canonical records contain {provider} completed trials with complete OpenRouter generation-ledger reconciliation. The remaining records use the GLM catalog rates stored in the benchmark runner and report `cost_source=estimated_from_openrouter_catalog`. The available credential was shared across harnesses; there were not independent per-harness OpenRouter keys in this run. Therefore provider totals are authoritative when present, but aggregate cost comparisons must be read with that limitation.",
        "",
        "The accounting pass is reproducible with [`fetch_openrouter_usage.py`](../../benchmarks/mercury_v2/scripts/fetch_openrouter_usage.py). It queries the OpenRouter generation endpoint using IDs captured in raw harness artifacts and writes a secret-free usage file; no API key is committed.",
        "",
        "## V1 comparison",
        "",
        "V1 used a different model (`inception/mercury-2.5-preview`), a different ten-task block, and four harnesses. Comparing raw percentages across V1 and V2 is therefore a descriptive cross-study comparison, not a model-effect estimate.",
        "",
        "| Harness | V1 resolved | V1 median time | V2 resolved | V2 median time |",
        "|---|---:|---:|---:|---:|",
    ]
    if isinstance(v1, dict):
        for old, new in (("critique-code", "critique-code"), ("claude-code", "claude-code"), ("oh-my-pi", "oh-my-pi"), ("opencode", "opencode")):
            old_s = v1.get("harnesses", {}).get(old, {})
            new_s = sums[new]
            lines.append(f"| {LABELS[new]} | {old_s.get('resolved', '—')}/{old_s.get('runs', '—')} | {fmt_ms(old_s.get('median_agent_ms'))} | {new_s['solved']}/{new_s['runs']} | {fmt_ms(new_s['median_ms'])} |")
    else:
        lines.append("| V1 report unavailable | — | — | — | — |")
    lines += [
        "",
        "## Reproduction recipe",
        "",
        "Use your own credentials and keep them outside the repository:",
        "",
        "```bash",
        "git clone https://github.com/repath500/mercury-harness-benchmark.git",
        "cd mercury-harness-benchmark",
        "uv tool install harbor",
        "export E2B_API_KEY=\"your-e2b-key\"",
        "export OPENROUTER_API_KEY=\"your-openrouter-key\"",
        "export HARBOR_SOURCE_DIR=\"/path/to/harbor-checkout\"",
        "export PYTHONPATH=\"$PWD\"",
        "python3 benchmarks/mercury_v2/scripts/freeze_oracle.py",
        "python3 benchmarks/mercury_v2/scripts/run_v2.py --mode oracle --concurrency 2",
        "python3 benchmarks/mercury_v2/scripts/run_v2.py --mode agents --concurrency 2",
        "python3 benchmarks/mercury_v2/scripts/fetch_openrouter_usage.py",
        "python3 benchmarks/mercury_v2/scripts/normalize_v2.py --mode agents",
        "python3 benchmarks/mercury_v2/scripts/build_chart_data.py",
        "python3 benchmarks/mercury_v2/scripts/render_study.py",
        "```",
        "",
        "The run uses the Harbor patches in [`benchmarks/mercury_v2/patches`](../../benchmarks/mercury_v2/patches), covering model-path preservation, E2B transfer/template handling, artifact-collection timeouts, and the Debian mirror workaround. The exact frozen configuration is [`benchmark.yaml`](../../benchmarks/mercury_v2/benchmark.yaml); the adapter and runner source is under [`benchmarks/mercury_v2`](../../benchmarks/mercury_v2).",
        "",
        "## Open-source artifact map",
        "",
        "- [`README.md`](../../benchmarks/mercury_v2/README.md) — scope, variables, and metric definitions.",
        "- [`benchmark.yaml`](../../benchmarks/mercury_v2/benchmark.yaml) — frozen model, environment, harness, timeout, and telemetry configuration.",
        "- [`mercury-v2.txt`](../../benchmarks/mercury_v2/tasks/mercury-v2.txt) — frozen 20-task list.",
        "- [`selection.json`](../../benchmarks/mercury_v2/selection.json) — static strata rationale and exclusions.",
        "- [`oracle-gate.json`](../../benchmarks/mercury_v2/oracle-gate.json) — pre-run reference-solution gate.",
        "- [`run_v2.py`](../../benchmarks/mercury_v2/scripts/run_v2.py) — rotated Harbor/E2B launcher.",
        "- [`normalize_v2.py`](../../benchmarks/mercury_v2/scripts/normalize_v2.py) — canonical result and telemetry normalization.",
        "- [`charts/data`](../../benchmarks/mercury_v2/charts/data) — secret-free chart inputs.",
        "- [`results/mercury-v2/canonical`](../../benchmarks/mercury_v2/results/mercury-v2/canonical) — per-trial result bundles: result, trajectory, patch, agent log, verifier log, and metadata.",
        "- [`raw-trials-manifest.json`](../../benchmarks/mercury_v2/results/mercury-v2/raw-trials-manifest.json) — secret-free index of the omitted raw Harbor directories and their evidence flags.",
        "",
        "## Limitations and next study",
        "",
        "- One run per task/harness pair does not support confidence intervals or significance tests.",
        "- The three difficulty strata are study labels, not FeatBench’s official labels.",
        "- Harbor’s E2B integration is single-container; this V2 block excludes multi-container/Compose tasks.",
        "- A shared provider credential prevents independent per-harness billing ledgers; Codex’s provider rows also reported zero cost despite nonzero native token counts.",
        "- Seven verifier outcomes were recovered after Harbor artifact-collection stalls; the agent evidence was retained and the verifier was rerun in a fresh sandbox, but those rows are not identical to an uninterrupted single Harbor process.",
        "- The selected task declarations used 2 or 8 CPUs rather than a fixed 10-CPU override.",
        "- Harness-native transcript formats differ; normalized categories improve comparison but do not erase semantic differences in tools or prompts.",
        "- The output-claim detector is a heuristic and should not be read as a calibrated honesty classifier.",
        "- V1 and V2 use different models and task blocks, so cross-version deltas are not causal.",
        "",
        "The next rigorous replication should retain the V2 task list, use dedicated provider keys, run repeated trials per pair, and pre-register any change to the harness configuration or difficulty policy.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    report = load(REPORT)
    selection = load(SELECTION)
    v1 = load(V1_REPORT) if V1_REPORT.exists() else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(markdown(report["records"], selection, v1))
    print(str(OUT))


if __name__ == "__main__":
    main()
