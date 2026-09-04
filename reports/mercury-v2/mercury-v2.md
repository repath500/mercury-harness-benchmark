# Mercury Harness Benchmark V2

Model: `z-ai/glm-5.3-flash`  
Environment: E2B, one fresh single-container sandbox per trial  
Trials: 140/140 completed

Difficulty strata are pre-run study labels based on static FeatBench test and reference-patch surface; they are not official FeatBench difficulty labels.

## Aggregate

| Harness | Solved | Cost | Cost/solved | Tokens | Median agent time | Regressions | False completions |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pi (vanilla) | 19/20 | $0.662295 | $0.034858 | 17,242,501 | 7:59 | 0 | 0 |
| Oh My Pi | 20/20 | $1.237036 | $0.061852 | 37,057,409 | 8:39 | 0 | 0 |
| Claude Code | 19/20 | $1.236632 | $0.065086 | 30,286,765 | 6:38 | 0 | 1 |
| Codex | 15/20 | $0.000000 | $0.000000 | 20,647,847 | 5:18 | 0 | 5 |
| DeepSeek Harness | 20/20 | $1.033177 | $0.051659 | 3,409,985 | 8:41 | 0 | 0 |
| CritiqueCode | 13/20 | $0.065850 | $0.005065 | 663,906 | 2:24 | 1 | 7 |
| OpenCode | 18/20 | $1.638882 | $0.091049 | 21,644,211 | 5:25 | 0 | 2 |

## Task × harness results

