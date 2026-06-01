#!/bin/bash
# FinPilot Agent 전체 서비스 시작 스크립트

set -e

CONDA_ENV="finpilot-llm"
BASE_DIR="/SSD/guest/chojoonghui/FinPilot"
PGDATA="$BASE_DIR/data/postgres"
REDIS_DIR="$BASE_DIR/data/redis"
BACKEND_DIR="$BASE_DIR/backend"

echo "=== FinPilot Agent Starting ==="

# PostgreSQL
if ! /home/guest/anaconda3/envs/$CONDA_ENV/bin/pg_ctl -D $PGDATA status > /dev/null 2>&1; then
    echo "[1/4] Starting PostgreSQL..."
    /home/guest/anaconda3/envs/$CONDA_ENV/bin/pg_ctl -D $PGDATA -l $PGDATA/../postgres.log start
    sleep 2
else
    echo "[1/4] PostgreSQL already running"
fi

# Redis
if ! /home/guest/anaconda3/envs/$CONDA_ENV/bin/redis-cli ping > /dev/null 2>&1; then
    echo "[2/4] Starting Redis..."
    /home/guest/anaconda3/envs/$CONDA_ENV/bin/redis-server \
        --daemonize yes --port 6379 \
        --logfile $REDIS_DIR/redis.log --dir $REDIS_DIR
    sleep 1
else
    echo "[2/4] Redis already running"
fi

# Backend
echo "[3/4] Starting FastAPI backend on :8000..."
cd $BACKEND_DIR
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
nohup /home/guest/anaconda3/envs/$CONDA_ENV/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --reload > /tmp/finpilot-api.log 2>&1 &
echo "  Backend PID: $!"
sleep 3

# Frontend
echo "[4/4] Starting Next.js frontend on :3000..."
cd $BASE_DIR/frontend
if [ -f package.json ]; then
    pkill -f "next-server" 2>/dev/null || true
    nohup npm run dev > /tmp/finpilot-frontend.log 2>&1 &
    echo "  Frontend PID: $!"
fi

echo ""
echo "=== Services started ==="
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/docs"
echo "  Frontend: http://localhost:3000"
