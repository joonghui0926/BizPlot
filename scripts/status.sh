#!/bin/bash
# FinPilot 서비스 상태 확인

echo "=== FinPilot Agent Status ==="
echo ""

# PostgreSQL
pg_ctl -D /SSD/guest/chojoonghui/FinPilot/data/postgres status 2>/dev/null \
  && echo "✓ PostgreSQL: running" \
  || echo "✗ PostgreSQL: stopped"

# Redis
/home/guest/anaconda3/envs/finpilot-llm/bin/redis-cli ping 2>/dev/null | grep -q PONG \
  && echo "✓ Redis: running" \
  || echo "✗ Redis: stopped"

# Backend
curl -sf http://localhost:8000/api/health > /dev/null 2>&1 \
  && echo "✓ FastAPI Backend: http://localhost:8000" \
  || echo "✗ FastAPI Backend: stopped"

# Frontend
curl -sf http://localhost:3000/login > /dev/null 2>&1 \
  && echo "✓ Next.js Frontend: http://localhost:3000" \
  || echo "✗ Next.js Frontend: stopped"

# vLLM
curl -sf http://localhost:8001/health > /dev/null 2>&1 \
  && echo "✓ vLLM Server: http://localhost:8001" \
  || echo "△ vLLM Server: not ready (fallback mode active)"

echo ""
echo "GPU Usage:"
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader | head -4
echo ""
echo "Logs:"
echo "  Backend:  /tmp/finpilot-api.log"
echo "  Frontend: /tmp/finpilot-frontend.log"
echo "  vLLM:     /tmp/vllm_new.log"
