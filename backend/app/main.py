from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, facilities, inspections, drawings, annotations, photos, damages, export, ocr, voice, audit, integrations, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 업로드 디렉토리 생성
    Path(settings.STORAGE_LOCAL_PATH).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="시설물 안전점검 자동화 플랫폼 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 (로컬 업로드)
uploads_path = Path(settings.STORAGE_LOCAL_PATH)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(uploads_path)), name="files")

# API 라우터 등록
app.include_router(auth.router, prefix="/api/v1")
app.include_router(facilities.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")
app.include_router(drawings.router, prefix="/api/v1")
app.include_router(annotations.router, prefix="/api/v1")
app.include_router(photos.router, prefix="/api/v1")
app.include_router(damages.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(ocr.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
