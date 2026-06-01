#!/bin/bash
# ───────────────────────────────────────────────────────────────
# Named Tunnel 실행 (www.xxx.kr 영구 배포)
# 사전: cloudflared.config.example.yml 참고해 ~/.cloudflared/config.yml 작성 +
#       tunnel login / create / route dns 완료해야 함 (scripts/DEPLOY.md 참고)
# ───────────────────────────────────────────────────────────────
set -e
BASE_DIR="/SSD/guest/chojoonghui/FinPilot"
CONFIG="${HOME}/.cloudflared/config.yml"

if [ ! -f "$CONFIG" ]; then
  echo "✗ $CONFIG 없음. scripts/cloudflared.config.example.yml 참고해 먼저 작성하세요."
  exit 1
fi

echo "Named tunnel 'finpilot' 기동 (config: $CONFIG)"
exec "$BASE_DIR/bin/cloudflared" tunnel --config "$CONFIG" run finpilot
