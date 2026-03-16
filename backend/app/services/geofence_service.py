import math
from typing import Optional


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 GPS 좌표 간 거리 계산 (meters)"""
    R = 6371000  # 지구 반지름 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def check_circular_geofence(
    lat: float,
    lng: float,
    center_lat: float,
    center_lng: float,
    radius_m: float,
    gps_accuracy: float = 0.0,
) -> tuple[bool, float]:
    """
    원형 지오펜스 검사 (교량용)
    Returns: (is_inside, distance_m)
    GPS 정확도를 고려한 보수적 판정
    """
    distance = haversine_distance(lat, lng, center_lat, center_lng)
    effective_distance = distance - gps_accuracy  # 오차 고려
    is_inside = effective_distance <= radius_m
    return is_inside, distance


def check_linear_geofence(
    lat: float,
    lng: float,
    polyline: list[dict],
    buffer_m: float,
) -> tuple[bool, float]:
    """
    선형 지오펜스 검사 (터널용)
    Returns: (is_inside, min_distance_m)
    """
    min_distance = float("inf")
    for i in range(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i + 1]
        dist = _point_to_segment_distance(lat, lng, p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        min_distance = min(min_distance, dist)

    is_inside = min_distance <= buffer_m
    return is_inside, min_distance


def _point_to_segment_distance(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float
) -> float:
    """점에서 선분까지 최단 거리"""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return haversine_distance(px, py, ax, ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    nearest_x = ax + t * dx
    nearest_y = ay + t * dy
    return haversine_distance(px, py, nearest_x, nearest_y)


def detect_gps_spoofing(gps_track: list[dict]) -> dict:
    """
    GPS 스푸핑 탐지
    - 비정상 고속이동 감지
    - 정확도 급변 감지
    Returns: {is_suspicious, reasons}
    """
    if len(gps_track) < 2:
        return {"is_suspicious": False, "reasons": []}

    reasons = []
    MAX_SPEED_MS = 30  # 108km/h 이상 = 의심

    for i in range(1, len(gps_track)):
        prev = gps_track[i - 1]
        curr = gps_track[i]

        dist = haversine_distance(
            prev["lat"], prev["lng"], curr["lat"], curr["lng"]
        )
        # 타임스탬프가 있으면 속도 계산
        if "time" in prev and "time" in curr:
            try:
                from datetime import datetime
                t1 = datetime.fromisoformat(prev["time"])
                t2 = datetime.fromisoformat(curr["time"])
                elapsed = (t2 - t1).total_seconds()
                if elapsed > 0:
                    speed = dist / elapsed
                    if speed > MAX_SPEED_MS:
                        reasons.append(f"비정상 이동속도: {speed:.1f}m/s")
            except Exception:
                pass

        # 정확도 급변
        if "accuracy" in prev and "accuracy" in curr:
            if abs(curr["accuracy"] - prev["accuracy"]) > 50:
                reasons.append("GPS 정확도 급변 감지")

    return {"is_suspicious": len(reasons) > 0, "reasons": reasons}
