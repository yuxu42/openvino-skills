---
name: build-test-openvino-genai-cpu
description: Build OpenVINO and OpenVINO.genai for CPU platform and run llm_bench with LLM models.
---

When build and test openvino and openvino.genai, always include:

1. openvino.genai is working on top of openvino, working as LLM pipeline application.
2. **how to build openvino**: $REPO_ROOT/openvino/docs/dev/build_linux.md. Build OpenVINO for CPU platform only. with 2 CPU cores at most. Build foler: openvino/build-test-ov-genai/
3. **how to build openvino.genai**: openvino.genai/src/docs/BUILD.md (code can be fetch from https://github.com/openvinotoolkit/openvino.genai.git)
4. **how to run llm_bench**: (https://github.com/openvinotoolkit/openvino.genai/tree/master/tools/llm_bench) tool to collect performance data on the platform with deepseek-r1-distill-qwen-1.5b model. 
5. **Using model IR file under**: /mnt/disk1/yxu28/models/deepseek-r1-distill-qwen-1.5b/FP16/
6. **please work in virtual environment**: "source venv-test/bin/activate" for Linux or "venv-test/Script/activate" for Windows.
7. **report the llm_bench result**: please save the llm_bench

---

## Manual dependency prep if on Windows OS

Download `oneapi-tbb-2021.13.1-win.zip` from
	https://storage.openvinotoolkit.org/dependencies/thirdparty/windows/oneapi-tbb-2021.13.1-win.zip
	and place it in [openvino/temp/download](openvino/temp/download) before running CMake. The build now relies on a small patch inside
	[cmake/dependencies.cmake](cmake/dependencies.cmake) (see [SKILL.md patch reference](tbb_patch.diff)) that detects the cached archive and flips `ENABLE_UNSAFE_LOCATIONS` temporarily so
	the extraction step can reuse the file without trying to fetch it again.

## CMake invocation (once prereqs are staged)

- Configure/build OpenVINO with the heavyweight components disabled so the limited network in this environment does not stall the configure step:

	```text
	cmake -S . -B build -DENABLE_INTEL_NPU=OFF -DENABLE_INTEL_NPU_INTERNAL=OFF -DENABLE_JS=OFF
	cmake --build build --config Release
	```

	The patched build still produces `bin/intel64/Release` artifacts for the CPU path, and the commands turn off the NPU compiler download plus the `node-api-headers` fetch that kept timing out.