import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export async function downloadWithAuth(url: string, filename: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`다운로드 실패 (${res.status})`)
  const blob = await res.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = objUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objUrl)
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number): string {
  if (value >= 100_000_000) return `₩${(value / 100_000_000).toFixed(1)}억`
  if (value >= 10_000) return `₩${(value / 10_000).toFixed(0)}만`
  return `₩${value.toLocaleString()}`
}

export function formatNumber(value: number): string {
  return value.toLocaleString()
}

export function getRiskLevel(score: number): { label: string; color: string; bg: string } {
  if (score >= 70) return { label: "높음", color: "text-red-600", bg: "bg-red-50" }
  if (score >= 40) return { label: "중간", color: "text-amber-600", bg: "bg-amber-50" }
  return { label: "낮음", color: "text-green-600", bg: "bg-green-50" }
}

export function getHealthLevel(score: number): { label: string; color: string } {
  if (score >= 75) return { label: "양호", color: "text-green-600" }
  if (score >= 50) return { label: "주의", color: "text-amber-600" }
  return { label: "위험", color: "text-red-600" }
}

export function getStrokeColor(score: number): string {
  if (score >= 75) return "#357A54"
  if (score >= 50) return "#3253E9"
  return "#B85B5B"
}
