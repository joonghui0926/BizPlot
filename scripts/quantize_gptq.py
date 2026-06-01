"""
Qwen3.6-27B merged → GPTQ INT8 양자화 (optimum 사용)
GPU 7, 결과: models/finpilot-qwen3.6-27b-gptq-int8
"""
import os, json, torch
os.environ["CUDA_VISIBLE_DEVICES"] = "7"
os.environ["LD_LIBRARY_PATH"] = (
    "/home/guest/anaconda3/envs/finpilot-llm/lib/python3.10/site-packages/nvidia/cu13/lib:"
    + os.environ.get("LD_LIBRARY_PATH", "")
)

from transformers import AutoTokenizer, AutoModelForCausalLM
from optimum.gptq import GPTQQuantizer

MODEL_PATH  = "/SSD/guest/chojoonghui/FinPilot/models/finpilot-qwen3.6-27b-merged"
OUTPUT_PATH = "/SSD/guest/chojoonghui/FinPilot/models/finpilot-qwen3.6-27b-gptq-int8"
TRAIN_PATH  = "/SSD/guest/chojoonghui/FinPilot/data/training/train.jsonl"

print("토크나이저 로드...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("캘리브레이션 데이터 준비 (128개)...")
with open(TRAIN_PATH) as f:
    raw = [json.loads(l) for l in f]

dataset = []
for item in raw[:128]:
    text = tokenizer.apply_chat_template(
        item["messages"], tokenize=False, add_generation_prompt=False
    )
    dataset.append(text)
print(f"캘리브레이션 샘플: {len(dataset)}개")

print("\n모델 로드 중 (CPU, float16)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map="cpu",
    low_cpu_mem_usage=True,
)
print(f"모델 로드 완료. 파라미터: {sum(p.numel() for p in model.parameters())/1e9:.1f}B")

print("\nGPTQ INT8 양자화 시작... (1~2시간 예상)")
quantizer = GPTQQuantizer(
    bits=8,
    group_size=128,
    dataset=dataset,
    tokenizer=tokenizer,
    model_seqlen=1024,
)

quantized_model = quantizer.quantize_model(model, tokenizer)
print("양자화 완료!")

print(f"\n저장 중: {OUTPUT_PATH}")
os.makedirs(OUTPUT_PATH, exist_ok=True)
quantized_model.save_pretrained(OUTPUT_PATH)
tokenizer.save_pretrained(OUTPUT_PATH)
print(f"✅ GPTQ INT8 양자화 완료: {OUTPUT_PATH}")
