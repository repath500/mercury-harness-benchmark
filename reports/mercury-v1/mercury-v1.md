# Mercury Harness Benchmark V1

Model: `inception/mercury-2.5-preview`  
Environment: E2B, one fresh single-container sandbox per trial  
Trials: 40/40 completed  

> Provider-side OpenRouter generation accounting is used where a generation ID was captured; remaining costs are estimates from the Mercury model catalog. The available OpenRouter key was shared, so billing could not be split into independent per-harness ledgers.

## Aggregate

| Harness | Solved | Total cost | Cost/solved | Tokens | Median agent time | Regressions | False completions |
|---|---:|---:|---:|---:|---:|---:|---:|
| critique-code | 8/10 | $0.236291 | $0.029536 | 5,584,876 | 1:29 | 0 | 2 |
| claude-code | 7/10 | $0.537726 | $0.076818 | 15,609,408 | 1:03 | 0 | 3 |
| oh-my-pi | 6/10 | $0.373359 | $0.062226 | 16,671,057 | 1:16 | 0 | 3 |
| opencode | 7/10 | $0.684547 | $0.097792 | 17,082,376 | 1:07 | 0 | 3 |

## Task results

| # | Task | Difficulty | Harness | Resolved | F2P | P2P | Agent time | Cost |
|---:|---|---|---|---|---:|---:|---:|---:|
| 1 | `huggingface__smolagents-783` | easy | critique-code | PASS | 1/1 | 206/206 | 1:50 | $0.010896 |
| 2 | `huggingface__smolagents-783` | easy | claude-code | PASS | 1/1 | 206/206 | 1:16 | $0.018094 |
| 3 | `huggingface__smolagents-783` | easy | oh-my-pi | PASS | 1/1 | 206/206 | 2:48 | $0.033772 |
| 4 | `huggingface__smolagents-783` | easy | opencode | PASS | 1/1 | 206/206 | 2:57 | $0.026171 |
| 5 | `encode__starlette-2806` | easy | claude-code | PASS | 1/1 | 435/435 | 0:45 | $0.017170 |
| 6 | `encode__starlette-2806` | easy | oh-my-pi | PASS | 1/1 | 435/435 | 0:49 | $0.009705 |
| 7 | `encode__starlette-2806` | easy | opencode | PASS | 1/1 | 435/435 | 0:40 | $0.016976 |
| 8 | `encode__starlette-2806` | easy | critique-code | PASS | 1/1 | 435/435 | 0:33 | $0.008740 |
| 9 | `jpadilla__pyjwt-913` | easy | oh-my-pi | PASS | 1/1 | 234/234 | 0:29 | $0.008853 |
| 10 | `jpadilla__pyjwt-913` | easy | opencode | PASS | 1/1 | 234/234 | 0:59 | $0.010310 |
| 11 | `jpadilla__pyjwt-913` | easy | critique-code | PASS | 1/1 | 234/234 | 2:08 | $0.019440 |
| 12 | `jpadilla__pyjwt-913` | easy | claude-code | PASS | 1/1 | 234/234 | 0:51 | $0.017417 |
| 13 | `tox-dev__tox-3288` | easy | opencode | PASS | 1/1 | 493/493 | 2:01 | $0.074478 |
| 14 | `tox-dev__tox-3288` | easy | critique-code | PASS | 1/1 | 493/493 | 1:22 | $0.021022 |
| 15 | `tox-dev__tox-3288` | easy | claude-code | PASS | 1/1 | 493/493 | 0:40 | $0.036366 |
| 16 | `tox-dev__tox-3288` | easy | oh-my-pi | PASS | 1/1 | 493/493 | 1:20 | $0.040183 |
| 17 | `dynaconf__dynaconf-1295` | easy | critique-code | PASS | 1/1 | 412/412 | 0:59 | $0.028864 |
| 18 | `dynaconf__dynaconf-1295` | easy | claude-code | PASS | 1/1 | 412/412 | 2:50 | $0.176238 |
| 19 | `dynaconf__dynaconf-1295` | easy | oh-my-pi | PASS | 1/1 | 412/412 | 1:10 | $0.041081 |
| 20 | `dynaconf__dynaconf-1295` | easy | opencode | PASS | 1/1 | 412/412 | 2:12 | $0.071244 |
| 21 | `stanfordnlp__dspy-7964` | hard | claude-code | PASS | 2/2 | 208/208 | 2:11 | $0.094155 |
| 22 | `stanfordnlp__dspy-7964` | hard | oh-my-pi | FAIL | 0/2 | 206/208 | 4:52 | $0.050109 |
| 23 | `stanfordnlp__dspy-7964` | hard | opencode | FAIL | 1/2 | 208/208 | 1:11 | $0.033666 |
| 24 | `stanfordnlp__dspy-7964` | hard | critique-code | PASS | 2/2 | 208/208 | 4:45 | $0.039653 |
| 25 | `projectmesa__mesa-2296` | hard | oh-my-pi | FAIL | 0/10 | 204/204 | 2:25 | $0.074696 |
| 26 | `projectmesa__mesa-2296` | hard | opencode | PASS | 10/10 | 204/204 | 1:03 | $0.050339 |
| 27 | `projectmesa__mesa-2296` | hard | critique-code | PASS | 10/10 | 204/204 | 1:36 | $0.029808 |
| 28 | `projectmesa__mesa-2296` | hard | claude-code | FAIL | 8/10 | 203/204 | 1:38 | $0.073249 |
| 29 | `openai__openai-agents-python-508` | hard | opencode | PASS | 29/29 | 186/186 | 0:38 | $0.015228 |
| 30 | `openai__openai-agents-python-508` | hard | critique-code | PASS | 29/29 | 186/186 | 0:14 | $0.006407 |
| 31 | `openai__openai-agents-python-508` | hard | claude-code | PASS | 29/29 | 186/186 | 0:43 | $0.026815 |
| 32 | `openai__openai-agents-python-508` | hard | oh-my-pi | PASS | 29/29 | 186/186 | 0:14 | $0.010205 |
| 33 | `aiogram__aiogram-1594` | hard | critique-code | FAIL | 1/3 | 717/717 | 1:45 | $0.032232 |
| 34 | `aiogram__aiogram-1594` | hard | claude-code | FAIL | 1/3 | 717/717 | 1:23 | $0.067293 |
| 35 | `aiogram__aiogram-1594` | hard | oh-my-pi | FAIL | 1/3 | 717/717 | 2:48 | $0.048244 |
| 36 | `aiogram__aiogram-1594` | hard | opencode | FAIL | 1/3 | 717/717 | 0:49 | $0.034304 |
| 37 | `huggingface__smolagents-1442` | hard | claude-code | FAIL | 0/7 | 320/321 | 0:18 | $0.010931 |
| 38 | `huggingface__smolagents-1442` | hard | oh-my-pi | FAIL | 5/7 | 320/321 | 1:11 | $0.056510 |
| 39 | `huggingface__smolagents-1442` | hard | opencode | FAIL | 4/7 | 303/321 | 3:25 | $0.351830 |
| 40 | `huggingface__smolagents-1442` | hard | critique-code | FAIL | 0/7 | 297/321 | 1:20 | $0.039229 |

## Run notes

- Oracle/reference validation passed for all 10 frozen tasks before agent trials.
- The aggregate uses 40 canonical records; raw Harbor contains 46 records because setup/validation retries were retained.
- Provider-side cost was reconciled for 19 trials; 21 use catalog estimates because no complete provider generation ledger was captured.
- Claude Code recorded 1 Mercury/OpenRouter compatibility API error; its external verifier still ran.

Raw Harbor trials remain under `benchmarks/mercury_v1/results/mercury-v1/trials/`; normalized per-trial artifacts are under `.../canonical/<task>/<harness>/`.
