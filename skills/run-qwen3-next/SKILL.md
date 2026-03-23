---
name: run-qwen3-next
description: Run Qwen3-Next OpenVINO IR models with OpenVINO GenAI llm_bench on Windows, including validated setup, CPU fallback, and current GPU limitations.
---

## Scope

This skill is for running Qwen3-Next OpenVINO IR models from `openvino.genai/tools/llm_bench/benchmark.py` on this Windows machine.

Validated paths:

- OpenVINO source: `C:\Users\sas\yxu28\openvino`
- OpenVINO GenAI source: `C:\Users\sas\yxu28\openvino.genai`
- Python venv activation: `C:\Users\sas\yxu28\venv-ov\Scripts\Activate.ps1`
- `llm_bench` entry point: `C:\Users\sas\yxu28\openvino.genai\tools\llm_bench\benchmark.py`

## Models observed on this machine

- FP16 model: `C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-fp16-small`
- INT4 model: `C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-i4-small`

Both exports report:

- `architectures`: `Qwen3NextForCausalLM`
- `model_type`: `qwen3_next`
- `transformers_version`: `4.57.6`

## Python environment setup

Use the venv first:

```powershell
& C:\Users\sas\yxu28\venv-ov\Scripts\Activate.ps1
```

Clear inherited Python path before running `benchmark.py`:

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
```

For Optimum backend runs, also set:

```powershell
$env:OMP_WAIT_POLICY = 'PASSIVE'
```

## Baseline command pattern

From `C:\Users\sas\yxu28`:

```powershell
& .\venv-ov\Scripts\Activate.ps1
Push-Location .\openvino.genai\tools\llm_bench
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:OMP_WAIT_POLICY = 'PASSIVE'
python .\benchmark.py -m "MODEL_DIR" -d DEVICE -f ov -t text_gen --optimum -p "Explain OpenVINO in one sentence." -n 1 -ic 20
Pop-Location
```

## Validated working path: FP16 model on CPU with Optimum backend

```powershell
& .\venv-ov\Scripts\Activate.ps1
Push-Location .\openvino.genai\tools\llm_bench
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:OMP_WAIT_POLICY = 'PASSIVE'
python .\benchmark.py `
  -m "C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-fp16-small" `
  -d CPU `
  -f ov `
  -t text_gen `
  --optimum `
  -p "Explain OpenVINO in one sentence." `
  -n 1 `
  -ic 20
Pop-Location
```

Observed result:

- `From pretrained time`: `53.24s`
- input tokens: `9`
- first token latency: `260.87 ms`
- other token latency: `43.20 ms/token`
- throughput: `23.15 tokens/s`

## GPU attempt: FP16 model with Optimum backend

```powershell
& .\venv-ov\Scripts\Activate.ps1
Push-Location .\openvino.genai\tools\llm_bench
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:OMP_WAIT_POLICY = 'PASSIVE'
python .\benchmark.py `
  -m "C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-fp16-small" `
  -d GPU `
  -f ov `
  -t text_gen `
  --optimum `
  -p "Explain OpenVINO in one sentence." `
  -n 1 `
  -ic 20
Pop-Location
```

Current result:

- compile fails on GPU with unsupported MOE operation

Observed error signature:

- `Operation: __module.model.layers.0.mlp/aten::sum/ReduceSum_1 of type MOE(extension) is not supported`

## GPU attempt: FP16 model with OpenVINO GenAI backend

The model directory needs tokenizer IR files.

Tokenizer conversion used successfully:

```powershell
& .\venv-ov\Scripts\Activate.ps1
python -c "from pathlib import Path; from transformers import AutoTokenizer; from optimum.exporters.openvino.convert import export_tokenizer; model_dir = Path(r'C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-fp16-small'); tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True); export_tokenizer(tok, model_dir)"
```

This produces:

- `openvino_tokenizer.xml`
- `openvino_detokenizer.xml`

GPU GenAI run still fails with:

- `Model references undeclared parameters: opset1::Parameter beam_idx () -> (i32[?])`

## INT4 model status

INT4 model path:

- `C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-i4-small`

Observed Optimum backend failure:

- `ConvertFullyConnectedToFullyConnectedCompressed`
- incompatible MatMul dimensions: `2048` vs `128`

## Practical guidance

1. use FP16 model on CPU with `--optimum` as the validated path
2. for GPU, expect current backend limitations for Qwen3-Next in this environment
3. current GPU failures are not caused by missing venv setup

## Short status summary

- CPU + Optimum + FP16: validated
- GPU + Optimum + FP16: failed on unsupported `MOE(extension)`
- GPU + GenAI + FP16: failed on undeclared `beam_idx`
- CPU/GPU + Optimum + INT4: failed on compressed MatMul shape mismatch
