"use client"
import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Store, MapPin, Calendar, Wallet, Upload, ArrowRight, Check, Search, X } from "lucide-react"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import { createStore, uploadSales, uploadCosts } from "@/lib/api"

const CATEGORIES = [
  { value: "cafe", label: "카페", emoji: "☕" },
  { value: "restaurant", label: "음식점", emoji: "🍽" },
  { value: "bakery", label: "제과·베이커리", emoji: "🥐" },
  { value: "beauty", label: "미용·뷰티", emoji: "✂️" },
  { value: "retail", label: "소매", emoji: "🛍" },
  { value: "other", label: "기타", emoji: "🏪" },
]

interface KakaoPlace { place_name: string; address_name: string; road_address_name: string }

export default function OnboardingPage() {
  const [step, setStep] = useState(0)
  const [storeData, setStoreData] = useState({
    name: "", category: "cafe", address: "", open_months: 12, monthly_avg_revenue: 10000000,
  })
  const [storeId, setStoreId] = useState<string | null>(null)
  const [salesFile, setSalesFile] = useState<File | null>(null)
  const [costFile, setCostFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleStoreSubmit = async () => {
    setLoading(true)
    try {
      const r = await createStore(storeData)
      setStoreId(r.data.id)
      setStep(1)
    } finally {
      setLoading(false)
    }
  }

  const handleDataUpload = async () => {
    if (!storeId) return
    setLoading(true)
    try {
      if (salesFile) await uploadSales(storeId, salesFile)
      if (costFile) await uploadCosts(storeId, costFile)
      router.push(`/dashboard/${storeId}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-[#EEF2FB] to-white">

      {/* Left panel (desktop) */}
      <div className="hidden lg:flex flex-col justify-between w-[400px] bg-gradient-to-br from-blue-700 to-blue-900 p-12 flex-shrink-0">
        <div className="flex items-center gap-3">
          <FinPilotMark size={44} color="rgba(255,255,255,0.9)" />
          <span className="text-2xl font-extrabold text-white tracking-tight">BizPlot</span>
        </div>
        <div>
          <div className="text-white/60 text-sm font-semibold mb-3 tracking-wide">STEP {step + 1} / 2</div>
          <h2 className="text-white text-2xl font-extrabold leading-tight mb-2">
            {step === 0 ? "사업 정보 입력" : "데이터 등록"}
          </h2>
          <p className="text-white/70 text-sm leading-relaxed">
            {step === 0
              ? "업종, 지역 정보를 입력하면 공공 데이터와 결합해 상권·날씨·경쟁점포 신호를 분석합니다."
              : "매출·비용 CSV를 올리면 시간대별 현금흐름 분석이 가능합니다. 나중에 올려도 됩니다."}
          </p>
        </div>
        <div className="flex gap-2">
          {[0, 1].map(i => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-8 bg-white" : i < step ? "w-5 bg-white/60" : "w-5 bg-white/20"}`} />
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Mobile header */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="text-[#3253E9]"><FinPilotMark size={36} /></div>
            <div>
              <div className="text-lg font-extrabold tracking-tight">사업 정보 등록</div>
              <div className="text-xs text-slate-400">Step {step + 1} / 2</div>
            </div>
          </div>

          {step === 0 ? (
            <StoreInfoStep data={storeData} onChange={setStoreData} />
          ) : (
            <DataUploadStep salesFile={salesFile} costFile={costFile} onSalesFile={setSalesFile} onCostFile={setCostFile} />
          )}

          <div className="mt-8 space-y-3">
            <button
              onClick={step === 0 ? handleStoreSubmit : handleDataUpload}
              disabled={loading || (step === 0 && !storeData.name)}
              className="flex items-center justify-center gap-2 w-full py-4 rounded-xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-40 hover:bg-blue-700 transition-colors"
            >
              {loading ? "처리 중..." : step === 0 ? <>다음 <ArrowRight size={18} /></> : <>진단 시작 <ArrowRight size={18} /></>}
            </button>
            {step === 1 && (
              <button onClick={() => router.push(`/dashboard/${storeId}`)} className="w-full py-3 text-sm font-semibold text-slate-400 hover:text-slate-600">
                나중에 업로드하기
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StoreInfoStep({ data, onChange }: { data: any; onChange: (d: any) => void }) {
  const [nameSuggestions, setNameSuggestions] = useState<KakaoPlace[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchTimer, setSearchTimer] = useState<NodeJS.Timeout | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const searchKakaoPlaces = async (query: string) => {
    if (!query || query.length < 2) { setNameSuggestions([]); return }
    const kakaoKey = process.env.NEXT_PUBLIC_KAKAO_REST_KEY
    if (!kakaoKey) return  // API 키 없으면 자동완성 건너뜀
    try {
      const r = await fetch(
        `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(query)}&size=5`,
        { headers: { Authorization: `KakaoAK ${kakaoKey}` } }
      )
      const d = await r.json()
      setNameSuggestions(d.documents || [])
      setShowSuggestions(true)
    } catch {
      setNameSuggestions([])
    }
  }

  const handleNameChange = (v: string) => {
    onChange({ ...data, name: v })
    if (searchTimer) clearTimeout(searchTimer)
    setSearchTimer(setTimeout(() => searchKakaoPlaces(v), 400))
  }

  const selectPlace = (place: KakaoPlace) => {
    onChange({ ...data, name: place.place_name, address: place.road_address_name || place.address_name })
    setShowSuggestions(false)
    setNameSuggestions([])
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 hidden lg:block">사업 정보 입력</h1>
      <p className="text-sm text-slate-400 mb-6 hidden lg:block">상권·날씨 데이터를 결합해 진단합니다.</p>

      <div className="space-y-5">
        {/* 상호명 (자동완성) */}
        <div>
          <label className="text-xs font-bold text-slate-700 block mb-1.5 flex items-center gap-1.5">
            <Store size={13} className="text-blue-500" />상호명
          </label>
          <div className="relative">
            <div className="relative">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                ref={inputRef}
                type="text"
                value={data.name}
                onChange={e => handleNameChange(e.target.value)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                placeholder="상호명 입력 (예: 봄날 카페)"
                className="w-full pl-9 pr-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {data.name && (
                <button onClick={() => onChange({ ...data, name: "" })} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500">
                  <X size={15} />
                </button>
              )}
            </div>
            {showSuggestions && nameSuggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-slate-200 rounded-xl shadow-lg z-50 mt-1 overflow-hidden">
                {nameSuggestions.map((p, i) => (
                  <button
                    key={i}
                    onMouseDown={() => selectPlace(p)}
                    className="w-full text-left px-4 py-3 hover:bg-blue-50 border-b border-slate-50 last:border-0"
                  >
                    <div className="text-[13.5px] font-semibold text-slate-800">{p.place_name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{p.road_address_name || p.address_name}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 업종 */}
        <div>
          <label className="text-xs font-bold text-slate-700 block mb-2">업종</label>
          <div className="grid grid-cols-3 gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.value}
                onClick={() => onChange({ ...data, category: cat.value })}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-[12.5px] font-semibold border transition-colors ${
                  data.category === cat.value
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-slate-200 text-slate-500 bg-white hover:border-slate-300"
                }`}
              >
                <span>{cat.emoji}</span>{cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* 주소 */}
        <div>
          <label className="text-xs font-bold text-slate-700 block mb-1.5 flex items-center gap-1.5">
            <MapPin size={13} className="text-blue-500" />사업장 주소
          </label>
          <input
            type="text"
            value={data.address}
            onChange={e => onChange({ ...data, address: e.target.value })}
            placeholder="전주시 완산구 효자동"
            className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[11px] text-slate-400 mt-1.5">상권·날씨 API 연결에 사용됩니다.</p>
        </div>

        {/* 영업 기간 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1.5 flex items-center gap-1.5">
              <Calendar size={13} className="text-blue-500" />영업 기간 (개월)
            </label>
            <input type="number" value={data.open_months}
              onChange={e => onChange({ ...data, open_months: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1.5 flex items-center gap-1.5">
              <Wallet size={13} className="text-blue-500" />월평균 매출 (만원)
            </label>
            <input type="number" value={Math.round(data.monthly_avg_revenue / 10000)}
              onChange={e => onChange({ ...data, monthly_avg_revenue: (parseInt(e.target.value) || 0) * 10000 })}
              className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function DataUploadStep({ salesFile, costFile, onSalesFile, onCostFile }: {
  salesFile: File | null; costFile: File | null
  onSalesFile: (f: File | null) => void; onCostFile: (f: File | null) => void
}) {
  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight mb-1 hidden lg:block">데이터 등록</h1>
      <p className="text-sm text-slate-400 mb-6 hidden lg:block">CSV를 올리면 시간대별 현금흐름까지 분석합니다.</p>

      <div className="space-y-3">
        {[
          { label: "매출 데이터", file: salesFile, onFile: onSalesFile, hint: "date, hour, amount, channel" },
          { label: "비용 데이터", file: costFile, onFile: onCostFile, hint: "date, type, category, amount" },
        ].map(({ label, file, onFile, hint }) => (
          <label key={label} className={`flex items-center gap-3.5 p-4 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
            file ? "border-green-300 bg-green-50" : "border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 bg-white"
          }`}>
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${file ? "bg-green-100 text-green-600" : "bg-blue-50 text-blue-400"}`}>
              {file ? <Check size={20} /> : <Upload size={20} />}
            </div>
            <div className="flex-1">
              <div className="text-[13.5px] font-bold text-slate-800">{label}</div>
              <div className="text-[11.5px] text-slate-400 mt-0.5">{file ? <span className="flex items-center gap-1"><Check size={12} />{file.name}</span> : hint}</div>
            </div>
            <input type="file" accept=".csv" className="hidden" onChange={e => onFile(e.target.files?.[0] ?? null)} />
          </label>
        ))}
      </div>

      <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
        <div className="text-xs font-bold text-slate-600 mb-1.5">CSV 예시</div>
        <code className="text-[11px] text-slate-500 block leading-relaxed">
          date,hour,amount,channel<br />
          2026-05-01,10,45000,pos<br />
          2026-05-01,14,62000,delivery
        </code>
      </div>
    </div>
  )
}
