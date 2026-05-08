#!/usr/bin/env python3
"""测试 WSL DrvFS 上 Python subprocess 的 CUDA 兼容性"""
import os
import subprocess
import sys

env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0"
env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")

# 测试1: nvidia-smi 在 Python subprocess 中
print("=== Test 1: nvidia-smi via subprocess ===")
r = subprocess.run(["nvidia-smi"], capture_output=True, text=True, env=env)
print(r.stdout[:500])

# 测试2: llama-server --help 在 Python subprocess 中
server = "/mnt/d/MiniCPM-V-CookBook-1/demo/web_demo/WebRTC_Demo/llama.cpp-omni/build/bin/llama-server"
print("\n=== Test 2: llama-server --help via subprocess (DrvFS) ===")
r = subprocess.run([server, "--help"], capture_output=True, text=True, env=env, timeout=10)
cuda_lines = [l for l in r.stderr.splitlines() if "cuda" in l.lower()]
for line in cuda_lines[:3]:
    print(line)

# 测试3: 把 binary 复制到 /tmp/ 后再运行
import shutil
import platform
if platform.system() == "Linux" and server.startswith("/mnt/"):
    tmp_dir = "/tmp/llama_test_cuda"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    shutil.copytree(os.path.dirname(server), tmp_dir, symlinks=True)
    for f in os.listdir(tmp_dir):
        fp = os.path.join(tmp_dir, f)
        if os.path.isfile(fp):
            os.chmod(fp, os.stat(fp).st_mode | 0o111)
    tmp_server = os.path.join(tmp_dir, "llama-server")
    
    print("\n=== Test 3: llama-server --help via subprocess (/tmp ext4) ===")
    r = subprocess.run([tmp_server, "--help"], capture_output=True, text=True, env=env, timeout=10, cwd=tmp_dir)
    cuda_lines = [l for l in r.stderr.splitlines() if "cuda" in l.lower()]
    for line in cuda_lines[:3]:
        print(line)

# 测试4: 直接 import ctypes 调用 libcuda
print("\n=== Test 4: ctypes cuInit ===")
try:
    import ctypes
    libcuda = ctypes.CDLL("libcuda.so.1")
    result = libcuda.cuInit(0)
    print(f"cuInit(0) = {result}")
    
    count = ctypes.c_int()
    libcuda.cuDeviceGetCount(ctypes.byref(count))
    print(f"cuDeviceGetCount = {count.value}")
except Exception as e:
    print(f"cuInit failed: {e}")

print("\nDone.")
