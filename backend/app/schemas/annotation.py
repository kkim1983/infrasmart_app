from pydantic import BaseModel, UUID4
from typing import Optional, List, Any
from datetime import datetime


class AnnotationCreate(BaseModel):
    drawing_id: UUID4
    ann_type: str           # pen | text | voice | circle | rect | arrow
    layer: str              # damage_new | damage_exist | damage_expanded | repaired | note
    coordinates: List[Any]  # [{x,y},...] or {x,y,w,h}
    content: Optional[str] = None
    style: Optional[dict] = None
    damage_record_id: Optional[UUID4] = None
    local_id: Optional[str] = None


class AnnotationRead(BaseModel):
    id: UUID4
    drawing_id: UUID4
    ann_type: str
    layer: str
    coordinates: List[Any]
    content: Optional[str]
    style: Optional[dict]
    damage_record_id: Optional[UUID4]
    local_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationBatchSync(BaseModel):
    """오프라인에서 쌓인 어노테이션 일괄 동기화"""
    annotations: List[AnnotationCreate]
    device_timestamp: datetime
