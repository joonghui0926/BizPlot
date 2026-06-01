"use client"
import { useEffect, useState } from "react"

// beforeinstallprompt 이벤트 타입 (표준 미정의라 최소 선언)
interface BIPEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>
}

const BRAND = "#2563EB"

export function PWAInstaller() {
  const [deferred, setDeferred] = useState<BIPEvent | null>(null)
  const [isIOS, setIsIOS] = useState(false)
  const [show, setShow] = useState(false)
  const [iosGuide, setIosGuide] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return

    // 1) 서비스워커 등록
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {})
    }

    // 2) 이미 설치(홈화면 실행) 상태면 배너 표시 안 함
    const standalone =
      window.matchMedia?.("(display-mode: standalone)").matches ||
      // @ts-expect-error iOS 전용 비표준 속성
      window.navigator.standalone === true
    if (standalone) return

    // 3) 최근에 닫았으면 하루 동안 표시 안 함
    const dismissedAt = Number(localStorage.getItem("pwa_dismissed") || 0)
    if (Date.now() - dismissedAt < 24 * 60 * 60 * 1000) return

    // 4) iOS 판별 (iPadOS 13+ 는 Mac 으로 위장 → 터치포인트로 보강)
    const ua = window.navigator.userAgent
    const ios =
      /iphone|ipad|ipod/i.test(ua) ||
      (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)
    const isSafari = /^((?!chrome|android|crios|fxios).)*safari/i.test(ua)
    if (ios && isSafari) {
      setIsIOS(true)
      setShow(true)
    }

    // 5) Android/Chrome: 설치 프롬프트 가로채기
    const onBIP = (e: Event) => {
      e.preventDefault()
      setDeferred(e as BIPEvent)
      setShow(true)
    }
    window.addEventListener("beforeinstallprompt", onBIP)

    // 6) 설치 완료 시 배너 숨김
    const onInstalled = () => setShow(false)
    window.addEventListener("appinstalled", onInstalled)

    return () => {
      window.removeEventListener("beforeinstallprompt", onBIP)
      window.removeEventListener("appinstalled", onInstalled)
    }
  }, [])

  if (!show) return null

  const close = () => {
    setShow(false)
    setIosGuide(false)
    localStorage.setItem("pwa_dismissed", String(Date.now()))
  }

  const onInstall = async () => {
    if (isIOS) {
      setIosGuide(true)
      return
    }
    if (deferred) {
      await deferred.prompt()
      await deferred.userChoice
      setDeferred(null)
      setShow(false)
    }
  }

  return (
    <>
      {/* 설치 배너 */}
      <div style={S.banner}>
        <img src="/icons/icon-192.png" alt="BizPlot" width={40} height={40} style={S.icon} />
        <div style={S.text}>
          <div style={S.title}>홈 화면에 BizPlot 추가</div>
          <div style={S.sub}>앱처럼 바로 실행하세요</div>
        </div>
        <button onClick={onInstall} style={S.btn}>다운로드</button>
        <button onClick={close} aria-label="닫기" style={S.x}>✕</button>
      </div>

      {/* iOS 안내 오버레이 */}
      {iosGuide && (
        <div style={S.overlay} onClick={close}>
          <div style={S.sheet} onClick={(e) => e.stopPropagation()}>
            <img src="/icons/icon-192.png" alt="BizPlot" width={56} height={56} style={S.icon} />
            <div style={S.sheetTitle}>홈 화면에 추가하는 방법</div>
            <ol style={S.steps}>
              <li>하단의 <b>공유 버튼</b> <span style={S.share}>⬆️</span> 을 누르세요</li>
              <li>목록에서 <b>‘홈 화면에 추가’</b> 를 선택하세요</li>
              <li><b>‘추가’</b> 를 누르면 BizPlot 아이콘이 생깁니다</li>
            </ol>
            <button onClick={close} style={S.btnWide}>확인</button>
          </div>
        </div>
      )}
    </>
  )
}

const S: Record<string, React.CSSProperties> = {
  banner: {
    position: "fixed", left: 12, right: 12, bottom: 12, zIndex: 9999,
    display: "flex", alignItems: "center", gap: 12,
    background: "#fff", border: "1px solid #e2e8f0",
    boxShadow: "0 8px 30px rgba(15,23,42,0.18)", borderRadius: 14,
    padding: "10px 12px", maxWidth: 460, margin: "0 auto",
  },
  icon: { borderRadius: 10, flexShrink: 0 },
  text: { flex: 1, minWidth: 0 },
  title: { fontWeight: 800, fontSize: 14, color: "#0f172a" },
  sub: { fontSize: 12, color: "#64748b" },
  btn: {
    background: BRAND, color: "#fff", border: "none", borderRadius: 10,
    padding: "9px 16px", fontWeight: 700, fontSize: 13, cursor: "pointer", flexShrink: 0,
  },
  x: { background: "transparent", border: "none", color: "#94a3b8", fontSize: 14, cursor: "pointer", padding: 4 },
  overlay: {
    position: "fixed", inset: 0, zIndex: 10000, background: "rgba(15,23,42,0.55)",
    display: "flex", alignItems: "flex-end", justifyContent: "center",
  },
  sheet: {
    background: "#fff", borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: "24px 22px 28px", width: "100%", maxWidth: 460, textAlign: "center",
  },
  sheetTitle: { fontWeight: 800, fontSize: 17, color: "#0f172a", margin: "12px 0 8px" },
  steps: { textAlign: "left", color: "#334155", fontSize: 14, lineHeight: 1.9, paddingLeft: 20, margin: "8px 0 18px" },
  share: { display: "inline-block", padding: "0 4px" },
  btnWide: {
    background: BRAND, color: "#fff", border: "none", borderRadius: 12,
    padding: "13px 0", width: "100%", fontWeight: 700, fontSize: 15, cursor: "pointer",
  },
}
