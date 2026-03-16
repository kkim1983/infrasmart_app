from pydantic import BaseModel, UUID4, EmailStr
from typing import Optional
from datetime import datetime


class InspectorCreate(BaseModel):
    name: str
    license_no: str
    license_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str
    company_id: Optional[UUID4] = None
    admin_key: Optional[str] = None  # 어드민 생성 시 사용


class InspectorRead(BaseModel):
    id: UUID4
    name: str
    license_no: str
    license_type: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class LoginRequest(BaseModel):
    license_no: str
    password: str
    device_info: Optional[dict] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    inspector: InspectorRead
    expires_in: int  # seconds
