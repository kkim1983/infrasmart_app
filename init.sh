#!/bin/bash
set -e

echo "🚀 InfraSmart 백엔드 초기화 시작..."
cd "$(dirname "$0")"

# 1. 백엔드 실행
echo ""
echo "① Docker 컨테이너 시작..."
docker compose up -d
sleep 3

# 2. DB 마이그레이션
echo ""
echo "② DB 마이그레이션..."
docker compose exec api alembic upgrade head

# 3. 교량 플러그인 등록
echo ""
echo "③ 교량 플러그인 등록..."
docker compose exec api python -c "
from app.core.database import AsyncSessionLocal
from app.models.facility import FacilityType
from sqlalchemy import select
import asyncio, json

async def seed():
    async with AsyncSessionLocal() as db:
        config = json.load(open('plugins/bridge/config.json'))
        r = await db.execute(select(FacilityType).where(FacilityType.code == 'BR'))
        if not r.scalar_one_or_none():
            db.add(FacilityType(code='BR', name='교량', config=config))
            await db.commit()
            print('  ✓ 교량 플러그인 등록 완료')
        else:
            print('  ✓ 이미 등록됨')

asyncio.run(seed())
"

# 4. 테스트 계정 등록
echo ""
echo "④ 테스트 계정 등록..."
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "홍길동",
    "license_no": "KR-2024-001",
    "license_type": "안전점검 전문가",
    "phone": "010-1234-5678",
    "password": "test1234!"
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
if 'id' in r:
    print('  ✓ 계정 생성 완료')
elif 'detail' in r and '이미' in str(r['detail']):
    print('  ✓ 이미 존재하는 계정')
else:
    print('  결과:', r)
" 2>/dev/null || echo "  ✓ 계정 처리 완료"

# 5. 로그인 → 토큰 획득
echo ""
echo "⑤ 테스트 교량 등록..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"license_no":"KR-2024-001","password":"test1234!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

if [ -z "$TOKEN" ]; then
  echo "  ⚠ 로그인 실패 - 이미 교량이 등록되어 있을 수 있습니다"
else
  curl -s -X POST http://localhost:8000/api/v1/facilities \
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
    }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
if 'id' in r:
    print('  ✓ 교량 등록 완료:', r.get('name'))
else:
    print('  결과:', r)
" 2>/dev/null || echo "  ✓ 교량 처리 완료"
fi

echo ""
echo "======================================"
echo "✅ 초기화 완료!"
echo ""
echo "📱 앱 로그인 정보"
echo "   자격증 번호: KR-2024-001"
echo "   비밀번호:    test1234!"
echo ""
echo "🌐 API 문서: http://localhost:8000/docs"
echo "======================================"
