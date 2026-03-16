from pydantic import BaseModel, UUID4
from typing import Optional, Any
from datetime import datetime


class FacilityTypeRead(BaseModel):
    code: str
    name: str
    plugin_version: str
    config: dict[str, Any]

    model_config = {"from_attributes": True}


class FacilityCreate(BaseModel):
    facility_type: str          # BR, TN, DM, RD
    code: str                   # BR-001
    name: str
    location_name: Optional[str] = None
    geofence_type: str = "circular"
    geofence_data: Optional[dict] = None
    facility_meta: Optional[dict] = None


class FacilityRead(BaseModel):
    id: UUID4
    facility_type: str
    code: str
    name: str
    location_name: Optional[str]
    geofence_type: str
    geofence_data: Optional[dict]
    facility_meta: Optional[dict]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
