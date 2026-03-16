from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.inspector import Inspector

security = HTTPBearer()


async def get_current_inspector(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Inspector:
    token = credentials.credentials
    payload = decode_token(token)
    inspector_id = payload.get("sub")
    if not inspector_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 오류")

    result = await db.execute(select(Inspector).where(Inspector.id == inspector_id))
    inspector = result.scalar_one_or_none()
    if not inspector or not inspector.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="점검자를 찾을 수 없습니다.")
    return inspector


async def get_current_admin(
    inspector: Inspector = Depends(get_current_inspector),
) -> Inspector:
    if not inspector.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return inspector
