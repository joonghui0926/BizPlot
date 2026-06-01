#!/bin/bash
# BF16 GGUF → Q4_K_M 양자화 (변환 완료 후 실행)
INPUT="/SSD/guest/chojoonghui/FinPilot/models/finpilot-bf16.gguf"
OUTPUT="/SSD/guest/chojoonghui/FinPilot/models/finpilot-q4km.gguf"

echo "Q4_K_M 양자화 시작..."
CUDA_VISIBLE_DEVICES=7 /home/guest/llama.cpp/build/bin/llama-quantize "$INPUT" "$OUTPUT" Q4_K_M
echo "완료: $OUTPUT"
du -sh "$OUTPUT"