| # | Task | Stratum | Harness | Resolved | F2P | P2P | Agent time | Cost |
|---:|---|---|---|---|---:|---:|---:|---:|
| 1 | `stanfordnlp__dspy-8247` | easy | Pi (vanilla) | PASS | 1/1 | 289/289 | 8:50 | $0.026996 |
| 2 | `stanfordnlp__dspy-8247` | easy | Oh My Pi | PASS | 1/1 | 289/289 | 8:16 | $0.025966 |
| 3 | `stanfordnlp__dspy-8247` | easy | Claude Code | PASS | 1/1 | 289/289 | 9:36 | $0.018688 |
| 4 | `stanfordnlp__dspy-8247` | easy | Codex | PASS | 1/1 | 289/289 | 6:00 | $0.000000 |
| 5 | `stanfordnlp__dspy-8247` | easy | DeepSeek Harness | PASS | 1/1 | 289/289 | 12:17 | $0.078741 |
| 6 | `stanfordnlp__dspy-8247` | easy | CritiqueCode | PASS | 1/1 | 289/289 | 1:17 | $0.001492 |
| 7 | `stanfordnlp__dspy-8247` | easy | OpenCode | PASS | 1/1 | 289/289 | 3:39 | $0.036734 |
| 8 | `stanfordnlp__dspy-8102` | easy | Oh My Pi | PASS | 1/1 | 234/234 | 9:39 | $0.024277 |
| 9 | `stanfordnlp__dspy-8102` | easy | Claude Code | PASS | 1/1 | 234/234 | 5:19 | $0.054044 |
| 10 | `stanfordnlp__dspy-8102` | easy | Codex | PASS | 1/1 | 234/234 | 2:12 | $0.000000 |
| 11 | `stanfordnlp__dspy-8102` | easy | DeepSeek Harness | PASS | 1/1 | 234/234 | 3:47 | $0.007289 |
| 12 | `stanfordnlp__dspy-8102` | easy | CritiqueCode | PASS | 1/1 | 234/234 | 1:21 | $0.001263 |
| 13 | `stanfordnlp__dspy-8102` | easy | OpenCode | PASS | 1/1 | 234/234 | 5:12 | $0.040112 |
| 14 | `stanfordnlp__dspy-8102` | easy | Pi (vanilla) | PASS | 1/1 | 234/234 | 6:02 | $0.018042 |
| 15 | `projectmesa__mesa-2502` | easy | Claude Code | PASS | 1/1 | 230/230 | 5:38 | $0.009876 |
| 16 | `projectmesa__mesa-2502` | easy | Codex | PASS | 1/1 | 230/230 | 2:36 | $0.000000 |
| 17 | `projectmesa__mesa-2502` | easy | DeepSeek Harness | PASS | 1/1 | 230/230 | 2:38 | $0.005662 |
| 18 | `projectmesa__mesa-2502` | easy | CritiqueCode | PASS | 1/1 | 230/230 | 0:44 | $0.001429 |
| 19 | `projectmesa__mesa-2502` | easy | OpenCode | PASS | 1/1 | 230/230 | 4:48 | $0.024904 |
| 20 | `projectmesa__mesa-2502` | easy | Pi (vanilla) | PASS | 1/1 | 230/230 | 1:52 | $0.004339 |
| 21 | `projectmesa__mesa-2502` | easy | Oh My Pi | PASS | 1/1 | 230/230 | 2:21 | $0.009622 |
| 22 | `projectmesa__mesa-2463` | easy | Codex | PASS | 1/1 | 247/247 | 7:08 | $0.000000 |
| 23 | `projectmesa__mesa-2463` | easy | DeepSeek Harness | PASS | 1/1 | 247/247 | 6:28 | $0.023697 |
| 24 | `projectmesa__mesa-2463` | easy | CritiqueCode | PASS | 1/1 | 247/247 | 3:10 | $0.002883 |
| 25 | `projectmesa__mesa-2463` | easy | OpenCode | PASS | 1/1 | 247/247 | 5:13 | $0.038341 |
| 26 | `projectmesa__mesa-2463` | easy | Pi (vanilla) | PASS | 1/1 | 247/247 | 16:43 | $0.051671 |
| 27 | `projectmesa__mesa-2463` | easy | Oh My Pi | PASS | 1/1 | 247/247 | 10:39 | $0.038898 |
| 28 | `projectmesa__mesa-2463` | easy | Claude Code | PASS | 1/1 | 247/247 | 6:57 | $0.110220 |
| 29 | `projectmesa__mesa-2253` | easy | DeepSeek Harness | PASS | 1/1 | 207/207 | 5:43 | $0.015459 |
| 30 | `projectmesa__mesa-2253` | easy | CritiqueCode | FAIL | 0/1 | 207/207 | 0:14 | $0.000466 |
| 31 | `projectmesa__mesa-2253` | easy | OpenCode | PASS | 1/1 | 207/207 | 7:24 | $0.070641 |
| 32 | `projectmesa__mesa-2253` | easy | Pi (vanilla) | FAIL | 0/1 | 207/207 | 4:45 | $0.016325 |
| 33 | `projectmesa__mesa-2253` | easy | Oh My Pi | PASS | 1/1 | 207/207 | 9:38 | $0.028506 |
| 34 | `projectmesa__mesa-2253` | easy | Claude Code | PASS | 1/1 | 207/207 | 7:20 | $0.073439 |
| 35 | `projectmesa__mesa-2253` | easy | Codex | FAIL | 0/1 | 207/207 | 3:46 | $0.000000 |
| 36 | `huggingface__smolagents-1302` | easy | CritiqueCode | FAIL | 0/1 | 223/223 | 1:34 | $0.002469 |
| 37 | `huggingface__smolagents-1302` | easy | OpenCode | FAIL | 0/1 | 223/223 | 2:04 | $0.012464 |
| 38 | `huggingface__smolagents-1302` | easy | Pi (vanilla) | PASS | 1/1 | 223/223 | 5:09 | $0.017075 |
| 39 | `huggingface__smolagents-1302` | easy | Oh My Pi | PASS | 1/1 | 223/223 | 4:25 | $0.015541 |
| 40 | `huggingface__smolagents-1302` | easy | Claude Code | PASS | 1/1 | 223/223 | 3:45 | $0.042129 |
| 41 | `huggingface__smolagents-1302` | easy | Codex | PASS | 1/1 | 223/223 | 3:51 | $0.000000 |
| 42 | `huggingface__smolagents-1302` | easy | DeepSeek Harness | PASS | 1/1 | 223/223 | 6:38 | $0.031411 |
| 43 | `huggingface__smolagents-1314` | easy | OpenCode | PASS | 1/1 | 225/225 | 4:48 | $0.041278 |
| 44 | `huggingface__smolagents-1314` | easy | Pi (vanilla) | PASS | 1/1 | 225/225 | 8:11 | $0.029797 |
| 45 | `huggingface__smolagents-1314` | easy | Oh My Pi | PASS | 1/1 | 225/225 | 5:19 | $0.040770 |
| 46 | `huggingface__smolagents-1314` | easy | Claude Code | FAIL | 0/1 | 225/225 | 0:56 | $0.012007 |
| 47 | `huggingface__smolagents-1314` | easy | Codex | PASS | 1/1 | 225/225 | 5:41 | $0.000000 |
| 48 | `huggingface__smolagents-1314` | easy | DeepSeek Harness | PASS | 1/1 | 225/225 | 3:15 | $0.046941 |
| 49 | `huggingface__smolagents-1314` | easy | CritiqueCode | FAIL | 1/1 | 223/225 | 2:47 | $0.003653 |
| 50 | `huggingface__smolagents-1104` | easy | Pi (vanilla) | PASS | 1/1 | 272/272 | 4:39 | $0.021646 |
| 51 | `huggingface__smolagents-1104` | easy | Oh My Pi | PASS | 1/1 | 272/272 | 8:36 | $0.049006 |
| 52 | `huggingface__smolagents-1104` | easy | Claude Code | PASS | 1/1 | 272/272 | 4:33 | $0.036867 |
| 53 | `huggingface__smolagents-1104` | easy | Codex | PASS | 1/1 | 272/272 | 2:01 | $0.000000 |
| 54 | `huggingface__smolagents-1104` | easy | DeepSeek Harness | PASS | 1/1 | 272/272 | 12:34 | $0.027551 |
| 55 | `huggingface__smolagents-1104` | easy | CritiqueCode | PASS | 1/1 | 272/272 | 2:20 | $0.001377 |
| 56 | `huggingface__smolagents-1104` | easy | OpenCode | FAIL | 0/1 | 0/272 | 1:44 | $0.015351 |
| 57 | `jpadilla__pyjwt-979` | easy | Oh My Pi | PASS | 1/1 | 241/241 | 7:05 | $0.020278 |
| 58 | `jpadilla__pyjwt-979` | easy | Claude Code | PASS | 1/1 | 241/241 | 6:06 | $0.016296 |
| 59 | `jpadilla__pyjwt-979` | easy | Codex | PASS | 1/1 | 241/241 | 4:55 | $0.000000 |
| 60 | `jpadilla__pyjwt-979` | easy | DeepSeek Harness | PASS | 1/1 | 241/241 | 4:34 | $0.022327 |
| 61 | `jpadilla__pyjwt-979` | easy | CritiqueCode | PASS | 1/1 | 241/241 | 2:28 | $0.003283 |
| 62 | `jpadilla__pyjwt-979` | easy | OpenCode | PASS | 1/1 | 241/241 | 6:06 | $0.103785 |
| 63 | `jpadilla__pyjwt-979` | easy | Pi (vanilla) | PASS | 1/1 | 241/241 | 4:54 | $0.014243 |
| 64 | `slackapi__bolt-python-1104` | easy | Claude Code | PASS | 2/2 | 111/111 | 9:07 | $0.099501 |
| 65 | `slackapi__bolt-python-1104` | easy | Codex | PASS | 2/2 | 111/111 | 3:53 | $0.000000 |
| 66 | `slackapi__bolt-python-1104` | easy | DeepSeek Harness | PASS | 2/2 | 111/111 | 9:28 | $0.030779 |
| 67 | `slackapi__bolt-python-1104` | easy | CritiqueCode | PASS | 2/2 | 111/111 | 1:18 | $0.001001 |
| 68 | `slackapi__bolt-python-1104` | easy | OpenCode | PASS | 2/2 | 111/111 | 7:53 | $0.064741 |
| 69 | `slackapi__bolt-python-1104` | easy | Pi (vanilla) | PASS | 2/2 | 111/111 | 12:19 | $0.033058 |
| 70 | `slackapi__bolt-python-1104` | easy | Oh My Pi | PASS | 2/2 | 111/111 | 12:42 | $0.103904 |
| 71 | `stanfordnlp__dspy-8139` | hard | Codex | PASS | 2/2 | 256/256 | 4:17 | $0.000000 |
| 72 | `stanfordnlp__dspy-8139` | hard | DeepSeek Harness | PASS | 2/2 | 256/256 | 12:53 | $0.069083 |
| 73 | `stanfordnlp__dspy-8139` | hard | CritiqueCode | PASS | 2/2 | 256/256 | 1:01 | $0.005466 |
| 74 | `stanfordnlp__dspy-8139` | hard | OpenCode | PASS | 2/2 | 256/256 | 4:17 | $0.058279 |
| 75 | `stanfordnlp__dspy-8139` | hard | Pi (vanilla) | PASS | 2/2 | 256/256 | 3:23 | $0.008770 |
| 76 | `stanfordnlp__dspy-8139` | hard | Oh My Pi | PASS | 2/2 | 256/256 | 9:13 | $0.036650 |
| 77 | `stanfordnlp__dspy-8139` | hard | Claude Code | PASS | 2/2 | 256/256 | 6:03 | $0.026431 |
| 78 | `stanfordnlp__dspy-7872` | hard | DeepSeek Harness | PASS | 4/4 | 196/196 | 4:13 | $0.053586 |
| 79 | `stanfordnlp__dspy-7872` | hard | CritiqueCode | PASS | 4/4 | 196/196 | 2:01 | $0.001855 |
| 80 | `stanfordnlp__dspy-7872` | hard | OpenCode | PASS | 4/4 | 196/196 | 4:08 | $0.050634 |
| 81 | `stanfordnlp__dspy-7872` | hard | Pi (vanilla) | PASS | 4/4 | 196/196 | 7:42 | $0.014078 |
| 82 | `stanfordnlp__dspy-7872` | hard | Oh My Pi | PASS | 4/4 | 196/196 | 8:08 | $0.040021 |
| 83 | `stanfordnlp__dspy-7872` | hard | Claude Code | PASS | 4/4 | 196/196 | 2:28 | $0.039643 |
| 84 | `stanfordnlp__dspy-7872` | hard | Codex | FAIL | 2/4 | 196/196 | 4:09 | $0.000000 |
| 85 | `openai__openai-agents-python-1198` | hard | CritiqueCode | PASS | 4/4 | 468/468 | 4:36 | $0.003914 |
| 86 | `openai__openai-agents-python-1198` | hard | OpenCode | PASS | 4/4 | 468/468 | 5:37 | $0.095248 |
| 87 | `openai__openai-agents-python-1198` | hard | Pi (vanilla) | PASS | 4/4 | 468/468 | 6:03 | $0.063454 |
| 88 | `openai__openai-agents-python-1198` | hard | Oh My Pi | PASS | 4/4 | 468/468 | 6:25 | $0.137537 |
| 89 | `openai__openai-agents-python-1198` | hard | Claude Code | PASS | 4/4 | 468/468 | 6:19 | $0.084516 |
| 90 | `openai__openai-agents-python-1198` | hard | Codex | FAIL | 0/4 | 468/468 | 2:26 | $0.000000 |
| 91 | `openai__openai-agents-python-1198` | hard | DeepSeek Harness | PASS | 4/4 | 468/468 | 7:58 | $0.026402 |
| 92 | `aiogram__aiogram-1670` | hard | OpenCode | PASS | 3/3 | 749/749 | 4:15 | $0.042258 |
| 93 | `aiogram__aiogram-1670` | hard | Pi (vanilla) | PASS | 3/3 | 749/749 | 17:50 | $0.029304 |
| 94 | `aiogram__aiogram-1670` | hard | Oh My Pi | PASS | 3/3 | 749/749 | 2:29 | $0.092195 |
| 95 | `aiogram__aiogram-1670` | hard | Claude Code | PASS | 3/3 | 749/749 | 3:57 | $0.065591 |
| 96 | `aiogram__aiogram-1670` | hard | Codex | FAIL | 0/3 | 749/749 | 5:56 | $0.000000 |
| 97 | `aiogram__aiogram-1670` | hard | DeepSeek Harness | PASS | 3/3 | 749/749 | 16:57 | $0.065130 |
| 98 | `aiogram__aiogram-1670` | hard | CritiqueCode | FAIL | 1/3 | 749/749 | 1:26 | $0.002232 |
| 99 | `iterative__dvc-10754` | hard | Pi (vanilla) | PASS | 3/3 | 1794/1794 | 13:19 | $0.100538 |
| 100 | `iterative__dvc-10754` | hard | Oh My Pi | PASS | 3/3 | 1794/1794 | 16:14 | $0.106136 |
| 101 | `iterative__dvc-10754` | hard | Claude Code | PASS | 3/3 | 1794/1794 | 14:16 | $0.114612 |
| 102 | `iterative__dvc-10754` | hard | Codex | PASS | 3/3 | 1794/1794 | 9:04 | $0.000000 |
| 103 | `iterative__dvc-10754` | hard | DeepSeek Harness | PASS | 3/3 | 1794/1794 | 29:00 | $0.158354 |
| 104 | `iterative__dvc-10754` | hard | CritiqueCode | PASS | 3/3 | 1794/1794 | 19:16 | $0.007600 |
| 105 | `iterative__dvc-10754` | hard | OpenCode | PASS | 3/3 | 1794/1794 | 9:15 | $0.123429 |
| 106 | `openai__openai-agents-python-1080` | very-hard | Oh My Pi | PASS | 10/10 | 380/380 | 6:53 | $0.041523 |
| 107 | `openai__openai-agents-python-1080` | very-hard | Claude Code | PASS | 10/10 | 380/380 | 17:14 | $0.031832 |
| 108 | `openai__openai-agents-python-1080` | very-hard | Codex | PASS | 10/10 | 380/380 | 6:15 | $0.000000 |
| 109 | `openai__openai-agents-python-1080` | very-hard | DeepSeek Harness | PASS | 10/10 | 380/380 | 10:36 | $0.087671 |
| 110 | `openai__openai-agents-python-1080` | very-hard | CritiqueCode | PASS | 10/10 | 380/380 | 4:15 | $0.007671 |
| 111 | `openai__openai-agents-python-1080` | very-hard | OpenCode | PASS | 10/10 | 380/380 | 8:31 | $0.071638 |
| 112 | `openai__openai-agents-python-1080` | very-hard | Pi (vanilla) | PASS | 10/10 | 380/380 | 7:48 | $0.009850 |
| 113 | `openai__openai-agents-python-842` | very-hard | Claude Code | PASS | 8/8 | 331/331 | 8:22 | $0.134904 |
| 114 | `openai__openai-agents-python-842` | very-hard | Codex | PASS | 8/8 | 331/331 | 14:48 | $0.000000 |
| 115 | `openai__openai-agents-python-842` | very-hard | DeepSeek Harness | PASS | 8/8 | 331/331 | 4:31 | $0.106554 |
| 116 | `openai__openai-agents-python-842` | very-hard | CritiqueCode | PASS | 8/8 | 331/331 | 4:35 | $0.004198 |
| 117 | `openai__openai-agents-python-842` | very-hard | OpenCode | PASS | 8/8 | 331/331 | 7:51 | $0.083490 |
| 118 | `openai__openai-agents-python-842` | very-hard | Pi (vanilla) | PASS | 8/8 | 331/331 | 12:37 | $0.039384 |
| 119 | `openai__openai-agents-python-842` | very-hard | Oh My Pi | PASS | 8/8 | 331/331 | 14:46 | $0.054561 |
| 120 | `jpadilla__pyjwt-886` | very-hard | Codex | PASS | 12/12 | 226/226 | 6:19 | $0.000000 |
| 121 | `jpadilla__pyjwt-886` | very-hard | DeepSeek Harness | PASS | 12/12 | 226/226 | 19:32 | $0.098143 |
| 122 | `jpadilla__pyjwt-886` | very-hard | CritiqueCode | FAIL | 9/12 | 226/226 | 3:22 | $0.001814 |
| 123 | `jpadilla__pyjwt-886` | very-hard | OpenCode | PASS | 12/12 | 226/226 | 9:26 | $0.206631 |
| 124 | `jpadilla__pyjwt-886` | very-hard | Pi (vanilla) | PASS | 12/12 | 226/226 | 16:33 | $0.088551 |
| 125 | `jpadilla__pyjwt-886` | very-hard | Oh My Pi | PASS | 12/12 | 226/226 | 12:41 | $0.065092 |
| 126 | `jpadilla__pyjwt-886` | very-hard | Claude Code | PASS | 12/12 | 226/226 | 12:15 | $0.084415 |
| 127 | `reflex-dev__reflex-5583` | very-hard | DeepSeek Harness | PASS | 6/6 | 0/0 | 9:24 | $0.023577 |
| 128 | `reflex-dev__reflex-5583` | very-hard | CritiqueCode | FAIL | 0/6 | 0/0 | 8:40 | $0.004223 |
| 129 | `reflex-dev__reflex-5583` | very-hard | OpenCode | PASS | 6/6 | 0/0 | 10:40 | $0.209738 |
| 130 | `reflex-dev__reflex-5583` | very-hard | Pi (vanilla) | PASS | 6/6 | 0/0 | 12:27 | $0.037042 |
| 131 | `reflex-dev__reflex-5583` | very-hard | Oh My Pi | PASS | 6/6 | 0/0 | 8:42 | $0.181785 |
| 132 | `reflex-dev__reflex-5583` | very-hard | Claude Code | PASS | 6/6 | 0/0 | 11:42 | $0.039444 |
| 133 | `reflex-dev__reflex-5583` | very-hard | Codex | FAIL | 0/6 | 0/0 | 30:46 | $0.000000 |
| 134 | `conan-io__conan-18493` | very-hard | CritiqueCode | FAIL | 0/8 | 3301/3301 | 9:24 | $0.007560 |
| 135 | `conan-io__conan-18493` | very-hard | OpenCode | PASS | 8/8 | 3301/3301 | 9:12 | $0.249186 |
| 136 | `conan-io__conan-18493` | very-hard | Pi (vanilla) | PASS | 8/8 | 3301/3301 | 9:56 | $0.038134 |
| 137 | `conan-io__conan-18493` | very-hard | Oh My Pi | PASS | 8/8 | 3301/3301 | 12:56 | $0.124769 |
| 138 | `conan-io__conan-18493` | very-hard | Claude Code | PASS | 8/8 | 3301/3301 | 17:16 | $0.142176 |
| 139 | `conan-io__conan-18493` | very-hard | Codex | PASS | 8/8 | 3301/3301 | 6:08 | $0.000000 |
| 140 | `conan-io__conan-18493` | very-hard | DeepSeek Harness | PASS | 8/8 | 3301/3301 | 14:48 | $0.054821 |

## Added V2 measurements

The canonical records add first model/tool latency, active-time share, context growth, tool efficiency, test-run counts, verifier-suite gap, output claims, artifact bytes, and provider-ledger completeness. Native transcripts and Harbor ATIF trajectories remain in each canonical trial directory.
