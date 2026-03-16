from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime


class CalibrationPoint(BaseModel):
    pixel_x: float
    pixel_y: float
    real_x: float   # mm
    real_y: float   # mm


class TransformMatrix(BaseModel):
    scale_x: float
    scale_y: float
    offset_x: float
    offset_y: float
    rotation: float = 0.0   # radians


class DrawingCreate(BaseModel):
    inspection_id: UUID4
    drawing_type: str               # GD, SD, LD, UD ...
    drawing_name: Optional[str] = None
    page_number: int = 1
    coord_system: str = "cartesian"


class DrawingCalibrate(BaseModel):
    calibration_points: List[CalibrationPoint]
    scale_text: Optional[str] = None


class DrawingRead(BaseModel):
    id: UUID4
    inspection_id: UUID4
    drawing_type: str
    drawing_name: Optional[str]
    file_url: str
    page_number: int
    transform_matrix: Optional[dict]
    scale_text: Optional[str]
    coord_system: str
    created_at: datetime

    model_config = {"from_attributes": True}
