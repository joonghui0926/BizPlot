/* FinPilot PWA Service Worker
 * - 설치 가능(installability) 요건 충족용 fetch 핸들러 포함
 * - /api 요청은 캐시하지 않음(항상 네트워크) — 로그인 토큰·실시간 진단 데이터 보호
 * - 정적 자산은 stale-while-revalidate, 페이지 이동은 network-first
 */
const CACHE = "finpilot-v1";
const APP_SHELL = ["/", "/manifest.json", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(APP_SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // GET 외 / 외부 오리진 / API 요청은 그대로 네트워크 통과 (캐시 X)
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api")) {
    return;
  }

  // 페이지 이동: network-first → 실패 시 캐시 → 그래도 없으면 "/"
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match("/")))
    );
    return;
  }

  // 정적 자산: stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
