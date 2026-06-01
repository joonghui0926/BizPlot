import { DiagnosisProvider } from "@/components/diagnosis/DiagnosisContext"

// [storeId] 하위 모든 탭(대시보드·원인분석·전략·리포트·설정)을 감싸는 레이아웃.
// Next 레이아웃은 탭 이동 시에도 유지되므로, 진단 진행바 상태가 페이지를 넘나들어도 보존된다.
export default function StoreLayout({ children }: { children: React.ReactNode }) {
  return <DiagnosisProvider>{children}</DiagnosisProvider>
}
