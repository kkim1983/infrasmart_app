from pydantic import BaseModel, UUID4
from typing import Optional


class GeofenceCheckRequest(BaseModel):
    facility_id: UUID4
    lat: float
    lng: float
    accuracy: float = 0.0  # GPS 정확도 (m)


class GeofenceCheckResponse(BaseModel):
    is_inside: bool
    distance_m: float           # 현장 중심까지 거리
    allowed_radius_m: float
    facility_name: str
    message: str
