---
name: fix-ov-crash-issue
description: Fix a reproducible OpenVINO CPU crash in benchmark_app on latest master (works in older revisions).
---

## Environment
- OS: Ubuntu 20.04
- Shell: bash
- Path style: Linux/Unix paths only (`/` and `~`)

# Skill Instructions

## Build OpenVINO
Build OpenVINO with:

```bash
cd /home/yxu28/projects/test/openvino/build_release
cmake -DENABLE_INTEL_CPU=ON -DENABLE_INTEL_GPU=OFF -DENABLE_INTEL_GNA=OFF -DENABLE_TESTS=ON ..
cmake --build . -- -j"$(nproc --all)"
```

## Source Code
- `/home/yxu28/projects/test/openvino`

## Model Paths
- `/home/yxu28/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.xml`
- `/home/yxu28/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.bin`

## Reproduce the Crash
Run:

```bash
/home/yxu28/projects/test/openvino/bin/intel64/Release/benchmark_app \
  -m /home/yxu28/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.xml \
  -t=5 \
  -data_shape "[1,2]" \
  -d CPU
```

The typical failure signature is:

```text
[ ERROR ] Fatal Python error: Floating point exception
```

The process may exit with code `136` (`SIGFPE`).

## Root Cause Workflow
1. Reproduce the issue and collect logs/backtrace.
2. Summarize the root cause.
3. Confirm the root cause with the user before changing code.
4. Implement the fix after user confirmation.

## Root Cause (Current Finding)
`SIGFPE` (exit `136`) comes from oneDNN reorder in TensorIterator back-edge handling when a dynamic-shape iteration produces zero-sized memory.

Failing call path:
- `BackEdgePortHelper::execute`
- `src/plugins/intel_cpu/src/nodes/tensoriterator.cpp` (around lines 182-185)
- `reorder.execute(...)` is called without checking empty memory descriptors.

## Patch Reference
```diff
diff --git a/src/plugins/intel_cpu/src/nodes/tensoriterator.cpp b/src/plugins/intel_cpu/src/nodes/tensoriterator.cpp
index 46d9922df8..e8f8ff9ef2 100644
--- a/src/plugins/intel_cpu/src/nodes/tensoriterator.cpp
+++ b/src/plugins/intel_cpu/src/nodes/tensoriterator.cpp
@@ -180,7 +180,7 @@ public:
     }

     void execute(const dnnl::stream& strm, int iter) override {
-        if (iter != 0) {
+        if (iter != 0 && mem_holder_src.get_desc().get_size() != 0 && mem_holder_dst.get_desc().get_size() != 0) {
             reorder.execute(strm, {{DNNL_ARG_FROM, mem_holder_src}, {DNNL_ARG_TO, mem_holder_dst}});
         }
     }
```

## Validation
After applying the fix, re-run the reproduce command above and confirm there is no crash.

## Single Layer Accuracy Test
```bash
ov_cpu_func_tests
```
