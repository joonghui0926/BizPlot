"use client"
import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { listStores } from "@/lib/api"
import type { Store } from "@/lib/types"
import { DashboardPage } from "@/components/dashboard/DashboardPage"

export default function DashboardRoute() {
  const { storeId } = useParams<{ storeId: string }>()
  const [store, setStore] = useState<Store | null>(null)
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) { router.push("/login"); return }
    listStores().then(r => {
      const s = r.data.find((s: Store) => s.id === storeId)
      if (s) setStore(s)
      else if (r.data.length > 0) router.push(`/dashboard/${r.data[0].id}`)
      else router.push("/onboarding")
    }).catch(() => router.push("/onboarding"))
  }, [storeId])

  if (!store) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  return <DashboardPage store={store} />
}
