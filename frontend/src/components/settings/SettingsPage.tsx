"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import {
  Store, Upload, LogOut, Plus, CheckCircle2,
  Bell, Shield, ChevronRight, MessageSquare, Star, RefreshCw
} from "lucide-react"
import { listStores, createStore, uploadSales, uploadCosts, addReviewSource, collectReviews, uploadReviewCsv } from "@/lib/api"
import type { Store as StoreType } from "@/lib/types"
import { AppShell } from "@/components/layout/AppShell"
import { Badge } from "@/components/ui/Badge"

interface Props { store: StoreType }

const CATEGORIES = [
  { value: "cafe", label: "카페" },
  { value: "restaurant", label: "음식점" },
  { value: "bakery", label: "제과·베이커리" },
  { value: "beauty", label: "미용" },
  { value: "retail", label: "소매" },
  { value: "other", label: "기타" },
]

export function SettingsPage({ store }: Props) {
  const [allStores, setAllStores] = useState<StoreType[]>([])
  const [addingStore, setAddingStore] = useState(false)
  const [newStore, setNewStore] = useState({ name: "", category: "cafe", address: "", open_months: 12, monthly_avg_revenue: 10000000 })
  const [saving, setSaving] = useState(false)
  const router = useRouter()

  useEffect(() => {
    listStores().then(r => setAllStores(r.data)).catch(() => {})
  }, [])

  const handleAddStore = async () => {
    if (!newStore.name) return
    setSaving(true)
    try {
      await createStore(newStore)
      const r = await listStores()
      setAllStores(r.data)
      setAddingStore(false)
      setNewStore({ name: "", category: "cafe", address: "", open_months: 12, monthly_avg_revenue: 10000000 })
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    router.push("/login")
  }

  const handleSwitchStore = (s: StoreType) => {
    router.push(`/dashboard/${s.id}`)
  }

  return (
    <AppShell store={store}>
      <div className="p-5 lg:px-10 lg:py-8 xl:px-12 2xl:px-16 w-full bg-white min-h-screen">
        <div className="mb-6">
          <h1 className="text-xl lg:text-2xl font-extrabold tracking-tight">내 정보</h1>
          <p className="text-sm text-slate-400 mt-0.5">계정 및 사업장 설정</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)] 2xl:grid-cols-[minmax(0,1fr)_minmax(460px,0.85fr)] gap-5 xl:gap-7">

          {/* 사업장 목록 */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-50">
              <div className="flex items-center gap-2 text-[13.5px] font-extrabold text-slate-700">
                <Store size={15} className="text-blue-500" />등록 사업장
              </div>
              <button
                onClick={() => setAddingStore(v => !v)}
                className="flex items-center gap-1.5 text-[12px] font-bold text-blue-600 hover:text-blue-700"
              >
                <Plus size={14} />추가
              </button>
            </div>

            {addingStore && (
              <div className="px-5 py-4 border-b border-slate-50 bg-blue-50/50 space-y-3">
                <input
                  placeholder="상호명"
                  value={newStore.name}
                  onChange={e => setNewStore(p => ({...p, name: e.target.value}))}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map(c => (
                    <button
                      key={c.value}
                      onClick={() => setNewStore(p => ({...p, category: c.value}))}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold border transition-colors ${
                        newStore.category === c.value
                          ? "border-blue-500 bg-blue-50 text-blue-700"
                          : "border-slate-200 text-slate-500"
                      }`}
                    >{c.label}</button>
                  ))}
                </div>
                <input
                  placeholder="주소 (예: 전주시 완산구 효자동)"
                  value={newStore.address}
                  onChange={e => setNewStore(p => ({...p, address: e.target.value}))}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleAddStore}
                  disabled={saving || !newStore.name}
                  className="w-full py-2.5 rounded-xl bg-blue-600 text-white font-bold text-[13px] disabled:opacity-50"
                >
                  {saving ? "저장 중..." : "사업장 추가"}
                </button>
              </div>
            )}

            <div className="divide-y divide-slate-50">
              {allStores.map(s => (
                <div
                  key={s.id}
                  className={`flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50 cursor-pointer transition-colors ${
                    s.id === store.id ? "bg-blue-50/40" : ""
                  }`}
                  onClick={() => handleSwitchStore(s)}
                >
                  <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center text-[14px] font-bold text-blue-600 flex-shrink-0">
                    {s.name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13.5px] font-semibold text-slate-800 truncate">{s.name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5 truncate">{s.address || s.category}</div>
                  </div>
                  {s.id === store.id
                    ? <Badge variant="blue" className="text-[10.5px]">현재</Badge>
                    : <ChevronRight size={15} className="text-slate-300" />
                  }
                </div>
              ))}
              {allStores.length === 0 && (
                <div className="text-center py-8 text-sm text-slate-400">등록된 사업장이 없습니다.</div>
              )}
            </div>
          </div>

          {/* 데이터 업로드 + 리뷰 */}
          <div className="space-y-4">
            <DataUploadCard store={store} />
            <ReviewConnectorCard store={store} />

            {/* 알림 설정 */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-50 text-[13.5px] font-extrabold text-slate-700">
                <Bell size={15} className="text-blue-500" />알림 설정
              </div>
              {[
                { label: "현금흐름 위험 알림", desc: "현금 유지 기간이 14일 미만일 때" },
                { label: "리뷰 부정 신호 증가", desc: "부정 키워드가 급증할 때" },
                { label: "진단 결과 갱신", desc: "새 데이터 처리 완료 시" },
              ].map((item, i) => (
                <div key={i} className={`flex items-center justify-between px-5 py-3.5 ${i > 0 ? "border-t border-slate-50" : ""}`}>
                  <div>
                    <div className="text-[13px] font-semibold text-slate-700">{item.label}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{item.desc}</div>
                  </div>
                  <button className="w-11 h-6 rounded-full bg-blue-600 relative transition-colors flex-shrink-0">
                    <span className="absolute right-0.5 top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 계정 섹션 */}
        <div className="mt-5 bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-50 text-[13.5px] font-extrabold text-slate-700">
            <Shield size={15} className="text-blue-500" />계정
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-5 py-4 text-left hover:bg-red-50 text-red-500 transition-colors"
          >
            <LogOut size={16} />
            <span className="text-[13.5px] font-semibold">로그아웃</span>
          </button>
        </div>
      </div>
    </AppShell>
  )
}

function ReviewConnectorCard({ store }: { store: StoreType }) {
  const [platform, setPlatform] = useState<"naver"|"google"|"manual">("naver")
  const [sourceUrl, setSourceUrl] = useState("")
  const [placeId, setPlaceId] = useState("")
  const [consent, setConsent] = useState(false)
  const [reviewFile, setReviewFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [collecting, setCollecting] = useState(false)
  const [msg, setMsg] = useState<{type:"ok"|"err"; text:string}|null>(null)

  const showMsg = (type: "ok"|"err", text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const handleRegister = async () => {
    if (!consent) return showMsg("err", "리뷰 수집 동의가 필요합니다")
    if (platform !== "manual" && !sourceUrl && !placeId) return showMsg("err", "URL 또는 Place ID를 입력해 주세요")
    setSaving(true)
    try {
      await addReviewSource(store.id, {
        platform,
        source_url: sourceUrl || null,
        place_id: placeId || null,
        consent_given: consent,
        collection_method: platform === "google" ? "api" : platform === "naver" ? "playwright" : "csv",
      })
      showMsg("ok", "리뷰 출처가 등록됐습니다")
      setSourceUrl(""); setPlaceId(""); setConsent(false)
    } catch {
      showMsg("err", "등록 실패. 다시 시도해 주세요")
    } finally { setSaving(false) }
  }

  const handleCollect = async () => {
    setCollecting(true)
    try {
      await collectReviews(store.id)
      showMsg("ok", "리뷰 수집을 시작했습니다. 잠시 후 대시보드에서 확인하세요")
    } catch {
      showMsg("err", "수집 실패. 리뷰 출처를 먼저 등록해 주세요")
    } finally { setCollecting(false) }
  }

  const handleCsvUpload = async () => {
    if (!reviewFile) return
    setSaving(true)
    try {
      await uploadReviewCsv(store.id, platform, reviewFile)
      showMsg("ok", `리뷰 CSV 업로드 완료 (${reviewFile.name})`)
      setReviewFile(null)
    } catch {
      showMsg("err", "업로드 실패")
    } finally { setSaving(false) }
  }

  const PLATFORMS = [
    { value: "naver", label: "네이버 플레이스" },
    { value: "google", label: "Google Maps" },
    { value: "manual", label: "CSV 직접 업로드" },
  ] as const

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-50">
        <div className="flex items-center gap-2 text-[13.5px] font-extrabold text-slate-700">
          <MessageSquare size={15} className="text-amber-500" />리뷰 연결 (Review Connector)
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* 플랫폼 선택 */}
        <div>
          <div className="text-xs font-bold text-slate-500 mb-2">플랫폼 선택</div>
          <div className="flex gap-2 flex-wrap">
            {PLATFORMS.map(p => (
              <button key={p.value} onClick={() => setPlatform(p.value)}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold border transition-colors ${
                  platform === p.value ? "border-amber-400 bg-amber-50 text-amber-700" : "border-slate-200 text-slate-500"
                }`}>{p.label}</button>
            ))}
          </div>
        </div>

        {platform === "naver" && (
          <div>
            <div className="text-xs font-bold text-slate-500 mb-1.5">네이버 플레이스 URL</div>
            <input value={sourceUrl} onChange={e => setSourceUrl(e.target.value)}
              placeholder="https://place.naver.com/restaurant/123456"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] bg-white focus:outline-none focus:ring-2 focus:ring-amber-400" />
            <div className="text-[10.5px] text-slate-400 mt-1">네이버 플레이스에서 본인 매장 URL을 복사해 붙여넣으세요</div>
          </div>
        )}

        {platform === "google" && (
          <div>
            <div className="text-xs font-bold text-slate-500 mb-1.5">Google Place ID</div>
            <input value={placeId} onChange={e => setPlaceId(e.target.value)}
              placeholder="ChIJxxxxxxxxxxxxxxx"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] bg-white focus:outline-none focus:ring-2 focus:ring-amber-400" />
            <div className="text-[10.5px] text-slate-400 mt-1">Google Maps에서 '공유 → 지도 퍼가기'에서 Place ID를 확인하세요</div>
          </div>
        )}

        {platform === "manual" && (
          <div>
            <div className="text-xs font-bold text-slate-500 mb-1.5">리뷰 CSV 파일</div>
            <label className={`flex items-center gap-3 p-3 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
              reviewFile ? "border-amber-300 bg-amber-50" : "border-slate-200 hover:border-amber-300"
            }`}>
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${reviewFile ? "bg-amber-100 text-amber-600" : "bg-slate-100 text-slate-400"}`}>
                {reviewFile ? <CheckCircle2 size={18}/> : <Upload size={18}/>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold">{reviewFile ? reviewFile.name : "CSV 파일 선택"}</div>
                <div className="text-[10.5px] text-slate-400">컬럼: platform, date, rating, text</div>
              </div>
              <input type="file" accept=".csv" className="hidden" onChange={e => setReviewFile(e.target.files?.[0] ?? null)}/>
            </label>
          </div>
        )}

        {/* 동의 체크박스 */}
        {platform !== "manual" && (
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-amber-500 flex-shrink-0"/>
            <div className="text-[12px] text-slate-600 leading-relaxed">
              <span className="font-semibold">본인 매장의 공개 리뷰 수집에 동의합니다.</span><br/>
              <span className="text-slate-400">수집된 리뷰는 사업 상태 분석에만 사용되며, 개인 식별 정보는 저장하지 않습니다.</span>
            </div>
          </label>
        )}

        {/* 메시지 */}
        {msg && (
          <div className={`text-[12px] font-semibold px-3 py-2 rounded-xl ${
            msg.type === "ok" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"
          }`}>{msg.text}</div>
        )}

        {/* 버튼 */}
        <div className="flex gap-2">
          {platform === "manual" ? (
            <button onClick={handleCsvUpload} disabled={saving || !reviewFile}
              className="flex-1 py-2.5 rounded-xl bg-amber-500 text-white font-bold text-[13px] disabled:opacity-50">
              {saving ? "업로드 중..." : "CSV 업로드"}
            </button>
          ) : (
            <button onClick={handleRegister} disabled={saving}
              className="flex-1 py-2.5 rounded-xl bg-amber-500 text-white font-bold text-[13px] disabled:opacity-50">
              {saving ? "등록 중..." : "출처 등록"}
            </button>
          )}
          <button onClick={handleCollect} disabled={collecting}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-100 text-slate-700 font-semibold text-[13px] disabled:opacity-50">
            <RefreshCw size={13} className={collecting ? "animate-spin" : ""}/>{collecting ? "수집 중" : "수집 시작"}
          </button>
        </div>
      </div>
    </div>
  )
}

function DataUploadCard({ store }: { store: StoreType }) {
  const [salesFile, setSalesFile] = useState<File | null>(null)
  const [costFile, setCostFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [done, setDone] = useState(false)

  const handleUpload = async () => {
    if (!salesFile && !costFile) return
    setUploading(true)
    try {
      if (salesFile) await uploadSales(store.id, salesFile)
      if (costFile) await uploadCosts(store.id, costFile)
      setDone(true)
      setTimeout(() => setDone(false), 3000)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-50 text-[13.5px] font-extrabold text-slate-700">
        <Upload size={15} className="text-blue-500" />데이터 업로드
      </div>
      <div className="p-5 space-y-3">
        {[
          { label: "매출 CSV", file: salesFile, onFile: setSalesFile, hint: "date, hour, amount, channel" },
          { label: "비용 CSV", file: costFile, onFile: setCostFile, hint: "date, type, category, amount" },
        ].map(({ label, file, onFile, hint }) => (
          <label key={label} className={`flex items-center gap-3 p-3 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
            file ? "border-green-300 bg-green-50" : "border-slate-200 hover:border-blue-300 hover:bg-blue-50/30"
          }`}>
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${file ? "bg-green-100 text-green-600" : "bg-slate-100 text-slate-400"}`}>
              {file ? <CheckCircle2 size={18} /> : <Upload size={18} />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-semibold text-slate-700">{label}</div>
              <div className="text-[11px] text-slate-400 truncate">{file ? file.name : hint}</div>
            </div>
            <input type="file" accept=".csv" className="hidden" onChange={e => onFile(e.target.files?.[0] ?? null)} />
          </label>
        ))}
        {(salesFile || costFile) && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full py-2.5 rounded-xl bg-blue-600 text-white font-bold text-[13px] disabled:opacity-50"
          >
            {uploading ? "업로드 중..." : done ? "완료" : "업로드하기"}
          </button>
        )}
      </div>
    </div>
  )
}
