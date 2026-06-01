"""
FinPilot QLoRA 파인튜닝
Base: Qwen/Qwen3.6-27B
GPU: A6000 48GB (CUDA_VISIBLE_DEVICES=2)  ← vLLM은 GPU 0,1 사용 중 (tensor parallel)
"""
import os
import torch
import json
from pathlib import Path
from datetime import datetime

# GPU 2 사용 (GPU 0,1은 vLLM tensor parallel 점유 중)
os.environ["CUDA_VISIBLE_DEVICES"] = "2"

MODEL_PATH = "/SSD/guest/chojoonghui/FinPilot/models/Qwen3.6-27B"
TRAIN_PATH = "/SSD/guest/chojoonghui/FinPilot/data/training/train.jsonl"
VAL_PATH   = "/SSD/guest/chojoonghui/FinPilot/data/training/val.jsonl"
OUTPUT_DIR = "/SSD/guest/chojoonghui/FinPilot/models/finpilot-qwen3.6-27b"

# ── 학습 설정 ──────────────────────────────────────────────────────
LORA_R = 16          # LoRA rank
LORA_ALPHA = 32      # LoRA alpha
LORA_DROPOUT = 0.05
MAX_SEQ_LEN = 2048
BATCH_SIZE = 1        # A6000 48GB에서 27B 4-bit: batch 1
GRAD_ACCUM = 8        # effective batch 8
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
WARMUP_STEPS = 50
SAVE_STEPS = 100
EVAL_STEPS = 100
MAX_STEPS = 300       # ~450샘플 * 3epoch / batch8 ≈ 169 steps → 더 많이

print(f"FinPilot QLoRA 파인튜닝 시작")
print(f"모델: {MODEL_PATH}")
print(f"GPU: {os.environ['CUDA_VISIBLE_DEVICES']} ({torch.cuda.get_device_name(0)})")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

from transformers import (
    AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from datasets import Dataset

# ── 1. 데이터 로드 ──────────────────────────────────────────────────
def load_jsonl(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def format_messages(sample: dict, tokenizer) -> str:
    """채팅 템플릿 적용"""
    messages = sample["messages"]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}

train_raw = load_jsonl(TRAIN_PATH)
val_raw   = load_jsonl(VAL_PATH)
print(f"\n학습 데이터: {len(train_raw)}개, 검증: {len(val_raw)}개")

# ── 2. 토크나이저 ───────────────────────────────────────────────────
print("\n토크나이저 로드 중...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,
    padding_side="right",
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.model_max_length = MAX_SEQ_LEN

# 데이터셋 변환
train_formatted = [format_messages(s, tokenizer) for s in train_raw]
val_formatted   = [format_messages(s, tokenizer) for s in val_raw]
train_dataset = Dataset.from_list(train_formatted)
val_dataset   = Dataset.from_list(val_formatted)

# ── 3. 모델 4-bit 로드 ─────────────────────────────────────────────
print("모델 4-bit 로드 중... (약 2~3분 소요)")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
)
model = prepare_model_for_kbit_training(model)
print(f"모델 로드 완료. 파라미터: {sum(p.numel() for p in model.parameters())/1e9:.1f}B")

# ── 4. LoRA 설정 ────────────────────────────────────────────────────
print("\nLoRA 설정 중...")
# Qwen3 계열 target modules
lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ── 5. 학습 설정 (TRL 1.5.x SFTConfig) ─────────────────────────────
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LEARNING_RATE,
    lr_scheduler_type="cosine",
    warmup_steps=WARMUP_STEPS,
    logging_steps=20,
    save_steps=SAVE_STEPS,
    eval_steps=EVAL_STEPS,
    eval_strategy="steps",
    save_total_limit=3,
    load_best_model_at_end=True,
    bf16=True,
    tf32=True,
    gradient_checkpointing=False,
    dataloader_num_workers=2,
    optim="paged_adamw_8bit",
    report_to="none",
    max_steps=MAX_STEPS,
    dataset_text_field="text",
    packing=False,
)

# ── 6. SFTTrainer ───────────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    args=training_args,
)

# ── 7. 학습 실행 ────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"파인튜닝 시작 ({MAX_STEPS} steps)")
print(f"예상 시간: GPU A6000 기준 약 2~3시간")
print(f"{'='*60}\n")

trainer.train()

# ── 8. 저장 ─────────────────────────────────────────────────────────
print("\n어댑터 저장 중...")
adapter_path = f"{OUTPUT_DIR}/final_adapter"
trainer.model.save_pretrained(adapter_path)
tokenizer.save_pretrained(adapter_path)
print(f"✅ 어댑터 저장: {adapter_path}")

# ── 9. 병합 (vLLM 서빙용) ───────────────────────────────────────────
print("\n어댑터 병합 중 (vLLM 서빙용)...")
from peft import PeftModel
from transformers import AutoModelForCausalLM

base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    device_map="cpu",  # 병합은 CPU에서
)
merged_model = PeftModel.from_pretrained(base_model, adapter_path)
merged_model = merged_model.merge_and_unload()

merged_path = "/SSD/guest/chojoonghui/FinPilot/models/finpilot-qwen3.6-27b-merged"
merged_model.save_pretrained(merged_path, safe_serialization=True)
tokenizer.save_pretrained(merged_path)
print(f"✅ 병합 모델 저장: {merged_path}")
print(f"\n파인튜닝 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
