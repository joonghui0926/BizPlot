#!/bin/bash
# ───────────────────────────────────────────────────────────────
# 즉시 외부 공개 (Cloudflare 계정·도메인 불필요)
# KAIST 내부망 서버를 바깥으로 노출 → 와이파이 무관하게 누구나 HTTPS 접속.
# 실행하면 https://xxxx.trycloudflare.com 임시 주소가 출력됩니다.
# (PWA 테스트용. 영구 www.xxx.kr 은 tunnel_named.sh 사용)
# ───────────────────────────────────────────────────────────────
set -e
BASE_DIR="/SSD/guest/chojoonghui/FinPilot"
PORT="${1:-3000}"   # 노출할 로컬 포트 (기본 프론트 3000)

echo "프론트(:$PORT)를 외부 HTTPS로 노출합니다..."
echo "출력되는 https://*.trycloudflare.com 주소로 외부(셀룰러 포함)에서 접속하세요."
echo ""
exec "$BASE_DIR/bin/cloudflared" tunnel --url "http://localhost:$PORT"
