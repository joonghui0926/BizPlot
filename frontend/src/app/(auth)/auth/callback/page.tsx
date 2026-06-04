"use client"

import { Suspense, useEffect } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2 } from "lucide-react"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import { listStores } from "@/lib/api"

function OAuthCallbackContent() {
  const router = useRouter()
  const params = useSearchParams()
  const token = params.get("token")
  const oauthError = params.get("error")
  const hasError = Boolean(oauthError || !token)

  useEffect(() => {
    if (oauthError || !token) {
      return
    }

    localStorage.setItem("token", token)

    async function goNext() {
      try {
        const stores = await listStores()
        const list = stores.data || []
        router.replace(list.length > 0 ? `/dashboard/${list[0].id}` : "/onboarding")
      } catch {
        router.replace("/onboarding")
      }
    }

    goNext()
  }, [oauthError, router, token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#EEF2FB] to-white p-6">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white">
          <FinPilotMark size={38} color="white" />
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight">로그인 처리 중</h1>
        {hasError ? (
          <>
            <p className="mt-3 text-sm text-red-500">소셜 로그인에 실패했습니다. 다시 시도해 주세요.</p>
            <Link
              href="/login"
              className="mt-6 inline-flex h-11 items-center justify-center rounded-lg bg-blue-600 px-5 text-sm font-bold text-white hover:bg-blue-700"
            >
              로그인으로 돌아가기
            </Link>
          </>
        ) : (
          <div className="mt-5 flex items-center justify-center gap-2 text-sm font-medium text-slate-500">
            <Loader2 size={18} className="animate-spin" />
            계정 정보를 확인하고 있습니다.
          </div>
        )}
      </div>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <OAuthCallbackContent />
    </Suspense>
  )
}
