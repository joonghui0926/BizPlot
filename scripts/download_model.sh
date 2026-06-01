#!/bin/bash
# Qwen3.6-27B 모델 다운로드

MODEL_DIR="/SSD/guest/chojoonghui/FinPilot/models"
mkdir -p "$MODEL_DIR"

echo "Downloading Qwen/Qwen3.6-27B from HuggingFace..."
echo "Storage needed: ~54GB (BF16) or ~27GB (8-bit)"

/home/guest/anaconda3/envs/finpilot-llm/bin/python -c "
from huggingface_hub import snapshot_download
import os

model_dir = snapshot_download(
    repo_id='Qwen/Qwen3.6-27B',
    local_dir='$MODEL_DIR/Qwen3.6-27B',
    local_dir_use_symlinks=False,
    ignore_patterns=['*.pt', '*.bin'],  # safetensors만
)
print(f'Downloaded to: {model_dir}')
"
echo "Download complete."
