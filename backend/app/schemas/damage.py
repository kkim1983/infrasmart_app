from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime, date


class DamageRecordCreate(BaseModel):
    inspection_id: UUID4
    damage_code: str        # C1, S1, E1 ...
    damage_name: Optional[str] = None
    location_data: Optional[dict] = None
    dimensions: Optional[dict] = None
    severity_grade: Optional[str] = None
    is_new: bool = True
    notes: Optional[str] = None
    drawing_ref: Optional[dict] = None
    local_id: Optional[str] = None


class DamageRecordUpdate(BaseModel):
    severity_grade: Optional[str] = None
    is_expanded: Optional[bool] = None
    is_repaired: Optional[bool] = None
    repair_date: Optional[date] = None
    repair_method: Optional[str] = None
    dimensions: Optional[dict] = None
    notes: Optional[str] = None


class DamageRecordRead(BaseModel):
    id: UUID4
    inspection_id: UUID4
    damage_code: str
    damage_name: Optional[str]
    location_data: Optional[dict]
    dimensions: Optional[dict]
    severity_grade: Optional[str]
    is_new: bool
    is_expanded: bool
    is_repaired: bool
    repair_date: Optional[date]
    notes: Optional[str]
    drawing_ref: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}
