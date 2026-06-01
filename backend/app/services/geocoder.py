"""주소 → 위경도 + 기상청 격자 변환"""
import math


def geocode_address(address: str) -> tuple[float, float, int, int]:
    """
    Returns (latitude, longitude, nx, ny)
    In production: use Kakao/Naver Geocoding API.
    Fallback: approximate coordinates for major regions.
    """
    region_map = {
        "전주": (35.8242, 127.1480),
        "광주": (35.1596, 126.8526),
        "익산": (35.9483, 126.9577),
        "군산": (35.9676, 126.7369),
        "서울": (37.5665, 126.9780),
        "부산": (35.1796, 129.0756),
    }
    for keyword, coords in region_map.items():
        if keyword in address:
            lat, lon = coords
            nx, ny = _latlng_to_grid(lat, lon)
            return lat, lon, nx, ny

    # Default: Jeonju city hall
    lat, lon = 35.8242, 127.1480
    nx, ny = _latlng_to_grid(lat, lon)
    return lat, lon, nx, ny


def _latlng_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """기상청 격자 좌표 변환 (Lambert conformal conic projection)"""
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = int(ra * math.sin(theta) + XO + 0.5)
    y = int(ro - ra * math.cos(theta) + YO + 0.5)
    return x, y
