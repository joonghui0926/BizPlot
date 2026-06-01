#!/bin/bash
# FinPilot 부팅 시 자동 시작 스크립트
# GPU 7이 비어있을 때만 전체 서비스 기동

set -e

CONDA_ENV="finpilot-llm"
PYTHON="/home/guest/anaconda3/envs/$CONDA_ENV/bin/python"
BASE_DIR="/SSD/guest/chojoonghui/FinPilot"
PGDATA="$BASE_DIR/data/postgres"
REDIS_DIR="$BASE_DIR/data/redis"
BACKEND_DIR="$BASE_DIR/backend"
GGUF_MODEL="$BASE_DIR/models/finpilot-q4km.gguf"
MODELFILE="$BASE_DIR/models/Modelfile"
LOG_DIR="/tmp/finpilot-logs"
GPU_ID=7
THRESHOLD=500  # MiB 미만이면 빈 것으로 판단

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/startup.log") 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] FinPilot 시작"

# ── GPU 7 사용 여부 확인 ──────────────────────────────────────────
GPU_USED=$(nvidia-smi -i $GPU_ID --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')
GPU_TOTAL=$(nvidia-smi -i $GPU_ID --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')
echo "[GPU $GPU_ID] ${GPU_USED}MiB / ${GPU_TOTAL}MiB 사용 중"

if [ "${GPU_USED:-0}" -gt "$THRESHOLD" ]; then
    echo "[GPU $GPU_ID] 이미 사용 중 (${GPU_USED}MiB). 서비스 기동 건너뜀."
    exit 0
fi
echo "[GPU $GPU_ID] 비어있음 — 서비스 기동"

# ── 1. PostgreSQL ─────────────────────────────────────────────────
if ! /home/guest/anaconda3/envs/$CONDA_ENV/bin/pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
    echo "[1/5] PostgreSQL 시작..."
    /home/guest/anaconda3/envs/$CONDA_ENV/bin/pg_ctl -D "$PGDATA" -l "$PGDATA/../postgres.log" start
    sleep 3
else
    echo "[1/5] PostgreSQL 이미 실행 중"
fi

# ── 2. Redis ──────────────────────────────────────────────────────
if ! /home/guest/anaconda3/envs/$CONDA_ENV/bin/redis-cli ping > /dev/null 2>&1; then
    echo "[2/5] Redis 시작..."
    /home/guest/anaconda3/envs/$CONDA_ENV/bin/redis-server \
        --daemonize yes --port 6379 \
        --logfile "$REDIS_DIR/redis.log" --dir "$REDIS_DIR"
    sleep 1
else
    echo "[2/5] Redis 이미 실행 중"
fi

# ── 3. FastAPI 백엔드 ──────────────────────────────────────────────
echo "[3/5] FastAPI 백엔드 시작 (:8000)..."
pkill -f "uvicorn app.main" 2>/dev/null || true; sleep 1
cd "$BACKEND_DIR"
nohup $PYTHON -m uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/backend.log" 2>&1 &
echo "  Backend PID: $!"
sleep 3

# ── 4. Ollama (GPU 7) ─────────────────────────────────────────────
if [ -f "$GGUF_MODEL" ]; then
    echo "[4/5] Ollama 시작 (GPU $GPU_ID, :11434)..."
    pkill -f "ollama serve" 2>/dev/null || true; sleep 2

    CUDA_VISIBLE_DEVICES=$GPU_ID \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS="$BASE_DIR/models/ollama" \
    nohup ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
    echo "  Ollama PID: $!"
    sleep 5

    # 모델 등록 (첫 실행 시)
    OLLAMA_HOST=127.0.0.1:11434 ollama list 2>/dev/null | grep -q "finpilot" || {
        echo "  finpilot 모델 등록 중..."
        OLLAMA_HOST=127.0.0.1:11434 ollama create finpilot -f "$MODELFILE" 2>&1 | tail -3
    }
else
    echo "[4/5] GGUF 모델 없음 ($GGUF_MODEL) — Ollama 건너뜀"
    echo "      먼저 scripts/quantize_gguf.sh 실행 필요"
fi

# ── 5. Next.js 프론트엔드 ─────────────────────────────────────────
echo "[5/5] Next.js 프론트엔드 시작 (:3000)..."
pkill -f "next-server" 2>/dev/null || true; sleep 1
cd "$BASE_DIR/frontend"
nohup npm run start > "$LOG_DIR/frontend.log" 2>&1 &
echo "  Frontend PID: $!"

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 서비스 기동 완료"
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  Ollama:   http://localhost:11434"
echo "  외부접근 (포트 열려있을 때):"
echo "    http://143.248.47.23:8000 (API)"
echo "    http://143.248.47.23:3000 (Frontend)"
