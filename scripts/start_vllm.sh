#!/bin/bash
# Qwen3.6-27B vLLM 서빙 시작 스크립트
# 8-bit 양자화 (AWQ/GPTQ) 또는 BF16으로 서빙

MODEL_PATH="/SSD/guest/chojoonghui/FinPilot/models/Qwen3.6-27B"
FALLBACK_MODEL="/SSD/guest/chojoonghui/LIBO2/models/Qwen3-14B"

# 모델 존재 확인
if [ -d "$MODEL_PATH" ]; then
    USE_MODEL=$MODEL_PATH
    MODEL_NAME="Qwen3.6-27B-FinPilot"
    echo "Using Qwen3.6-27B"
elif [ -d "$FALLBACK_MODEL" ]; then
    USE_MODEL=$FALLBACK_MODEL
    MODEL_NAME="Qwen3-14B-FinPilot"
    echo "Using Qwen3-14B (fallback)"
else
    echo "ERROR: No model found. Run download_model.sh first."
    exit 1
fi

# GPU 메모리 확인
GPU_MEM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
echo "GPU Free Memory: ${GPU_MEM}MB"

# 양자화 설정 (48GB → 27B 8-bit 가능)
if [ "${GPU_MEM:-0}" -gt 40000 ]; then
    QUANTIZE="--dtype bfloat16"
else
    QUANTIZE="--quantization awq --dtype auto"
fi

echo "Starting vLLM server on port 8001..."
CUDA_VISIBLE_DEVICES=0 \
    /home/guest/anaconda3/envs/finpilot-llm/bin/python -m vllm.entrypoints.openai.api_server \
    --model "$USE_MODEL" \
    --host 127.0.0.1 \
    --port 8001 \
    $QUANTIZE \
    --max-model-len 32768 \
    --served-model-name "$MODEL_NAME" \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --gpu-memory-utilization 0.92 \
    2>&1 | tee /tmp/vllm.log
