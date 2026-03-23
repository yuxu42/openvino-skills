# Using CLIntercept with Qwen3-Next

`CLIntercept` can intercept OpenCL API calls and generate logs, timing summaries, and Chrome trace files.

Package location on this machine:

- `C:\Users\sas\yxu28\opencl-intercept-layer`

## What was validated

The OpenCL intercept layer was built successfully on this machine:

- `C:\Users\sas\yxu28\opencl-intercept-layer\build-vs\cliloader\Release\cliloader.exe`
- `C:\Users\sas\yxu28\opencl-intercept-layer\build-vs\intercept\Release\OpenCL.dll`

Because Windows `cliloader.exe` must be in the same directory as the intercept `OpenCL.dll`, a runnable folder was prepared here:

- `C:\Users\sas\yxu28\opencl-intercept-layer\run`

## Important note about `clinfo`

The suggested smoke test is:

```powershell
cliloader.exe clinfo
```

However, `clinfo.exe` was not found on this machine, so that exact test was not run.

## Validated Qwen3-Next CLIntercept command

This command was used to run the FP16 Qwen3-Next model on GPU through `llm_bench` with Optimum backend under CLIntercept:

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:OMP_WAIT_POLICY = 'PASSIVE'

Push-Location C:\Users\sas\yxu28\opencl-intercept-layer\run
.\cliloader.exe -dv -cdt -f --dump-dir C:\Users\sas\yxu28\opencl-intercept-layer\run\dump_qwen_gpu_optimum `
  C:\Users\sas\yxu28\venv-ov\Scripts\python.exe `
  C:\Users\sas\yxu28\openvino.genai\tools\llm_bench\benchmark.py `
  -m C:\Users\sas\models\Qwen3-Next-80B-A3B-Instruct-ov-fp16-small `
  -d GPU `
  -f ov `
  -t text_gen `
  --optimum `
  -p "Explain OpenVINO in one sentence." `
  -n 1 `
  -ic 20
Pop-Location
```

## Runtime result

The benchmark still failed during GPU model compilation with the same Optimum/OpenVINO GPU error:

- `Operation: __module.model.layers.0.mlp/aten::sum/ReduceSum_1 of type MOE(extension) is not supported`

This means the run did not reach successful GPU kernel execution.

## CLIntercept output files

The run generated these files:

- `C:\Users\sas\yxu28\opencl-intercept-layer\run\dump_qwen_gpu_optimum\clintercept_log.txt`
- `C:\Users\sas\yxu28\opencl-intercept-layer\run\dump_qwen_gpu_optimum\clintercept_report.txt`
- `C:\Users\sas\yxu28\opencl-intercept-layer\run\dump_qwen_gpu_optimum\clintercept_trace.json`

## Observed CLIntercept analysis

Key findings from the intercept logs:

- `CLIntercept` loaded successfully
- it found and loaded the system OpenCL dispatch loader
- device timing and Chrome device timeline controls were enabled
- `Total Enqueues: 0`
- the Chrome trace contains only process metadata and no device execution records

## Performance conclusion

For this Qwen3-Next FP16 GPU attempt, CLIntercept shows that:

1. the application did not submit any OpenCL kernel enqueues
2. the failure happened before actual GPU execution
3. there is no kernel-level OpenCL performance bottleneck to analyze yet for this workload in the current environment
4. the real blocker is model/backend compatibility on GPU, not a low-level OpenCL execution slowdown

## Practical next step

To get useful CLIntercept performance data, first run a GPU workload that compiles and executes successfully. For Qwen3-Next on this machine, the currently validated path is:

- CPU + `benchmark.py --optimum` + FP16 model

GPU paths currently fail before OpenCL execution:

- Optimum backend: unsupported `MOE(extension)`
- OpenVINO GenAI backend: undeclared `beam_idx`
