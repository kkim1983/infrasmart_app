from pydantic_settings import BaseSettings
from typing import List


def _parse_origins(v: str) -> List[str]:
    """ALLOWED_ORIGINS 환경변수 파싱 (콤마 구분 또는 JSON 배열 형식 모두 지원)"""
    v = v.strip()
    if v.startswith('['):
        import json
        return json.loads(v)
    return [x.strip() for x in v.split(',') if x.strip()]


class Settings(BaseSettings):
    # 앱
    APP_NAME: str = "InfraSmart"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # CORS 허용 출처 (str로 저장 → allowed_origins 프로퍼티로 파싱)
    # 환경변수 형식 (둘 다 지원):
    #   콤마 구분: ALLOWED_ORIGINS=https://a.com,https://b.com
    #   JSON 배열: ALLOWED_ORIGINS=["https://a.com","https://b.com"]
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @property
    def allowed_origins(self) -> List[str]:
        return _parse_origins(self.ALLOWED_ORIGINS)

    # 데이터베이스
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "infrasmart"
    POSTGRES_USER: str = "infrasmart"
    POSTGRES_PASSWORD: str = "changeme_secure_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "changeme_very_long_random_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8시간 (현장 점검 1일치)

    # 서버 공개 URL (파일 URL 생성에 사용)
    BACKEND_URL: str = "http://localhost:8000"

    # 파일 스토리지
    STORAGE_TYPE: str = "local"  # local | s3
    STORAGE_LOCAL_PATH: str = "./uploads"
    NCLOUD_ACCESS_KEY: str = ""
    NCLOUD_SECRET_KEY: str = ""
    NCLOUD_REGION: str = "kr-standard"
    NCLOUD_BUCKET: str = "infrasmart-files"

    # AI 서비스
    OPENAI_API_KEY: str = ""

    # 지오펜스
    DEFAULT_GEOFENCE_RADIUS_M: int = 500
    GPS_SPOOF_DETECTION: bool = True

    # 어드민
    ADMIN_CREATION_KEY: str = ""  # 설정 시 해당 키로 어드민 계정 생성 가능

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
