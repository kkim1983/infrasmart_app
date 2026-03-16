# InfraSmart - 빠른 시작 가이드

## 사전 요구사항

- Docker Desktop
- Flutter SDK (3.x)
- Xcode (iOS) 또는 Android Studio

---

## 1. 백엔드 실행

```bash
# 저장소 루트에서
cd "infrasmart app"

# 환경변수 설정 (.env.example 복사, 이미 생성됨)
cp .env.example .env

# Docker로 PostgreSQL + Redis + FastAPI 실행
docker compose up -d

# 처음 실행 시 DB 마이그레이션
docker compose exec api alembic upgrade head

# 교량 플러그인 DB 등록 (초기 데이터)
docker compose exec api python -c "
from app.core.database import *
from app.models import *
import asyncio, json

async def seed():
    async with AsyncSessionLocal() as db:
        from app.models.facility import FacilityType
        from sqlalchemy import select
        config = json.load(open('plugins/bridge/config.json'))
        exists = await db.execute(select(FacilityType).where(FacilityType.code == 'BR'))
        if not exists.scalar_one_or_none():
            db.add(FacilityType(code='BR', name='교량', config=config))
            await db.commit()
            print('교량 플러그인 등록 완료')

asyncio.run(seed())
"
```

**확인:**
- API 문서: http://localhost:8000/docs
- pgAdmin: http://localhost:5050 (admin@infrasmart.kr / admin)
- Health: http://localhost:8000/health

---

## 2. Flutter 앱 실행

```bash
cd "infrasmart app/mobile"

# 패키지 설치 (최초 1회)
flutter pub get

# iOS 시뮬레이터 실행
flutter run -d "iPhone 15 Pro"

# Android 에뮬레이터 실행
flutter run -d emulator-5554

# 빌드 (릴리즈)
flutter build ios --release
flutter build apk --release
```

---

## 3. 첫 점검자 등록

```bash
# API로 직접 등록
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "홍길동",
    "license_no": "KR-2024-001",
    "license_type": "안전점검 전문가",
    "phone": "010-1234-5678",
    "password": "test1234!"
  }'
```

---

## 4. 테스트 교량 등록

```bash
# 로그인
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"license_no":"KR-2024-001","password":"test1234!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 교량 등록
curl -X POST http://localhost:8000/api/v1/facilities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "facility_type": "BR",
    "code": "BR-001",
    "name": "테스트교",
    "location_name": "서울시 강남구",
    "geofence_type": "circular",
    "geofence_data": {
      "center_lat": 37.4979,
      "center_lng": 127.0276,
      "radius_m": 500
    },
    "facility_meta": {
      "bridge_length": 120,
      "width": 12,
      "span_count": 3,
      "built_year": 2005,
      "road_name": "테스트로"
    }
  }'
```

---

## 5. E2E 점검 플로우 테스트

```
앱 실행
  → 로그인 (자격증번호: KR-2024-001 / 비밀번호: test1234!)
  → 시설물 목록에서 "테스트교" 선택
  → "점검 시작" 버튼
  → (GPS 지오펜스 검증)
  → 도면 업로드 (PDF 파일)
  → 도면에서 어노테이션 작성
  → 카메라 촬영 (손상 유형 선택 후)
  → 엑셀 내보내기 버튼
```

---

## 프로젝트 구조

```
infrasmart app/
├── backend/               # FastAPI 백엔드
│   ├── app/               # 소스코드
│   ├── plugins/bridge/    # 교량 플러그인 설정
│   └── migrations/        # DB 마이그레이션
├── mobile/                # Flutter 앱
│   ├── lib/               # Dart 소스코드
│   └── assets/plugins/    # 플러그인 설정 (오프라인용)
├── docker-compose.yml
├── ARCHITECTURE.md        # 아키텍처 설계서
└── QUICKSTART.md          # 이 파일
```

---

## Phase 2 추가 예정 기능

- CAD 좌표 정합 + DXF 내보내기
- OCR 손상현황표 자동 추출
- 음성 입력 (Whisper API)
- 감사 로그 + 디지털 서명
- 외부 솔루션 API 연동
