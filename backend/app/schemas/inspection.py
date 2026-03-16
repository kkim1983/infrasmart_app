from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime
from app.models.inspection import InspectionType, InspectionStatus


class InspectionCreate(BaseModel):
    facility_id: UUID4
    inspection_type: InspectionType = InspectionType.ROUTINE
    device_info: Optional[dict] = None
    notes: Optional[str] = None


class InspectionUpdate(BaseModel):
    status: Optional[InspectionStatus] = None
    ended_at: Optional[datetime] = None
    gps_track: Optional[List[dict]] = None
    notes: Optional[str] = None


class InspectionRead(BaseModel):
    id: UUID4
    facility_id: UUID4
    inspector_id: UUID4
    inspection_type: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GpsTrackPoint(BaseModel):
    lat: float
    lng: float
    accuracy: float
    timestamp: Optional[datetime] = None
