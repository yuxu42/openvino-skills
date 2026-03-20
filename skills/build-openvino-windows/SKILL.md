---
name: build-openvino-windows
description: Build OpenVINO for Intel CPU and GPU on Windows, then build and verify OpenVINO GenAI on top of that build.
---

## Repos and environment

- OpenVINO source: `C:\Users\sas\yxu28\openvino`
- OpenVINO GenAI source: `C:\Users\sas\yxu28\openvino.genai`
- PowerShell venv: `C:\Users\sas\yxu28\venv-ov\Scripts\Activate.ps1`
- Use at most 4 build jobs.

OpenVINO GenAI must be built against the same OpenVINO source build. On this machine, the validated entry point is the local install created from that build: `openvino/install-vs`.

## Primary docs

1. OpenVINO Windows build doc: `openvino/docs/dev/build_windows.md`
2. OpenVINO Linux build doc: `openvino/docs/dev/build_linux.md`
3. OpenVINO GenAI build doc: `openvino.genai/src/docs/BUILD.md`
4. OpenVINO extra modules option: `openvino/cmake/features.cmake` and `openvino/cmake/extra_modules.cmake`

## Proxy for restricted network

When GitHub downloads stall or time out, use:

```powershell
$proxy = 'http://proxy-dmz.intel.com:912'
$env:HTTP_PROXY = $proxy
$env:HTTPS_PROXY = $proxy
$env:http_proxy = $proxy
$env:https_proxy = $proxy
```

This proxy worked for configure and build attempts in this workspace.

## Windows dependency staging

### TBB archive for OpenVINO

- Cached file: `C:\Users\sas\yxu28\oneapi-tbb-2021.13.1-win.zip`
- Place or keep a copy at `openvino/temp/download/oneapi-tbb-2021.13.1-win.zip` before CMake configure.

### SentencePiece for OpenVINO GenAI / Tokenizers

- Cached tarball: `C:\Users\sas\yxu28\sentencepiece-0.2.1.tar.gz`
- Verified local unpacked source: `openvino.genai/thirdparty/sentencepiece-0.2.1-local/sentencepiece-0.2.1`
- Reliable offline workaround:
  `-DFETCHCONTENT_SOURCE_DIR_SENTENCEPIECE=C:/Users/sas/yxu28/openvino.genai/thirdparty/sentencepiece-0.2.1-local/sentencepiece-0.2.1`

### PCRE2 for OpenVINO GenAI / Tokenizers

- Cached archive: `C:\Users\sas\yxu28\pcre2-10.46.zip`
- `openvino.genai/thirdparty/openvino_tokenizers/src/CMakeLists.txt` supports a local archive override.
- Override priority:
  1. `-DPCRE2_LOCAL_ARCHIVE=...`
  2. environment variable `PCRE2_LOCAL_ARCHIVE`
  3. auto-detected `C:/Users/sas/yxu28/pcre2-10.46.zip`

### nlohmann_json for OpenVINO GenAI

- Cached archive: `C:\Users\sas\yxu28\json-3.11.3.tar.gz`
- `openvino.genai/src/cpp/CMakeLists.txt` supports a local archive override.
- Override priority:
  1. `-DNLOHMANN_JSON_LOCAL_ARCHIVE=...`
  2. environment variable `NLOHMANN_JSON_LOCAL_ARCHIVE`
  3. auto-detected `C:/Users/sas/yxu28/json-3.11.3.tar.gz`

### safetensors.h for OpenVINO GenAI

- Cached archive: `C:\Users\sas\yxu28\974a85d7dfd6e010558353226638bb26d6b9d756.tar.gz`
- `openvino.genai/src/cpp/CMakeLists.txt` supports a local archive override.
- Override priority:
  1. `-DSAFETENSORS_H_LOCAL_ARCHIVE=...`
  2. environment variable `SAFETENSORS_H_LOCAL_ARCHIVE`
  3. auto-detected `C:/Users/sas/yxu28/974a85d7dfd6e010558353226638bb26d6b9d756.tar.gz`

## Verified OpenVINO build flow on Windows

Use PowerShell from `C:\Users\sas\yxu28`:

```powershell
& .\venv-ov\Scripts\Activate.ps1

cmake -S openvino -B openvino\build-vs -G "Visual Studio 17 2022" -A x64 `
  -DENABLE_TESTS=OFF `
  -DENABLE_INTEL_NPU=OFF `
  -DENABLE_INTEL_NPU_INTERNAL=OFF `
  -DENABLE_JS=OFF

cmake --build openvino\build-vs --config Release --parallel 4
cmake --install openvino\build-vs --config Release --prefix openvino\install-vs
```

