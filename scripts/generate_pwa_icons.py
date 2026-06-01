"""
FinPilot PWA 아이콘 생성기
- 파란 배경(#2563EB) + 흰색 로고(report_worker / FinPilotMark 동일 경로)
- 아이폰 홈화면(apple-touch-icon 180, 불투명 정사각·iOS가 모서리 자동 라운딩) 대응
- Android/매니페스트용 192/512 + maskable(안전영역 패딩) 생성
실행: python scripts/generate_pwa_icons.py
"""
import os
import cairosvg

OUT_DIR = "/SSD/guest/chojoonghui/FinPilot/frontend/public"
ICONS_DIR = os.path.join(OUT_DIR, "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

BG = "#2563EB"      # theme_color 와 동일
FG = "#FFFFFF"      # 흰색 로고

# FinPilotMark 의 원본 좌표계 (viewBox "30 100 870 590")
SRC_X, SRC_Y, SRC_W, SRC_H = 30, 100, 870, 590
LOGO_PATHS = """
  <path d="M 420.50 437.50 Q 421.00 435.00 416.00 434.50 Q 411.00 434.00 365.00 440.00 Q 319.00 446.00 308.00 448.50 Q 297.00 451.00 271.00 459.50 Q 245.00 468.00 236.00 472.00 Q 227.00 476.00 213.50 484.00 Q 200.00 492.00 183.00 506.50 Q 166.00 521.00 105.00 594.00 Q 44.00 667.00 44.00 669.00 Q 44.00 671.00 109.50 671.00 Q 175.00 671.00 192.50 668.00 Q 210.00 665.00 220.50 661.50 Q 231.00 658.00 243.50 652.00 Q 256.00 646.00 272.00 634.50 Q 288.00 623.00 303.50 606.50 Q 319.00 590.00 346.50 551.50 Q 374.00 513.00 397.00 476.50 Q 420.00 440.00 420.50 437.50 Z" fill="{fg}"/>
  <path d="M 777.50 215.00 Q 780.00 207.00 779.00 206.00 Q 778.00 205.00 765.00 214.00 Q 752.00 223.00 735.00 232.50 Q 718.00 242.00 705.50 247.50 Q 693.00 253.00 673.50 259.50 Q 654.00 266.00 617.50 274.00 Q 581.00 282.00 506.50 292.00 Q 432.00 302.00 409.00 307.50 Q 386.00 313.00 372.00 318.00 Q 358.00 323.00 337.00 334.00 Q 316.00 345.00 296.50 359.50 Q 277.00 374.00 259.50 391.50 Q 242.00 409.00 231.50 422.00 Q 221.00 435.00 216.50 442.50 Q 212.00 450.00 214.00 451.00 Q 216.00 452.00 239.50 441.50 Q 263.00 431.00 284.00 425.00 Q 305.00 419.00 328.50 414.50 Q 352.00 410.00 408.00 402.50 Q 464.00 395.00 496.50 389.50 Q 529.00 384.00 563.50 376.00 Q 598.00 368.00 620.50 360.00 Q 643.00 352.00 656.00 345.50 Q 669.00 339.00 680.50 331.50 Q 692.00 324.00 709.00 309.50 Q 726.00 295.00 734.00 286.00 Q 742.00 277.00 752.50 262.00 Q 763.00 247.00 769.00 235.00 Q 775.00 223.00 777.50 215.00 Z" fill="{fg}"/>
  <path d="M 726.50 341.50 Q 731.00 327.00 728.00 327.00 Q 725.00 327.00 715.00 336.00 Q 705.00 345.00 686.50 357.50 Q 668.00 370.00 650.00 379.00 Q 632.00 388.00 609.00 397.00 Q 586.00 406.00 577.00 410.50 Q 568.00 415.00 559.50 420.50 Q 551.00 426.00 545.00 431.00 Q 539.00 436.00 529.00 446.50 Q 519.00 457.00 511.00 468.00 Q 503.00 479.00 455.00 550.50 Q 407.00 622.00 406.50 624.50 Q 406.00 627.00 420.50 627.00 Q 435.00 627.00 449.50 625.50 Q 464.00 624.00 483.50 619.50 Q 503.00 615.00 514.00 611.50 Q 525.00 608.00 546.50 598.00 Q 568.00 588.00 580.50 579.50 Q 593.00 571.00 601.00 564.00 Q 609.00 557.00 620.50 544.50 Q 632.00 532.00 643.50 515.00 Q 655.00 498.00 665.00 480.50 Q 675.00 463.00 689.50 432.50 Q 704.00 402.00 713.00 379.00 Q 722.00 356.00 726.50 341.50 Z" fill="{fg}"/>
  <circle cx="842.39" cy="157.99" r="45.16" fill="{fg}"/>
""".format(fg=FG)


def build_svg(size: int, margin: float, radius_frac: float = 0.0) -> str:
    """size 정사각 캔버스에 파란 배경 + 흰 로고를 margin(여백 비율) 두고 중앙배치."""
    inner_w = size * (1 - 2 * margin)
    sc = inner_w / SRC_W
    tx = margin * size - SRC_X * sc
    ty = (size - SRC_H * sc) / 2 - SRC_Y * sc
    rx = size * radius_frac
    bg = (
        f'<rect width="{size}" height="{size}" rx="{rx}" ry="{rx}" fill="{BG}"/>'
        if radius_frac > 0
        else f'<rect width="{size}" height="{size}" fill="{BG}"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
        f'{bg}'
        f'<g transform="translate({tx:.3f},{ty:.3f}) scale({sc:.5f})">{LOGO_PATHS}</g>'
        f'</svg>'
    )


def render(path: str, size: int, margin: float, radius_frac: float = 0.0):
    svg = build_svg(size, margin, radius_frac)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path,
                     output_width=size, output_height=size)
    print(f"  ✅ {os.path.relpath(path, OUT_DIR)} ({size}x{size})")


def main():
    print("FinPilot PWA 아이콘 생성")
    # iOS 홈화면: 불투명 정사각(투명/라운딩 X — iOS가 자동 처리), 여백 18%
    render(os.path.join(OUT_DIR, "apple-touch-icon.png"), 180, margin=0.18)
    # Android/매니페스트 표준 아이콘
    render(os.path.join(ICONS_DIR, "icon-192.png"), 192, margin=0.16)
    render(os.path.join(ICONS_DIR, "icon-512.png"), 512, margin=0.16)
    render(os.path.join(ICONS_DIR, "icon-1024.png"), 1024, margin=0.16)
    # maskable (Android adaptive: 안전영역 80% → 여백 22%)
    render(os.path.join(ICONS_DIR, "icon-192-maskable.png"), 192, margin=0.22)
    render(os.path.join(ICONS_DIR, "icon-512-maskable.png"), 512, margin=0.22)
    # 파비콘
    render(os.path.join(OUT_DIR, "favicon.png"), 48, margin=0.12)
    render(os.path.join(OUT_DIR, "icon.png"), 512, margin=0.16)
    print("완료.")


if __name__ == "__main__":
    main()
