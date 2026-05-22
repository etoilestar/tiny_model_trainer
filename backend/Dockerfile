# syntax=docker/dockerfile:1
ARG TARGETARCH=amd64

# ── AMD64: CUDA 12.1 runtime + Python 3.11 ────────────────────────────────
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04 AS base-amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-distutils \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

# 安装 PyTorch 2.5.1（CUDA 12.1）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu121 \
    && pip install --no-cache-dir -r /tmp/requirements.txt

RUN pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless || true \
    && pip install --no-cache-dir opencv-python-headless==4.10.0.84 -i https://pypi.tuna.tsinghua.edu.cn/simple

# ── ARM64: CPU-only Python 3.11 ────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 PyTorch 2.5.1（CPU-only）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# ── Final: 根据 TARGETARCH 选择基础镜像（默认 amd64）─────────────────────
FROM base-${TARGETARCH}

WORKDIR /app

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/data /app/uploads /app/models /app/checkpoints

EXPOSE 5000

CMD ["python", "run.py"]
