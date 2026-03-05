---
name: fix-ov-crash-issue
description: when running benchmmark_app of openvino with model, it crash with lastest OpenVINO master, but it works well in previous version. Please help to fix the issue.
---

## OS and Version: Ubuntu 20.04
Please be aware that you'r working on Linux OS, using Linus style file path, and using bash command line.

# Skill Instructions
## Build OpenVINO
Build OpenVINO with the following command:

```bash
cd ~/test/openvino/build_release
cmake -DENABLE_INTEL_CPU=ON -DENABLE_INTEL_GPU=OFF -DENABLE_INTEL_GNA=OFF -DENABLE_TESTS=ON ..
make --jobs=$(nproc --all)
```

## Source Code
The source code is in the following path:
~/test/openvino

## Models
The models are in the following paths:
~/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.xml
~/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.bin


## How to reproduce
You can use the following command to run

```bash
benchmark_app -m ~/projects/test/tmp/TF_Separate_Bass_IR_v11_FP16_batch_1.xml -t=5 -data_shape "[1,2] -d CPU
```
you can find benchmark_app after you build OpenVINO. You can confirm whether it's can be reproduced or not. If it can be reproduced, please fix the issue.

The error message is as follows:
[ ERROR ] Fatal Python error: Fatal Python error: Floating point exception

## Summarize the root cause of the issue and confirm with user before you fix the issue.

## After confirm with user for the root cause, go on to fix

## After you fix the issue, you can re-run the test:

## Single layer accuracy test
You can use the following command to run the single layer accuracy test:

```bash
ov_cpu_func_tests
```
