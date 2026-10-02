# Artifact reproduction commands

Command, input path and output path only. All commands run from the repository root unless the command itself changes directory. `<REPO>` is the repository root; `<LEGACY_REPO>`, `<GPU_VENV>`, `<GPU_HOME>`, `<HF_HOME>` stand for machine-specific locations. Rows under sections 3 and 4 were extracted mechanically from the per-TASK documents (sections "실험 또는 검증 방법" and "재현 정보"); shell variables defined in the same code block are substituted. They were not re-executed for this list. Measurement drivers (`run_*.sh`) need the RBLN device and compiled model artifacts under `models/` (not in the repository).

## 1. Aggregated tables (`results/tables/`)

Source: `results/tables/README.md`. Inputs are untracked analysis outputs under `results/npu/stage2/`; prerequisite commands first.

| command | input paths | output paths |
|---|---|---|
| `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| `env -u PYTHONPATH python3 experiments/npu/analysis/padding_ratio.py --output results/npu/stage2/padding_ratio.json` |  | `results/npu/stage2/padding_ratio.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/padding_decompose.py --output results/npu/stage2/padding_decompose.json` |  | `results/npu/stage2/padding_decompose.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py --output results/npu/stage2/layer_audit.json` |  | `results/npu/stage2/layer_audit.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py --json results/npu/stage2/reuse_cost.json` |  | `results/npu/stage2/reuse_cost.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py --run results/npu/stage2/20260908-133635-grid-paired --output results/npu/stage2/20260908-133635-grid-paired/grid_paired.json` | `results/npu/stage2/20260908-133635-grid-paired` | `results/npu/stage2/20260908-133635-grid-paired/grid_paired.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py --run results/npu/stage2/20260908-151119-step-cost --task54-run results/npu/stage2/20260908-133635-grid-paired --output results/npu/stage2/20260908-151119-step-cost/grid_step_cost.json` | `results/npu/stage2/20260908-151119-step-cost`<br>`results/npu/stage2/20260908-133635-grid-paired` | `results/npu/stage2/20260908-151119-step-cost/grid_step_cost.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/prefill_tax.py --input-dir results/npu/stage2/20260821-220100-prefill-tax/probe --spike-factor 5.0 --output results/npu/stage2/20260821-220100-prefill-tax/prefill_tax_result.json` | `results/npu/stage2/20260821-220100-prefill-tax/probe` | `results/npu/stage2/20260821-220100-prefill-tax/prefill_tax_result.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py --run results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/config_device.json` | `results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/config_device.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py --run results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/config_device.n6.json` | `results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/config_device.n6.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/batch_curve.py --run results/npu/stage2/20260824-222453-batch-saturation --output results/npu/stage2/20260824-222453-batch-saturation/batch_curve.json` | `results/npu/stage2/20260824-222453-batch-saturation` | `results/npu/stage2/20260824-222453-batch-saturation/batch_curve.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/null_channel.py --run results/npu/stage2/20260901-020342-null-channel --sessions 6,8 --output results/npu/stage2/20260901-020342-null-channel/null_channel.json` | `results/npu/stage2/20260901-020342-null-channel` | `results/npu/stage2/20260901-020342-null-channel/null_channel.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/recompile_variance.py analyze --run results/npu/stage2/20260911-191300-recompile-variance --output results/npu/stage2/20260911-191300-recompile-variance/recompile_variance.json` | `results/npu/stage2/20260911-191300-recompile-variance` | `results/npu/stage2/20260911-191300-recompile-variance/recompile_variance.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py analyze --run results/npu/stage2/20260912-134732-dummy-lifecycle --output results/npu/stage2/20260912-134732-dummy-lifecycle/dummy_lifecycle.json` | `results/npu/stage2/20260912-134732-dummy-lifecycle` | `results/npu/stage2/20260912-134732-dummy-lifecycle/dummy_lifecycle.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config --run results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/per_repetition.json` | `results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/per_repetition.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config --run results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/per_repetition.json` | `results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/per_repetition.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode saturation --run results/npu/stage2/20260824-222453-batch-saturation --baseline B8 --arms B16,B24,B32 --sessions 6,8,10 --output results/npu/stage2/20260824-222453-batch-saturation/per_repetition.json` | `results/npu/stage2/20260824-222453-batch-saturation` | `results/npu/stage2/20260824-222453-batch-saturation/per_repetition.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py --run results/npu/stage2/20260823-183505-final-confirm --fix-arrivals results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/arrival_feedback.json` | `results/npu/stage2/20260823-183505-final-confirm`<br>`results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/arrival_feedback.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py --run results/npu/stage2/20260824-160028-n6-reconfirm --fix-arrivals results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/arrival_feedback.json` | `results/npu/stage2/20260824-160028-n6-reconfirm`<br>`results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/arrival_feedback.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py --run results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/dummy_block_effect.json` | `results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/dummy_block_effect.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py --run results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/dummy_block_effect.json` | `results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/dummy_block_effect.json` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py --sessions 6,8,10 --weight sum-seconds --top 20 --dummy-block --output-dir results/npu/stage2/20260922-dummy-block/search-on` |  | `results/npu/stage2/20260922-dummy-block/search-on` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py --sessions "$S" --weight "$W" --top 20 --output-dir results/npu/stage2/20260922-config-search-sensitivity/"${W}_$(echo $S \| tr , _)"` |  | `results/npu/stage2/20260922-config-search-sensitivity/${W}_$(echo $S \| tr , _)` |
| `env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all` |  |  |

Per-table: `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --table <ID>` writes `results/tables/<ID>.md` and `results/tables/<ID>.csv`; `--all` also writes `results/tables/manifest.json`. Paper tables: `env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --table <PID>` / `--all` writes `results/tables/<PID>.md`, `results/tables/<PID>.csv` and `results/tables/figures/F_*.csv`.

## 2. Paper figures and package

| command | input paths | output paths |
|---|---|---|
| `env -u PYTHONPATH python3 paper/figures/make_figures.py` | values embedded in the script; provenance in `paper/figures/SOURCES.md` | `paper/figures/*.svg`, `paper/figures/en/*.svg`, `paper/figures/pdf/*.pdf` |
| `env -u PYTHONPATH python3 paper/figures/verify_figures.py` | `paper/figures/*.svg`, `paper/figures/en/*.svg`, `paper/figures/pdf/*.pdf` | stdout; `paper/figures/INSPECTION.md` is its recorded output |
| `env -u PYTHONPATH python3 paper/draft/make_table_3_1.py --write` | values embedded in the script | `paper/draft/table_3_1.md`, `paper/draft/table_3_1.tex` |
| `python3 paper/latex/md2tex.py` | `paper/draft/[0-9]*.md` (not in the repository) | `paper/latex/sections/` |
| `python3 paper/draft/check_claims.py` | `paper/CLAIMS.md`, `paper/draft/[0-9]*.md` (not in the repository) | stdout |
| `bash paper/latex/make_package.sh` | `paper/figures/pdf/*.pdf`, `paper/latex/main.tex` (not in the repository), `paper/latex/refs.bib` | `paper/latex/figures/` |

## 3. Per-TASK commands (NPU, `docs/research/TASK*.md`)

| source | command | input paths | output paths |
|---|---|---|---|
| TASK02 | `experiments/npu/launch/run_isolated_python.sh experiments/npu/probes/runtime_probe.py --output-dir results/npu/stage0/20260818-184144-blocked-model-artifact` |  | `experiments/npu/probes/runtime_probe.py`<br>`results/npu/stage0/20260818-184144-blocked-model-artifact` |
| TASK06 | `experiments/npu/launch/run_isolated_python.sh experiments/npu/probes/runtime_probe.py --output-dir <RUN>/probe` |  | `experiments/npu/probes/runtime_probe.py`<br>`<RUN>/probe` |
| TASK06 | `experiments/npu/launch/run_isolated_python.sh experiments/npu/stage0/download_model.py --model-id Qwen/Qwen3-4B --output-dir <RUN>/download` | `Qwen/Qwen3-4B` | `experiments/npu/stage0/download_model.py`<br>`<RUN>/download` |
| TASK06 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage0/single_inference.py --model-dir models/Qwen3-4B-rbln-b1-s8192-d4 --prompt-file experiments/npu/stage0/prompt.txt --max-tokens 64 --seed 20260819 --output-dir <RUN>/inference` | `models/Qwen3-4B-rbln-b1-s8192-d4`<br>`experiments/npu/stage0/prompt.txt` | `experiments/npu/stage0/single_inference.py`<br>`<RUN>/inference` |
| TASK09 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage1/serving_probe.py --base-url http://127.0.0.1:8000 --prompt-file experiments/npu/stage1/prompt.txt --max-tokens 32 --seed 20260819 --concurrency 2 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage1/prompt.txt` | `experiments/npu/stage1/serving_probe.py`<br>`<RUN>/probe` |
| TASK10 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage1/concurrency_probe.py --base-url http://127.0.0.1:8000 --prompt-file experiments/npu/stage1/prompt.txt --max-tokens 256 --seed 20260819 --levels 1,2,4,8 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage1/prompt.txt` | `experiments/npu/stage1/concurrency_probe.py`<br>`<RUN>/probe` |
| TASK11 | `env -u PYTHONPATH python3 experiments/npu/stage2/build_prompts.py --tokenizer-dir models/Qwen3-4B-rbln-b8-s8192-d4-mb --targets 100,130,260,1000,4000 --suffix-tokens 8 --suffix-variants 5 --output experiments/npu/stage2/prefix_prompts.json` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` | `experiments/npu/stage2/prefix_prompts.json` |
| TASK11 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage2/prefix_cache_probe.py --base-url http://127.0.0.1:8000 --prompts-file experiments/npu/stage2/prefix_prompts.json --lengths 100,130,260,1000,4000 --repeats 5 --max-tokens 8 --seed 20260819 --tag apc_on --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage2/prefix_prompts.json` | `experiments/npu/stage2/prefix_cache_probe.py`<br>`<RUN>/probe` |
| TASK12 | `bash patches/vllm_rbln-0.11.1/apply.sh status` |  |  |
| TASK12 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage1/concurrency_probe.py --base-url http://127.0.0.1:8000 --prompt-file experiments/npu/stage1/prompt.txt --max-tokens 128 --seed 20260819 --levels 1,2,3,5,8 --output-dir <RUN>/probe-run{A,B}` | `http://127.0.0.1:8000`<br>`experiments/npu/stage1/prompt.txt` | `experiments/npu/stage1/concurrency_probe.py`<br>`<RUN>/probe-run{A,B}` |
| TASK12 | `sudo bash patches/vllm_rbln-0.11.1/apply.sh apply` |  |  |
| TASK12 | `sudo bash patches/vllm_rbln-0.11.1/apply.sh revert` |  |  |
| TASK13 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage2/decode_cost_probe.py --base-url http://127.0.0.1:8000 --prompt-file experiments/npu/stage1/prompt.txt --level <N> --max-tokens 512 --seed 20260819 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage1/prompt.txt` | `experiments/npu/stage2/decode_cost_probe.py`<br>`<RUN>/probe` |
| TASK13 | `env -u PYTHONPATH python3 experiments/npu/analysis/bootstrap_ratio.py --input-dir <RUN>/probe --base-seed 20260819 --resamples 2000 --ci-width-max 0.10 --pairs 3:4,5:6,5:7,5:8,6:7,6:8,7:8,1:2,2:3,4:5 --output <RUN>/bootstrap.json` | `<RUN>/probe` | `<RUN>/bootstrap.json` |
| TASK14 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage2/gap_turnover_probe.py --base-url http://127.0.0.1:8000 --prompts-file experiments/npu/stage2/gap_prompts.json --trial <K> --max-tokens 8 --seed 20260819 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage2/gap_prompts.json` | `experiments/npu/stage2/gap_turnover_probe.py`<br>`<RUN>/probe` |
| TASK15 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage2/gap_turnover_probe.py --base-url http://127.0.0.1:8000 --prompts-file experiments/npu/stage2/cliff_prompts.json --trial <K> --max-tokens 8 --seed 20260819 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`experiments/npu/stage2/cliff_prompts.json` | `experiments/npu/stage2/gap_turnover_probe.py`<br>`<RUN>/probe` |
| TASK16 | `env -u PYTHONPATH python3 experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py` |  |  |
| TASK18 | `env -u PYTHONPATH experiments/npu/launch/run_isolated_python.sh experiments/npu/stage2/session_runner.py --base-url http://127.0.0.1:8000 --tokenizer-dir models/Qwen3-4B-rbln-b8-s8192-d4-mb --arm gate --sessions 8 --turns 2 --first-segment ladder:300:300 --later-segment fixed:8 --generation fixed:32 --gap fixed:2 --base-seed 20260822 --block-id g0 --sampling-seed 20260819 --output-dir <RUN>/probe` | `http://127.0.0.1:8000`<br>`models/Qwen3-4B-rbln-b8-s8192-d4-mb`<br>`fixed:2` | `experiments/npu/stage2/session_runner.py`<br>`<RUN>/probe` |
| TASK18 | `env -u PYTHONPATH python3 experiments/npu/analysis/join_check.py --rows <RUN>/probe/requests.gate.g0.jsonl --server-log <RUN>/server.log --metrics-dump <RUN>/metrics-final.prom --output <RUN>/join_check.json` | `<RUN>/probe/requests.gate.g0.jsonl`<br>`<RUN>/server.log`<br>`<RUN>/metrics-final.prom` | `<RUN>/join_check.json` |
| TASK23 | `SWEEP_BASE_SEED=20260841 bash experiments/npu/stage2/run_sweep.sh <RUN2a> <ARM> <3\|5\|7\|8> <B> <none\|zero>` |  | `<RUN2a>` |
| TASK23 | `SWEEP_BASE_SEED=20260842 SWEEP_ARTIFACT=$PWD/models/Qwen3-4B-rbln-b8-s8192-d4-mb6 bash experiments/npu/stage2/run_sweep.sh <RUN2b> <ARM> <6\|8> <B> <none\|zero>` |  | `<RUN2b>` |
| TASK24 | `python3 experiments/npu/analysis/sim_compare.py --run results/npu/stage2/20260820-165200-nslots-sweep --labels AGENTIC.n6.b0,CONVENTIONAL.n6.b0` | `results/npu/stage2/20260820-165200-nslots-sweep` |  |
| TASK25 | `SWEEP_BASE_SEED=20260850 bash experiments/npu/stage2/run_sweep.sh <RUN> <ARM> <3\|4\|7> <3\|4\|5> <none\|zero>` |  | `<RUN>` |
| TASK25 | `python3 experiments/npu/analysis/oos_gate.py --run <RUN> --prediction <선등록 예측 JSON> --new-blocks 3,4,5 --tolerance 0.05 --prior 3:<TASK23 run>:0,1,2 --prior 4:<TASK20 run>:0,1,2 --prior 7:<TASK23 run>:0,1,2` | `<RUN>` |  |
| TASK27 | `python3 experiments/npu/analysis/policy_eval.py --run results/npu/stage2/20260820-165200-nslots-sweep --cells 6:0,1,2 8:0,1,2 10:0,1,2 12:0,1,2 --budgets 0.5,1,2,5 --policies quantize:0.25,quantize:0.5,quantize:1,quantize:2,topup,freeslot --oracle` | `results/npu/stage2/20260820-165200-nslots-sweep` |  |
| TASK28 | `SWEEP_BASE_SEED=20260860 SWEEP_POLICY=freeslot SWEEP_BUDGET=1.0 bash experiments/npu/stage2/run_sweep.sh <RUN> FREESLOT <N> <B> none` |  | `<RUN>` |
| TASK28 | `SWEEP_BASE_SEED=20260860 bash experiments/npu/stage2/run_sweep.sh <RUN> IMMEDIATE <N> <B> none` |  | `<RUN>` |
| TASK28 | `python3 experiments/npu/analysis/policy_device.py --run <RUN> --cells 6:6,7,8 8:6,7,8 10:6,7,8` | `<RUN>` |  |
| TASK36 | `env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py --run <RUN> --sessions 6 --output <RUN>/config_device.n6.json` | `<RUN>` | `<RUN>/config_device.n6.json` |
| TASK37 | `env -u PYTHONPATH python3 paper/figures/make_figures.py` |  |  |
| TASK38 | `env -u PYTHONPATH python3 paper/figures/verify_figures.py` |  |  |
| TASK38 | `env -u PYTHONPATH python3 paper/figures/make_figures.py` |  |  |
| TASK39 | `env -u PYTHONPATH python3 paper/figures/make_figures.py` |  |  |
| TASK39 | `env -u PYTHONPATH python3 paper/figures/verify_figures.py` |  |  |
| TASK40 | `env -u PYTHONPATH python3 experiments/npu/analysis/batch_curve.py --run <RUN> --output <RUN>/batch_curve.json` | `<RUN>` | `<RUN>/batch_curve.json` |
| TASK41 | `env -u PYTHONPATH python3 paper/figures/make_figures.py` |  |  |
| TASK41 | `env -u PYTHONPATH python3 paper/figures/verify_figures.py` |  |  |
| TASK41 | `env -u PYTHONPATH python3 paper/draft/check_claims.py` |  |  |
| TASK41 | `env -u PYTHONPATH python3 paper/latex/md2tex.py` |  |  |
| TASK41 | `bash paper/latex/make_package.sh` |  |  |
| TASK42 | `env -u PYTHONPATH python3 paper/latex/md2tex.py` |  |  |
| TASK42 | `env -u PYTHONPATH python3 paper/draft/check_claims.py` |  |  |
| TASK42 | `env -u PYTHONPATH python3 paper/figures/verify_figures.py` |  |  |
| TASK42 | `bash paper/latex/make_package.sh` |  |  |
| TASK43 | `env -u PYTHONPATH python3 paper/draft/check_claims.py` |  |  |
| TASK43 | `env -u PYTHONPATH python3 paper/figures/verify_figures.py` |  |  |
| TASK44 | `env -u PYTHONPATH python3 paper/latex/md2tex.py` |  |  |
| TASK44 | `env -u PYTHONPATH python3 paper/draft/check_claims.py` |  |  |
| TASK45 | `env -u PYTHONPATH python3 paper/figures/make_figures.py` |  |  |
| TASK45 | `env -u PYTHONPATH python3 paper/latex/md2tex.py` |  |  |
| TASK45 | `bash paper/latex/make_package.sh` |  |  |
| TASK46 | `env -u PYTHONPATH python3 experiments/npu/analysis/tail_latency.py --run <RUN> --arms BASE,TUNED --sessions 6,8,10` | `<RUN>` |  |
| TASK46 | `bash paper/latex/make_package.sh` |  |  |
| TASK49 | `env -u PYTHONPATH python3 experiments/npu/analysis/channel_tolerance_sensitivity.py --output results/npu/stage2/channel_tolerance_sensitivity.json` |  | `results/npu/stage2/channel_tolerance_sensitivity.json` |
| TASK50 | `env -u PYTHONPATH python3 experiments/npu/analysis/null_channel.py --run <RUN> --sessions 6,8 --output <RUN>/null_channel.json` | `<RUN>` | `<RUN>/null_channel.json` |
| TASK50 | `env -u PYTHONPATH python3 experiments/npu/analysis/null_channel_posthoc.py --run <RUN> --output <RUN>/null_channel_posthoc.json` | `<RUN>` | `<RUN>/null_channel_posthoc.json` |
| TASK52 | `env -u PYTHONPATH python3 experiments/npu/analysis/padding_ratio.py --output results/npu/stage2/padding_ratio.json` |  | `results/npu/stage2/padding_ratio.json` |
| TASK53 | `env -u PYTHONPATH python3 paper/draft/make_table_3_1.py --write` |  |  |
| TASK54 | `bash experiments/npu/stage2/run_grid_paired.sh "results/npu/stage2/20260908-133635-grid-paired"` |  | `results/npu/stage2/20260908-133635-grid-paired` |
| TASK54 | `env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py --run "results/npu/stage2/20260908-133635-grid-paired" --output "results/npu/stage2/20260908-133635-grid-paired/grid_paired.json"` | `results/npu/stage2/20260908-133635-grid-paired` | `results/npu/stage2/20260908-133635-grid-paired/grid_paired.json` |
| TASK54 | `bash experiments/npu/stage2/run_grid_paired.sh <RUN>` |  | `<RUN>` |
| TASK54 | `env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py --run <RUN> --output <RUN>/grid_paired.json` | `<RUN>` | `<RUN>/grid_paired.json` |
| TASK55 | `bash experiments/npu/stage2/run_step_cost.sh "results/npu/stage2/20260908-151119-step-cost"` |  | `results/npu/stage2/20260908-151119-step-cost` |
| TASK55 | `env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py --run "results/npu/stage2/20260908-151119-step-cost" --task54-run results/npu/stage2/20260908-133635-grid-paired --output "results/npu/stage2/20260908-151119-step-cost/grid_step_cost.json"` | `results/npu/stage2/20260908-151119-step-cost`<br>`results/npu/stage2/20260908-133635-grid-paired` | `results/npu/stage2/20260908-151119-step-cost/grid_step_cost.json` |
| TASK55 | `bash experiments/npu/stage2/run_step_cost.sh <RUN>` |  | `<RUN>` |
| TASK55 | `env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py --run <RUN> --task54-run <T54RUN> --output <RUN>/grid_step_cost.json` | `<RUN>`<br>`<T54RUN>` | `<RUN>/grid_step_cost.json` |
| TASK56 | `env -u PYTHONPATH python3 experiments/npu/analysis/padding_decompose.py --output results/npu/stage2/padding_decompose.json` |  | `results/npu/stage2/padding_decompose.json` |
| TASK58 | `env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py --output results/npu/stage2/layer_audit.json` |  | `results/npu/stage2/layer_audit.json` |
| TASK59 | `env -u PYTHONPATH python3 experiments/npu/analysis/observation_audit.py --output results/npu/stage2/observation_audit.json` |  | `results/npu/stage2/observation_audit.json` |
| TASK61 | `PYTHONHASHSEED=0 python3 experiments/npu/analysis/config_search_rerun.py --output-dir <RUN>/run-a` |  | `<RUN>/run-a` |
| TASK61 | `PYTHONHASHSEED=1 python3 experiments/npu/analysis/config_search_rerun.py --output-dir <RUN>/run-b` |  | `<RUN>/run-b` |
| TASK61 | `python3 experiments/npu/analysis/config_search.py --max-buckets 5 --output <RUN>/committed-mb5.json` |  | `<RUN>/committed-mb5.json` |
| TASK61 | `python3 experiments/npu/analysis/config_search.py --output <RUN>/committed-default.json` |  | `<RUN>/committed-default.json` |
| TASK62 | `bash experiments/npu/stage2/compile_recompile_a3.sh "results/npu/stage2/20260911-191300-recompile-variance"` |  | `results/npu/stage2/20260911-191300-recompile-variance` |
| TASK62 | `bash experiments/npu/stage2/run_recompile_variance.sh "results/npu/stage2/20260911-191300-recompile-variance"` |  | `results/npu/stage2/20260911-191300-recompile-variance` |
| TASK62 | `env -u PYTHONPATH python3 experiments/npu/analysis/recompile_variance.py analyze --run "results/npu/stage2/20260911-191300-recompile-variance" --output "results/npu/stage2/20260911-191300-recompile-variance/recompile_variance.json"` | `results/npu/stage2/20260911-191300-recompile-variance` | `results/npu/stage2/20260911-191300-recompile-variance/recompile_variance.json` |
| TASK63 | `bash experiments/npu/stage2/run_dummy_lifecycle.sh "results/npu/stage2/20260912-134732-dummy-lifecycle" pilot` |  | `results/npu/stage2/20260912-134732-dummy-lifecycle` |
| TASK63 | `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py pilot --run "results/npu/stage2/20260912-134732-dummy-lifecycle"` | `results/npu/stage2/20260912-134732-dummy-lifecycle` |  |
| TASK63 | `bash experiments/npu/stage2/run_dummy_lifecycle.sh "results/npu/stage2/20260912-134732-dummy-lifecycle" main` |  | `results/npu/stage2/20260912-134732-dummy-lifecycle` |
| TASK63 | `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py analyze --run "results/npu/stage2/20260912-134732-dummy-lifecycle" --output "results/npu/stage2/20260912-134732-dummy-lifecycle/dummy_lifecycle.json"` | `results/npu/stage2/20260912-134732-dummy-lifecycle` | `results/npu/stage2/20260912-134732-dummy-lifecycle/dummy_lifecycle.json` |
| TASK63 | `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert` |  |  |
| TASK64 | `bash experiments/npu/stage2/run_admission_eviction.sh "results/npu/stage2/20260912-144017-admission-eviction"` |  | `results/npu/stage2/20260912-144017-admission-eviction` |
| TASK64 | `env -u PYTHONPATH python3 experiments/npu/analysis/admission_eviction.py analyze --run "results/npu/stage2/20260912-144017-admission-eviction" --output "results/npu/stage2/20260912-144017-admission-eviction/admission_eviction.json"` | `results/npu/stage2/20260912-144017-admission-eviction` | `results/npu/stage2/20260912-144017-admission-eviction/admission_eviction.json` |
| TASK64 | `sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert` |  |  |
| TASK65 | `env -u PYTHONPATH python3 paper/draft/make_table_3_1.py` |  |  |
| TASK66 | `env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py --json results/npu/stage2/reuse_cost.json` |  | `results/npu/stage2/reuse_cost.json` |
| TASK67 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| TASK68 | `env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py --run results/npu/stage2/20260823-183505-final-confirm --fix-arrivals results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/arrival_feedback.json` | `results/npu/stage2/20260823-183505-final-confirm`<br>`results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/arrival_feedback.json` |
| TASK68 | `env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py --run results/npu/stage2/20260824-160028-n6-reconfirm --fix-arrivals results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/arrival_feedback.json` | `results/npu/stage2/20260824-160028-n6-reconfirm`<br>`results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/arrival_feedback.json` |
| TASK68 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --table S07` |  |  |
| TASK69 | `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py --run results/npu/stage2/20260823-183505-final-confirm --sessions 6,8,10 --output results/npu/stage2/20260823-183505-final-confirm/dummy_block_effect.json` | `results/npu/stage2/20260823-183505-final-confirm` | `results/npu/stage2/20260823-183505-final-confirm/dummy_block_effect.json` |
| TASK69 | `env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py --run results/npu/stage2/20260824-160028-n6-reconfirm --sessions 6 --output results/npu/stage2/20260824-160028-n6-reconfirm/dummy_block_effect.json` | `results/npu/stage2/20260824-160028-n6-reconfirm` | `results/npu/stage2/20260824-160028-n6-reconfirm/dummy_block_effect.json` |
| TASK69 | `env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py --sessions 6,8,10 --weight sum-seconds --top 20 --dummy-block --output-dir results/npu/stage2/20260922-dummy-block/search-on` |  | `results/npu/stage2/20260922-dummy-block/search-on` |
| TASK69 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --table S08` |  |  |
| TASK71 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py` |  |  |
| TASK71 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py --seed 20260929` |  |  |
| TASK72 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_retro.py --items r1,r2,r3,r4,r5p,r5` |  |  |
| TASK72 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| TASK73 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_selfcheck.py` |  |  |
| TASK73 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v0_retro.py --items r1,r5p --out-dir <scratch>` |  | `<scratch>` |
| TASK73 | `env -u PYTHONPATH python3 experiments/npu/analysis/model_v1_dev.py` |  |  |
| TASK73 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| TASK74 | `env -u PYTHONPATH python3 experiments/npu/analysis/sim_semantics_effect.py` |  |  |
| TASK74 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| TASK77 | `env -u PYTHONPATH python3 experiments/npu/stage3/runner_offline_check.py --work <scratch>/offline` | `<scratch>/offline` |  |
| TASK77 | `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all` |  |  |
| TASK78 | `env -u PYTHONPATH python3 experiments/npu/stage3/select_grids.py --output results/npu/stage3/grid_select/select.json` |  | `results/npu/stage3/grid_select/select.json` |
| TASK79 | `bash experiments/npu/stage3/run_pilot.sh results/npu/stage3/20260929-pilot-streaming` |  | `results/npu/stage3/20260929-pilot-streaming` |
| TASK79 | `env -u PYTHONPATH python3 experiments/npu/stage3/pilot_analyze.py --run results/npu/stage3/20260929-pilot-streaming --output results/npu/stage3/20260929-pilot-streaming/pilot_verdict.json` | `results/npu/stage3/20260929-pilot-streaming` | `results/npu/stage3/20260929-pilot-streaming/pilot_verdict.json` |
| TASK80 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_main_plans.py` |  |  |
| TASK80 | `env -u PYTHONPATH python3 experiments/npu/stage3/predict_main.py --dp-grids experiments/npu/stage3/plans/main/DP_GRIDS.json --output results/npu/stage3/predict/main_predictions.json` | `experiments/npu/stage3/plans/main/DP_GRIDS.json` | `results/npu/stage3/predict/main_predictions.json` |
| TASK81 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_main_plans_ext.py` |  |  |
| TASK81 | `env -u PYTHONPATH python3 experiments/npu/stage3/predict_ext.py --output results/npu/stage3/predict/ext_predictions.json` |  | `results/npu/stage3/predict/ext_predictions.json` |
| TASK81 | `env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS.json` |  | `experiments/npu/stage3/plans/main/NULL_PREDICTORS.json` |
| TASK81 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_main_order.py` |  |  |
| TASK81 | `bash experiments/npu/stage3/compile_dp8.sh results/npu/stage3/20260930-main` |  | `results/npu/stage3/20260930-main` |
| TASK81 | `bash experiments/npu/stage3/map_check_dp8.sh results/npu/stage3/20260930-main` |  | `results/npu/stage3/20260930-main` |
| TASK82 | `bash experiments/npu/stage3/run_main.sh results/npu/stage3/20260930-main` |  | `results/npu/stage3/20260930-main` |
| TASK82 | `env -u PYTHONPATH python3 experiments/npu/stage3/main_analyze.py --run results/npu/stage3/20260930-main --output results/npu/stage3/20260930-main/main_verdict.json` | `results/npu/stage3/20260930-main` | `results/npu/stage3/20260930-main/main_verdict.json` |
| TASK83 | `env -u PYTHONPATH python3 experiments/npu/stage3/stationarity.py --run results/npu/stage3/20260930-main --output results/npu/stage3/20260930-main/stationarity.json` | `results/npu/stage3/20260930-main` | `results/npu/stage3/20260930-main/stationarity.json` |
| TASK84 | `bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_base` | `<scratch>/reg_base` |  |
| TASK84 | `bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_after2` | `<scratch>/reg_after2` |  |
| TASK84 | `env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <base> <after> --semantics-check` | `<base>`<br>`<after>` |  |
| TASK84 | `env -u PYTHONPATH python3 tests/test_descriptor_v2.py` |  |  |
| TASK85 | `env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev.py --output results/npu/stage3/v11_dev/diag.json` |  | `results/npu/stage3/v11_dev/diag.json` |
| TASK85 | `env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev_eval.py --ks 1,2,3 --order random --output results/npu/stage3/v11_dev/eval.json` |  | `results/npu/stage3/v11_dev/eval.json` |
| TASK85 | `env -u PYTHONPATH python3 experiments/npu/stage3/v11_dev_eval.py --ks 2,3 --order admission --output results/npu/stage3/v11_dev/eval_admission.json` |  | `results/npu/stage3/v11_dev/eval_admission.json` |
| TASK85 | `env -u PYTHONPATH python3 tests/test_survival_v11.py` |  |  |
| TASK85 | `env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX.json --ns 6,8,10,12 --with-dp8 --predictors v1,v11 --workers 70 --output results/npu/stage3/predict/v11_main_predictions.json` | `INDEX.json` | `results/npu/stage3/predict/v11_main_predictions.json` |
| TASK86 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_hiload_plans.py` |  |  |
| TASK86 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX_HI.json --ns 14,16 --workers 30 --output results/npu/stage3/predict/hiload_predictions.json` | `INDEX_HI.json` | `results/npu/stage3/predict/hiload_predictions.json` |
| TASK86 | `env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors_hi.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS_HI.json` |  | `experiments/npu/stage3/plans/main/NULL_PREDICTORS_HI.json` |
| TASK86 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_hiload_order.py` |  |  |
| TASK87 | `bash experiments/npu/stage3/run_hiload.sh results/npu/stage3/20261001-hiload` |  | `results/npu/stage3/20261001-hiload` |
| TASK87 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/hiload_analyze.py --run results/npu/stage3/20261001-hiload --output results/npu/stage3/20261001-hiload/hiload_verdict.json` | `results/npu/stage3/20261001-hiload` | `results/npu/stage3/20261001-hiload/hiload_verdict.json` |
| TASK88 | `bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_A` | `<scratch>/reg_A` |  |
| TASK88 | `env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <scratch>/reg_base <scratch>/reg_A --semantics-check` | `<scratch>/reg_base`<br>`<scratch>/reg_A` |  |
| TASK89 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 tests/gpu_sim_parity.py --gpu-root <scratch>/gpu_repo --out <scratch>/parity.json` | `<scratch>/gpu_repo` | `<scratch>/parity.json` |
| TASK89 | `bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_B` | `<scratch>/reg_B` |  |
| TASK89 | `env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <scratch>/reg_base <scratch>/reg_B --semantics-check` | `<scratch>/reg_base`<br>`<scratch>/reg_B` |  |
| TASK89 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/predict_v11.py --index INDEX_HI.json --ns 14,16 --workers 30 --output <scratch>/reg_B/hiload_predictions.json` | `INDEX_HI.json` | `<scratch>/reg_B/hiload_predictions.json` |
| TASK89 | `env -u PYTHONPATH python3 tests/test_descriptor_v2.py` |  |  |
| TASK90 | `env -u PYTHONPATH python3 experiments/npu/stage3/b2_diag.py --output results/npu/stage3/v12_dev/b2_diag.json` |  | `results/npu/stage3/v12_dev/b2_diag.json` |
| TASK90 | `env -u PYTHONPATH python3 experiments/npu/stage3/v12_dev_eval.py --output results/npu/stage3/v12_dev/freeze_check.json` |  | `results/npu/stage3/v12_dev/freeze_check.json` |
| TASK90 | `env -u PYTHONPATH python3 tests/test_survival_v11.py` |  |  |
| TASK91 | `env -u PYTHONPATH python3 experiments/npu/stage3/step_audit.py --output results/npu/stage3/step_audit/audit.json` |  | `results/npu/stage3/step_audit/audit.json` |
| TASK91 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/step_audit_explain.py --output results/npu/stage3/step_audit/explain.json` |  | `results/npu/stage3/step_audit/explain.json` |
| TASK92 | `bash experiments/npu/stage3/run_stepcost_op.sh results/npu/stage3/20261001-stepcost-op` |  | `results/npu/stage3/20261001-stepcost-op` |
| TASK92 | `bash experiments/npu/stage3/run_stepcost_supp.sh results/npu/stage3/20261001-stepcost-op` |  | `results/npu/stage3/20261001-stepcost-op` |
| TASK92 | `bash experiments/npu/stage3/run_stepcost_supp2.sh results/npu/stage3/20261001-stepcost-op` |  | `results/npu/stage3/20261001-stepcost-op` |
| TASK92 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/stage3/stepcost_op_analyze.py --run results/npu/stage3/20261001-stepcost-op --output results/npu/stage3/stepcost_op/stepcost_op.json` | `results/npu/stage3/20261001-stepcost-op` | `results/npu/stage3/stepcost_op/stepcost_op.json` |
| TASK92 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_opcost.py --source results/npu/stage3/stepcost_op/stepcost_op.json` | `results/npu/stage3/stepcost_op/stepcost_op.json` |  |
| TASK93 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_simblind_plans.py` |  |  |
| TASK93 | `cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 predict_simblind.py --output <REPO>/results/npu/stage3/predict/simblind_predictions.json && cd -` |  | `<REPO>/results/npu/stage3/predict/simblind_predictions.json` |
| TASK93 | `env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors_sim.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS_SIM.json` |  | `experiments/npu/stage3/plans/main/NULL_PREDICTORS_SIM.json` |
| TASK93 | `env -u PYTHONPATH python3 experiments/npu/stage3/make_simblind_order.py` |  |  |
| TASK93 | `bash experiments/npu/stage3/run_simblind.sh results/npu/stage3/20261002-simblind` |  | `results/npu/stage3/20261002-simblind` |
| TASK94 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all` |  |  |
| TASK95 | `bash experiments/npu/stage3/run_simblind.sh results/npu/stage3/20261002-simblind` |  | `results/npu/stage3/20261002-simblind` |
| TASK95 | `cd experiments/npu/stage3 && OMP_NUM_THREADS=1 env -u PYTHONPATH python3 simblind_analyze.py --run <REPO>/results/npu/stage3/20261002-simblind --output <REPO>/results/npu/stage3/20261002-simblind/simblind_verdict.json` | `<REPO>/results/npu/stage3/20261002-simblind` | `<REPO>/results/npu/stage3/20261002-simblind/simblind_verdict.json` |
| TASK96 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/queue_depth_obs.py --output results/npu/stage3/queue_obs/queue_obs.json` |  | `results/npu/stage3/queue_obs/queue_obs.json` |
| TASK96 | `OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all` |  |  |

## 4. Per-GTASK commands (GPU, branch `gpu-a6000`, `docs/research/gpu/GTASK*.md`)

Present in an export only with `--gpu-ref`.

| source | command | input paths | output paths |
|---|---|---|---|
| GTASK02 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/substrate/a6000_vllm_0220_draft.py` |  |  |
| GTASK07 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/tokid_check.py --out-dir <abs>/results/gpu/multiturn/tokid_check/<UTC>` |  | `<abs>/results/gpu/multiturn/tokid_check/<UTC>` |
| GTASK08 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/select_configs.py --out-dir <abs>/experiments/gpu/multiturn/selection --plans-dir <abs>/results/gpu/multiturn/selection_plans` | `<abs>/results/gpu/multiturn/selection_plans` | `<abs>/experiments/gpu/multiturn/selection` |
| GTASK09 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/predict_mt.py --selection <abs>/experiments/gpu/multiturn/selection/selection.json --plan-dir <abs>/experiments/gpu/multiturn/plans --out <abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json` | `<abs>/experiments/gpu/multiturn/selection/selection.json`<br>`<abs>/experiments/gpu/multiturn/plans` | `<abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json` |
| GTASK09 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/summarize_predictions.py <abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json` | `<abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json` |  |
| GTASK10 | `setsid nohup env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/run_schedule.py --schedule <abs>/experiments/gpu/multiturn/plans/pilot/SCHEDULE.json --run-dir <abs>/results/gpu/multiturn/pilot/20260929T1754Z &` | `<abs>/experiments/gpu/multiturn/plans/pilot/SCHEDULE.json`<br>`<abs>/results/gpu/multiturn/pilot/20260929T1754Z` |  |
| GTASK10 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/pilot_analyze.py --run-dir <RUN> --out <RUN>/pilot_verdict.json` |  | `<RUN>/pilot_verdict.json` |
| GTASK11 | `setsid nohup env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/run_schedule.py --schedule <abs>/experiments/gpu/multiturn/plans/main/ORDER.json --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z &` | `<abs>/experiments/gpu/multiturn/plans/main/ORDER.json`<br>`<abs>/results/gpu/multiturn/main/20260930T1411Z` |  |
| GTASK11 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/main_judge.py --run-dir <RUN> --out <RUN>/verdict.json` |  | `<RUN>/verdict.json` |
| GTASK12 | `setsid nohup env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/replay.py --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z --out <abs>/results/gpu/multiturn/main/20260930T1411Z/replay/run1.json --jobs 16 &` | `<abs>/results/gpu/multiturn/main/20260930T1411Z` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/replay/run1.json` |
| GTASK12 | `env -u PYTHONPATH <GPU_VENV>/bin/python experiments/gpu/multiturn/replay_summary.py --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z --replay <abs>/results/gpu/multiturn/main/20260930T1411Z/replay/run1.json --out <abs>/results/gpu/multiturn/main/20260930T1411Z/replay/summary.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z`<br>`<abs>/results/gpu/multiturn/main/20260930T1411Z/replay/run1.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/replay/summary.json` |
| GTASK13 | `python3 experiments/gpu/multiturn/timescale_report.py --sim <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/sim.json --verdict <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/../verdict.json --pred experiments/gpu/multiturn/plans/PREDICTIONS.json --out <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/timescale_report.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/sim.json`<br>`<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/../verdict.json`<br>`experiments/gpu/multiturn/plans/PREDICTIONS.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/timescale_report.json` |
| GTASK14 | `python3 experiments/gpu/multiturn/dynamics_report.py --obs <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/obs.json --sim <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/sim.json --timescale <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/timescale_report.json --out <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/dynamics_report.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/obs.json`<br>`<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/sim.json`<br>`<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/timescale_report.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/dynamics_report.json` |
| GTASK15 | `python3 experiments/gpu/multiturn/channel_report.py --obs <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/obs.json --out <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/channel_report.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/obs.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/channel_report.json` |
| GTASK16 | `python3 experiments/gpu/multiturn/stationarity.py --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z --out <abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/stationarity.json` | `<abs>/results/gpu/multiturn/main/20260930T1411Z` | `<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics/stationarity.json` |