### Verified OpenVINO artifacts

The build and install produced these validated runtime files:

- `openvino/bin/intel64/Release/openvino.dll`
- `openvino/bin/intel64/Release/openvino_intel_cpu_plugin.dll`
- `openvino/bin/intel64/Release/openvino_intel_gpu_plugin.dll`
- `openvino/install-vs/runtime/bin/intel64/Release/openvino.dll`
- `openvino/install-vs/runtime/bin/intel64/Release/openvino_intel_cpu_plugin.dll`
- `openvino/install-vs/runtime/bin/intel64/Release/openvino_intel_gpu_plugin.dll`
- `openvino/install-vs/python/openvino/_pyopenvino.cp310-win_amd64.pyd`

## Environment for building OpenVINO GenAI against the local OpenVINO install

Use PowerShell and keep the venv active:

```powershell
& .\venv-ov\Scripts\Activate.ps1
. .\openvino\install-vs\setupvars.ps1

$env:OpenVINO_DIR = "$PWD\openvino\install-vs\runtime\cmake"
$env:OPENVINO_LIB_PATHS = "$PWD\openvino\install-vs\runtime\bin\intel64\Release;$env:OPENVINO_LIB_PATHS"
$env:PYTHONPATH = "$PWD\openvino\install-vs\python;$env:PYTHONPATH"
$env:PATH = "$env:OPENVINO_LIB_PATHS;$env:PATH"
```

`openvino/install-vs/runtime/cmake` is the validated `OpenVINO_DIR` for GenAI configure on this machine.

## Verified OpenVINO GenAI configure/build commands on this machine

The validated GenAI build directory in this workspace is `openvino.genai/build-vs7`.

```powershell
$proxy = 'http://proxy-dmz.intel.com:912'
$env:HTTP_PROXY = $proxy
$env:HTTPS_PROXY = $proxy
$env:http_proxy = $proxy
$env:https_proxy = $proxy

& .\venv-ov\Scripts\Activate.ps1
. .\openvino\install-vs\setupvars.ps1

cmake -S openvino.genai -B openvino.genai\build-vs7 -G "Visual Studio 17 2022" -A x64 `
  -DOpenVINO_DIR="$PWD\openvino\install-vs\runtime\cmake" `
  -DFETCHCONTENT_SOURCE_DIR_SENTENCEPIECE="$PWD\openvino.genai\thirdparty\sentencepiece-0.2.1-local\sentencepiece-0.2.1" `
  -DPCRE2_LOCAL_ARCHIVE="$PWD\pcre2-10.46.zip" `
  -DNLOHMANN_JSON_LOCAL_ARCHIVE="$PWD\json-3.11.3.tar.gz" `
  -DSAFETENSORS_H_LOCAL_ARCHIVE="$PWD\974a85d7dfd6e010558353226638bb26d6b9d756.tar.gz" `
  -DENABLE_XGRAMMAR=OFF `
  -DENABLE_GGUF=OFF `
  -DENABLE_JS=OFF

cmake --build openvino.genai\build-vs7 --config Release --parallel 4
```

Validated build outputs include:

- `openvino.genai/build-vs7/openvino_genai/openvino_genai.dll`
- `openvino.genai/build-vs7/openvino_genai/openvino_tokenizers.dll`
- `openvino.genai/build-vs7/openvino_genai/py_openvino_genai.cp310-win_amd64.pyd`
- `openvino.genai/build-vs7/src/c/Release/openvino_genai_c.dll`
- `openvino.genai/build-vs7/OpenVINOGenAIConfig.cmake`
- `openvino.genai/build-vs7/OpenVINOGenAITargets.cmake`

## Verified OpenVINO GenAI install command on this machine

After a successful build, install GenAI into the same local OpenVINO prefix:

```powershell
cmake --install openvino.genai\build-vs7 --config Release --prefix openvino\install-vs
```

Verified installed artifacts include:

- `openvino/install-vs/runtime/bin/intel64/Release/openvino_genai.dll`
- `openvino/install-vs/runtime/bin/intel64/Release/openvino_genai_c.dll`
- `openvino/install-vs/runtime/bin/intel64/Release/openvino_tokenizers.dll`
- `openvino/install-vs/runtime/lib/intel64/Release/openvino_genai.lib`
- `openvino/install-vs/runtime/lib/intel64/Release/openvino_genai_c.lib`
- `openvino/install-vs/python/openvino_genai/py_openvino_genai.cp310-win_amd64.pyd`
- `openvino/install-vs/runtime/cmake/OpenVINOGenAIConfig.cmake`
- `openvino/install-vs/runtime/cmake/OpenVINOGenAITargets.cmake`

