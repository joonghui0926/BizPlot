# FinPilot 외부 배포 가이드 (KAIST 내부망 → www.xxx.kr 공개)

KAIST 서버(143.248.47.23)는 외부에서 직접 접속이 안 되지만 **아웃바운드는 열려 있어**,
서버가 바깥으로 거는 **Cloudflare 역터널**로 와이파이 무관하게 누구나 접속하게 만든다.
Cloudflare Tunnel은 HTTPS를 자동 제공하므로 **PWA(서비스워커/홈화면 추가) 요건도 충족**된다.

```
[외부 사용자 휴대폰/셀룰러]
        │ https://www.xxx.kr
        ▼
[Cloudflare 엣지] ──(역터널, 서버가 outbound로 연결)──► [KAIST 서버]
                                                          Next.js :3000
                                                          └ /api → FastAPI :8000
                                                          FastAPI → Ollama :11434 (GPU7)
```

> 프론트(:3000)만 노출하면 된다. 브라우저는 `/api`(상대경로)로만 호출하고,
> Next.js가 이를 서버사이드에서 `localhost:8000`으로 프록시하기 때문이다(`next.config.ts`).

---

## A. 지금 당장 테스트 (계정·도메인 불필요)

```bash
# 1) 서비스 기동 (DB·Redis·Ollama·백엔드·프론트)
bash scripts/startup.sh        # 또는 scripts/start.sh

# 2) 프론트는 PWA가 prod 빌드에서 안정적이므로 build 후 start 권장
cd frontend && npm run build && npm run start &   # :3000

# 3) 임시 공개 URL 발급 (외부에서 바로 접속됨)
bash scripts/tunnel_quick.sh
#   → https://랜덤.trycloudflare.com 출력 → 휴대폰 셀룰러로 접속해 PWA 설치 테스트
```

## B. 영구 배포 (www.xxx.kr)

### 1) .kr 도메인 구매 — **사장님 직접** (결제 필요)
- 가비아(gabia.com) 또는 후이즈(whois.co.kr)에서 `xxx.kr` 등록 (연 1~2만원대)
- Cloudflare는 .kr 직접 등록 불가 → 위 등록대행사에서 산 뒤 **네임서버만 Cloudflare로 변경**

### 2) Cloudflare 가입 + 도메인 추가 — **사장님 직접** (무료)
- dash.cloudflare.com 가입 → "Add a site"에 `xxx.kr` 입력 (Free 플랜)
- Cloudflare가 알려주는 네임서버 2개(예: `xxx.ns.cloudflare.com`)를
  가비아 → 도메인 관리 → 네임서버 설정에 입력 (반영 수십분~수시간)

### 3) 터널 생성 — 서버에서 (cloudflared 이미 준비됨: `./bin/cloudflared`)
```bash
cd /SSD/guest/chojoonghui/FinPilot
./bin/cloudflared tunnel login              # 브라우저 링크 → Cloudflare 로그인·xxx.kr 인가
./bin/cloudflared tunnel create finpilot    # TUNNEL_ID 발급 (~/.cloudflared/<ID>.json 생성)

# 설정파일 작성
cp scripts/cloudflared.config.example.yml ~/.cloudflared/config.yml
#   → <TUNNEL_ID> 와 <도메인> 을 실제 값으로 수정

# DNS 라우팅 등록 (CNAME 자동 생성)
./bin/cloudflared tunnel route dns finpilot www.xxx.kr
./bin/cloudflared tunnel route dns finpilot xxx.kr

# 실행
bash scripts/tunnel_named.sh
```
→ 이제 `https://www.xxx.kr` 로 전 세계 누구나 접속. (백그라운드 상시 실행은 nohup/systemd 권장)

---

## C. Ollama 온디맨드(GPU7) 동작
- Ollama는 **요청이 오면 그때 모델을 GPU7 VRAM에 로드**하고, 유휴 시 자동 언로드한다(기본 5분).
  즉 "요청 오면 띄운다"가 기본 동작이며 `scripts/startup.sh`가 `CUDA_VISIBLE_DEVICES=7`로 고정한다.
- 언로드 타이밍 조절: `OLLAMA_KEEP_ALIVE=30m`(데모 중 끊김 방지) / `=0`(즉시 언로드) 환경변수로 serve 기동.

---

## D. 운영 주의
- **상시 실행**: 터널/프론트/백엔드를 `nohup` 또는 systemd 사용자 서비스로 등록해 SSH 끊겨도 유지.
- **공모전 시연영상**: 규칙상 대회명/팀명으로 검색되는 공개 영상 금지 → 유튜브 '미등록(Unlisted)'로.
- **보안**: 외부 공개 즉시 `backend/.env`·`frontend/.env.local`의 실제 API 키 노출 위험 ↑ → 키 회수/교체 권장.
- 첫 접속 시 모델 로드(수초~십수초) 지연 가능 → 시연 직전 더미 요청 1회로 GPU 예열.
