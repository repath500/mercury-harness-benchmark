# Notices and provenance

This repository contains original benchmark orchestration, normalization,
study prose, and derived aggregate data, plus copied or derived materials from
other projects. The notices below describe the intended boundaries.

## FeatBench task materials

The ten task directories under `benchmarks/mercury_v1/tasks/featbench/` are
generated from the PGCodeLLM/FeatBench dataset and include repository code,
tests, task instructions, and reference solutions. Their upstream repository
licenses and attribution requirements remain applicable. They are included so
the oracle gate and benchmark can be audited and reproduced.

## Harbor and E2B

The benchmark invokes Harbor and the E2B SDK as external dependencies. The
small `patches/harbor-e2b-v1.patch` file is an auditable local patch against
the Harbor source checkout; it does not relicense Harbor.

## CritiqueCode runtime

`e2b-templates/critique-pi-v1/` contains the runtime files used by the
CritiqueCode adapter in the source workspace. Preserve any upstream notices
that apply to those files. The support change is also recorded as
`patches/critique-code-positive-budget.patch`.

## Lieflat Charts

The visual companion is published separately in the
[`repath500/lieflat-charts`](https://github.com/repath500/lieflat-charts) fork,
derived from [`larashero3-dotcom/lieflat-charts`](https://github.com/larashero3-dotcom/lieflat-charts).
That repository remains under its upstream PolyForm Noncommercial License.
The benchmark repository does not relicense Lieflat Charts.
