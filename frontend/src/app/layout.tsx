import type { Metadata, Viewport } from "next"
import "./globals.css"
import { PWAInstaller } from "@/components/pwa/PWAInstaller"

export const metadata: Metadata = {
  title: "BizPlot Agent · AI CFO Platform",
  description: "소상공인의 금융 운영을 설계하는 AI CFO Platform",
  manifest: "/manifest.json",
  applicationName: "BizPlot",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "BizPlot" },
  icons: {
    icon: [
      { url: "/favicon.png", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  // 흰색 헤더와 맞춰 상단 파란 틴트(주소창·상태바 1px 라인) 제거
  themeColor: "#ffffff",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        {/* iOS 홈화면 아이콘 (불투명 파란 배경 PNG — 아이폰에서 정상 표시) */}
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="icon" href="/favicon.png" type="image/png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="BizPlot" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.css"
        />
      </head>
      <body style={{ fontFamily: "'Pretendard', -apple-system, sans-serif" }}>
        {children}
        <PWAInstaller />
      </body>
    </html>
  )
}