## How to verify with GenAI applications for an LLM IR model

Validated model path on this machine:

- `C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16`

### Important Windows runtime note

`openvino_tokenizers.dll` requires `tbb12.dll`. The validated fix on this machine is to add the Intel oneAPI TBB runtime to `PATH` before running GenAI applications:

```powershell
$env:PATH = "C:\Program Files (x86)\Intel\oneAPI\tbb\latest\bin;$env:PATH"
```

For build-tree verification, also add the GenAI build outputs:

```powershell
. .\openvino\install-vs\setupvars.ps1
$env:PATH = "C:\Program Files (x86)\Intel\oneAPI\tbb\latest\bin;$PWD\openvino.genai\build-vs7\openvino_genai;$PWD\openvino.genai\build-vs7\bin\Release;$env:PATH"
```

### Build verification applications

```powershell
cmake --build openvino.genai\build-vs7 --config Release --target benchmark_genai greedy_causal_lm --parallel 4
```

### Benchmark verification

Use the validated C++ benchmark sample:

```powershell
.\openvino.genai\build-vs7\bin\Release\benchmark_genai.exe `
  -m "C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16" `
  -d CPU `
  --nw 1 `
  -n 2 `
  --mt 20
```

GPU run:

```powershell
.\openvino.genai\build-vs7\bin\Release\benchmark_genai.exe `
  -m "C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16" `
  -d GPU `
  --nw 1 `
  -n 2 `
  --mt 20
```

Note: on this machine, the C++ sample accepted `--nw` and `--mt`; using short forms for those flags was not the validated path.

Observed benchmark result on this machine:

- CPU
  - Load time: `988.00 ms`
  - Generate time: `1363.12 +/- 94.32 ms`
  - TTFT: `151.40 +/- 45.06 ms`
  - TPOT: `63.76 +/- 10.15 ms/token`
  - Throughput: `15.68 +/- 2.50 tokens/s`
- GPU
  - Load time: `10422.00 ms`
  - Generate time: `999.55 +/- 2.91 ms`
  - TTFT: `52.16 +/- 0.00 ms`
  - TPOT: `49.84 +/- 0.92 ms/token`
  - Throughput: `20.06 +/- 0.37 tokens/s`

### Functional generation verification

Use the validated C++ greedy sample for a simple end-to-end check:

```powershell
.\openvino.genai\build-vs7\bin\Release\greedy_causal_lm.exe `
  "C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16" `
  "Write one short sentence about OpenVINO."
```

This command was validated to load the model and generate text. With this model, the first output may start with `<think>` before the final answer text.

## Alternative integration path

OpenVINO GenAI can also be built as an OpenVINO extra module with `OPENVINO_EXTRA_MODULES`, but the verified standalone path in this workspace is:

1. build OpenVINO first
2. install it locally under `openvino/install-vs`
3. point `OpenVINO_DIR` at `openvino/install-vs/runtime/cmake`
4. configure OpenVINO GenAI separately

## LLM bench reminder

- Tool: `openvino.genai/tools/llm_bench`
- Model path provided by user: `C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16`
- Save the `llm_bench` result when benchmark execution is requested.

## Current status observed on this machine

- OpenVINO build is complete.
- OpenVINO GenAI build is complete in `openvino.genai/build-vs7` with `ENABLE_GGUF=OFF`.
- OpenVINO GenAI was installed into `openvino/install-vs`.
- Verified installed runtime artifacts include `openvino_genai.dll`, `openvino_genai_c.dll`, `openvino_tokenizers.dll`, the Python package, and the `OpenVINOGenAIConfig.cmake` package files.
- Local archive overrides are implemented for `SentencePiece`, `PCRE2`, `nlohmann_json`, and `safetensors.h`.
- Proxy `http://proxy-dmz.intel.com:912` can be used when GitHub access is slow or blocked.
- Verified GenAI applications on this machine include `benchmark_genai.exe` and `greedy_causal_lm.exe`.
- Verified LLM IR model path is `C:\Users\sas\models\deepseek-r1-distill-qwen-1.5b\FP16`.
- Verified benchmark result shows better steady-state throughput on GPU than CPU for this model, but higher GPU load time.
- `tbb12.dll` from `C:\Program Files (x86)\Intel\oneAPI\tbb\latest\bin` must be available on `PATH` for the validated C++ GenAI applications.
