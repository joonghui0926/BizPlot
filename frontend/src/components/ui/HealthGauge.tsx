"use client"
import { getHealthLevel, getStrokeColor } from "@/lib/utils"

interface Props {
  score: number
  size?: number
  showLabel?: boolean
}

export function HealthGauge({ score, size = 120, showLabel = true }: Props) {
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const strokeOffset = circumference - progress
  const color = getStrokeColor(score)
  const { label } = getHealthLevel(score)

  // 크기에 비례한 폰트 (작은 게이지에서 깨지지 않도록)
  const valueSize = Math.round(size * 0.30)
  const labelSize = Math.max(9, Math.round(size * 0.105))
  const stroke = Math.max(7, Math.round(size * 0.10))
  const showInnerLabel = showLabel && size >= 80   // 작은 게이지는 숫자만

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 120 120" width={size} height={size}>
        <circle cx="60" cy="60" r={radius} fill="none" stroke="#E6EBF2" strokeWidth={stroke} />
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeOffset}
          transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="font-extrabold tabular-nums" style={{ color, fontSize: valueSize }}>
          {Math.round(score)}
        </span>
        {showInnerLabel && (
          <span className="text-slate-400 font-semibold mt-1" style={{ fontSize: labelSize }}>{label}</span>
        )}
      </div>
    </div>
  )
}
