from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime


class PhotoCreate(BaseModel):
    inspection_id: UUID4
    damage_record_id: Optional[UUID4] = None
    damage_code: Optional[str] = None
    damage_description: Optional[str] = None
    gps: Optional[dict] = None
    drawing_ref: Optional[dict] = None
    taken_at: Optional[datetime] = None
    local_id: Optional[str] = None


class PhotoRead(BaseModel):
    id: UUID4
    inspection_id: UUID4
    damage_record_id: Optional[UUID4]
    photo_number: str
    file_url: str
    thumbnail_url: Optional[str]
    gps: Optional[dict]
    damage_code: Optional[str]
    damage_description: Optional[str]
    drawing_ref: Optional[dict]
    taken_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
