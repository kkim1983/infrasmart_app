# 시설물 안전점검 자동화 플랫폼 - 아키텍처 설계서

> 작성일: 2026-03-13
> 버전: v1.0
> 작성: Claude Sonnet 4.6 (AI 아키텍처 설계)

---

## 목차

1. [설계 철학](#1-설계-철학)
2. [시스템 전체 구조](#2-시스템-전체-구조)
3. [Facility Plugin 시스템](#3-facility-plugin-시스템)
4. [기능별 상세 설계](#4-기능별-상세-설계)
5. [핵심 주의사항 1 - 오프라인 우선 설계](#5-핵심-주의사항-1---오프라인-우선-설계)
6. [핵심 주의사항 2 - CAD 좌표 정합](#6-핵심-주의사항-2---cad-좌표-정합)
7. [핵심 주의사항 3 - 법적 감사 로그 & 데이터 불변성](#7-핵심-주의사항-3---법적-감사-로그--데이터-불변성)
8. [데이터베이스 스키마](#8-데이터베이스-스키마)
9. [기술 스택](#9-기술-스택)
10. [개발 로드맵 (AI 활용 기준)](#10-개발-로드맵-ai-활용-기준)
11. [새 시설물 확장 방법](#11-새-시설물-확장-방법)

---

## 1. 설계 철학

세 가지 원칙을 모든 설계의 기반으로 한다.

| 원칙 | 내용 |
|------|------|
| **Facility-Agnostic Core** | 교량/터널/댐/도로 등 어떤 시설물도 플러그인으로 추가 가능 |
| **Offline-First** | 현장 통신 불안정 → 오프라인에서 100% 동작, 연결 시 자동 동기화 |
| **Immutable Audit Trail** | 모든 데이터 변경 이력 영구 보존, 법적 효력 보장 (10년+ 보존) |

---

## 2. 시스템 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FACILITY PLATFORM CORE                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Facility Plugin Registry                        │   │
│  │                                                             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │ 교량(BR) │ │ 터널(TN) │ │  댐(DM)  │ │  도로(RD)   │  │   │
│  │  │ Plugin   │ │ Plugin   │ │ Plugin   │ │  Plugin     │  │   │
│  │  │ v1.0     │ │ v1.0     │ │ 예정     │ │  예정       │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────▼─────────────────────────────────┐   │
│  │                   Core Engine                               │   │
│  │                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │  Annotation  │  │  Inspection  │  │   Export         │  │   │
│  │  │  Engine      │  │  Workflow    │  │   Engine         │  │   │
│  │  │  (도면마킹)   │  │  Engine      │  │  (엑셀/CAD/API)  │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │  OCR Engine  │  │  Camera      │  │   Audit          │  │   │
│  │  │  (표추출)     │  │  Engine      │  │   Engine         │  │   │
│  │  │              │  │  (사진관리)   │  │  (감사로그)       │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────▼─────────────────────────────────┐   │
│  │              Offline-First Layer                            │   │
│  │  SQLite(로컬) ←→ Sync Queue ←→ PostgreSQL(서버)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──┐  ┌─────────▼──┐  ┌────────▼────┐
    │  Auth      │  │  AI/ML     │  │  External   │
    │  Service   │  │  Services  │  │  Solution   │
    │  (인증/GPS) │  │  (OCR/YOLO)│  │  API 연동   │
    └────────────┘  └────────────┘  └─────────────┘
```

### 백엔드 마이크로서비스 구성

| 서비스 | 역할 |
|--------|------|
| **Auth Service** | JWT, 생체인증, GPS 위치 검증, 디지털 서명 |
| **Document Service** | PDF 저장/관리, 어노테이션 관리, CAD 변환 |
| **OCR Service** | 손상현황표 추출, 이미지 전처리 |
| **Camera/Photo Service** | 사진 메타데이터, 번호 부여, AI 분석 |
| **Export Service** | 엑셀 생성, 외부 솔루션 API 연동 |
| **Audit Service** | 불변 이벤트 로그, 해시 체인 관리 |

---

## 3. Facility Plugin 시스템

### 플러그인 인터페이스 (TypeScript)

```typescript
interface FacilityPlugin {
  facilityType: FacilityType;         // BRIDGE | TUNNEL | DAM | ROAD

  getDamageCodes(): DamageCodeRegistry;      // 손상코드 체계
  getDrawingTypes(): DrawingTypeConfig[];    // 도면 유형
  getInspectionForm(): FormSchema;           // 점검 양식
  getExcelTemplates(): ExcelTemplateConfig[];// 엑셀 템플릿
  getCADLayerConfig(): CADLayerConfig;       // CAD 레이어 설정
  getGeofenceConfig(): GeofenceConfig;       // 현장 지오펜스
  getSeverityGrades(): SeverityGrade[];      // 심각도 등급 체계
  getReportSections(): ReportSection[];      // 보고서 섹션
}
```

### 교량 vs 터널 플러그인 비교

| 구성요소 | 교량(BR) | 터널(TN) |
|---------|----------|----------|
| **손상코드** | C1(균열), S1(박리), E1(철근노출) | C1(균열), L1(누수), R1(라이닝박리) |
| **도면 유형** | 일반도, 구조도, 상세도, 배근도 | 종단면도, 횡단면도, **전개도(★)** |
| **전개도 처리** | 해당없음 | 원통→평면 좌표변환 (별도 로직) |
| **지오펜스** | 원형 (반경 500m) | 선형 (터널 구간 ±100m) |
| **위치 표기** | 부재번호 + 스팬 | 측점(STA) + 링번호 |
| **심각도** | A~E (도로교설계기준) | A~E (터널 기준) |

> ★ 터널 전개도: 원통형 터널을 평면으로 펼친 도면. 위치 표기: `STA.1+500 ~ 1+520 / 좌측 벽체`

### 플러그인 JSON 설정 예시

```json
{
  "facilityType": "TUNNEL",
  "version": "1.0.0",
  "damageCodes": [
    {
      "code": "C1", "name": "균열", "unit": "m",
      "fields": ["length", "width", "depth"],
      "severity_matrix": "tunnel_crack_severity_v1"
    },
    {
      "code": "L1", "name": "누수", "unit": "m²",
      "fields": ["area", "flow_rate"],
      "severity_matrix": "tunnel_leak_severity_v1"
    }
  ],
  "drawingTypes": [
    {"code": "LD", "name": "종단면도", "coordinateSystem": "linear"},
    {"code": "CD", "name": "횡단면도", "coordinateSystem": "section"},
    {"code": "UD", "name": "전개도",   "coordinateSystem": "unfolded"}
  ],
  "locationSchema": {
    "primary": "station",
    "secondary": "ring",
    "tertiary": "position"
  },
  "geofence": {
    "type": "linear",
    "bufferMeters": 100
  }
}
```

---

## 4. 기능별 상세 설계

### 기능 1 - PDF 도면 어노테이션 + CAD 연동

**어노테이션 데이터 모델**

```json
{
  "id": "uuid",
  "type": "pen | text | voice | shape",
  "coordinates": [{"x": 120, "y": 340}, "..."],
  "content": "균열 L=2.5m",
  "layer": "damage_new | damage_exist | repaired",
  "damageType": "crack | spalling | rebar_exposure",
  "timestamp": "2026-03-13T09:30:00Z",
  "inspectorId": "uuid",
  "gpsLocation": {"lat": 37.1234, "lng": 127.5678}
}
```

**CAD 레이어 매핑**

| 어노테이션 레이어 | CAD 레이어 색상 | 의미 |
|-----------------|----------------|------|
| `damage_new` | RED | 신규 손상 |
| `damage_exist` | YELLOW | 기존 손상 |
| `damage_expanded` | ORANGE | 확대 손상 |
| `repaired` | GREEN | 보수 완료 |
| `text_note` | WHITE | 텍스트 메모 |

**기술**: PSPDFKit SDK (PDF 뷰어) + Fabric.js/Flutter Canvas (어노테이션) + ezdxf (DXF 생성)

---

### 기능 2 - 카메라 촬영 + 자동 메타데이터

**사진 번호 체계**: `현장코드-부재번호-손상유형-순번`
- 예: `BR001-G3-CR-004.jpg`

**촬영 플로우**

```
손상 위치 선택 (도면에서 탭)
    → 손상 유형 / 규모 입력 UI
    → 카메라 촬영
    → GPS 좌표 자동 기록
    → 타임스탬프 자동 기록
    → 점검자 ID 자동 기록
    → 도면 위치 좌표 연결
    → 사진번호 자동 부여
    → (선택) AI 손상 자동 분석 (YOLOv8)
```

**Photo 메타데이터 구조**

```json
{
  "photoId": "BR001-G3-CR-004",
  "drawingRef": {"drawingId": "uuid", "x": 340, "y": 120},
  "damageType": "crack",
  "dimensions": {"length": 2.5, "width": 0.3},
  "severity": "B",
  "gps": {"lat": 37.1234, "lng": 127.5678},
  "inspector": {"id": "uuid", "name": "홍길동"},
  "timestamp": "2026-03-13T09:30:00Z",
  "repaired": false,
  "aiAnalysis": {"confidence": 0.94, "detectedType": "crack"}
}
```

---

### 기능 3 - OCR 손상현황표 추출

**처리 파이프라인**

```
Step 1: 표 영역 드래그 선택 (사용자)
    ↓
Step 2: 이미지 전처리 (Backend)
    - 회전 보정 (deskew)
    - 이진화 / 노이즈 제거
    - 해상도 업스케일
    ↓
Step 3: 표 구조 인식
    - Table Detection: PaddleOCR / Google Vision
    - 셀 경계선 인식 → 행/열 매핑
    ↓
Step 4: 텍스트 추출 + 정규화
    - 한글 OCR
    - 손상코드 정규화 (C1→균열 등)
    - 수치 파싱 (2.5m, 0.3mm 등)
    ↓
Step 5: 사용자 검수 UI → 수동 수정 가능
    ↓
Step 6: DB 저장 + 엑셀 반영
```

---

### 기능 4 - 신규/기존 손상 → 엑셀 자동 반영

**손상 상태 4가지 레이어**

```
Layer 1: 기존손상 (이전 점검에서 가져옴)  → 노란색
Layer 2: 신규손상 (이번 점검 신규)        → 빨간색
Layer 3: 확대손상 (기존에서 커짐)         → 주황색
Layer 4: 보수완료 (repair=true)          → 초록색
```

**변경 → 엑셀 자동 반영 흐름**

```
도면/표에서 상태 변경 (예: 보수여부 체크)
    → EventBus 이벤트 발행
    → DamageRecord 업데이트 (변경 이력 포함)
    → Excel Template Engine 트리거
    → 손상현황표 셀 자동 갱신
    → 실시간 미리보기 or 최종 Export 반영
```

---

### 기능 5 - GPS + 개인인증 (불법 하도급 차단)

**3단계 인증 구조**

```
1단계: 신원 인증
    - 건설업 면허 DB 조회 (KISCON API)
    - 생체인증 (Face ID / 지문)
    - 개인키 발급 (디지털 서명용)

2단계: 현장 위치 검증 (GPS Geofencing)
    - 교량: 중심좌표 + 반경 500m 원형 구역
    - 터널: 터널 구간 선형 + 좌우 100m 버퍼
    - 점검 전 위치 인증 필수
    - 이탈 시 경고 + 5분 후 작업 중단

3단계: 지속적 이상 감지
    - 이동 패턴 분석 (비정상 고속이동 = 차량조작 의심)
    - GPS 스푸핑 탐지 (위성수/정확도 모니터링)
    - 주기적 셀카 촬영 요구 (안면인식 재확인)
    - 모든 작업에 GPS 좌표 + 타임스탬프 기록
```

**인증 토큰 구조**

```json
{
  "userId": "uuid",
  "licenseNo": "점검면허번호",
  "companyId": "uuid",
  "inspectionId": "uuid",
  "facilityId": "uuid",
  "gpsSnapshot": [
    {"lat": 37.1234, "lng": 127.5678, "time": "09:00:00", "accuracy": 5}
  ],
  "signature": "ECDSA 서명값",
  "validUntil": "2026-03-13T23:59:59Z"
}
```

---

### 기능 6 - 표준 엑셀 추출 + 외부 솔루션 연동

**엑셀 시트 구성**

| Sheet | 내용 |
|-------|------|
| Sheet 1 | 현장개요 (시설물 정보, 점검 일자, 점검자) |
| Sheet 2 | 손상현황표 (표준양식, OCR+어노테이션 통합) |
| Sheet 3 | 사진대지 (사진+설명 자동배치) |
| Sheet 4 | 점검자 인증 이력 (GPS, 서명, 타임스탬프) |
| Sheet 5 | GPS 위치 이력 |

**외부 솔루션 연동 방식**

```
방법 A: REST API Push
    POST /api/external/inspection-result
    Authorization: API-Key {key}
    Content-Type: application/json
    Body: 표준화된 JSON 페이로드

방법 B: .xlsx 파일 다운로드
    사용자가 직접 다운로드 후 솔루션에 업로드

방법 C: Webhook
    점검 완료 시 등록된 URL로 자동 POST
```

---

## 5. 핵심 주의사항 1 - 오프라인 우선 설계

### 오프라인에서 가능한 작업 (100%)

- PDF 도면 열기 (사전 다운로드)
- 모든 어노테이션 작업
- 카메라 촬영 및 사진 관리
- 손상 기록 입력/수정
- OCR 결과 편집

### 온라인이 필요한 작업

- 음성 → 텍스트 변환 (Whisper API)
- AI 손상 자동 분석 (YOLOv8)
- 서버 동기화
- CAD/엑셀 최종 생성 (서버 처리 시)

### Sync Queue 구조

```json
{
  "op": "CREATE | UPDATE | DELETE",
  "entity": "annotation | photo | damage | inspection",
  "data": {"...실제 데이터..."},
  "localId": "uuid",
  "status": "PENDING | SYNCING | SYNCED | FAILED",
  "retryCount": 0,
  "createdAt": "timestamp"
}
```

### 충돌 해결 전략

| 데이터 유형 | 전략 |
|------------|------|
| 어노테이션 | Last-Write-Wins (타임스탬프 기준) |
| 손상기록 | Merge (두 점검자가 다른 위치 작업 시) |
| 사진 | Append-Only (절대 덮어쓰지 않음) |

### 동기화 상태 표시 (UI)

```
🟢 동기화됨    → 서버와 일치
🟡 동기화 대기 → 큐에 작업 있음, 연결 대기 중
🔴 오프라인    → 연결 없음, 로컬에만 저장
```

---

## 6. 핵심 주의사항 2 - CAD 좌표 정합

### 문제 정의

PDF 도면의 픽셀 좌표 → 실제 치수(mm/m) → CAD 좌표계 변환이 필요하며, 이 변환의 정확도가 CAD 출력 품질을 결정한다.

### 해결 파이프라인

**Step 1: 스케일 자동 추출 (OCR)**

```
PDF 도면에서 자동 탐지:
- OCR: "S=1/100", "축척 1:100" 텍스트 추출
- 이미지: 스케일바(자 모양) 패턴 인식
- 실패 시 Step 2로 대체
```

**Step 2: 수동 캘리브레이션 (보정점 방식)**

```
사용자가 도면에서 알려진 두 점 탭:
"이 두 기둥 중심 거리가 실제 25,000mm 입니다"

Point A: 픽셀(120, 340) → 실제 좌표(0, 0)
Point B: 픽셀(890, 340) → 실제 좌표(25000, 0)

계산:
scale_x = 25000 / (890 - 120) = 32.47 mm/px
rotation = atan2(dy_px, dx_px) - atan2(dy_real, dx_real)
```

**Step 3: 변환 행렬 저장**

```json
{
  "drawingId": "uuid",
  "transformMatrix": {
    "scaleX": 32.47,
    "scaleY": 32.47,
    "offsetX": -3898,
    "offsetY": -11050,
    "rotation": 0.0023
  },
  "calibrationPoints": ["..."],
  "verifiedAt": "timestamp",
  "verifiedBy": "inspectorId"
}
```

**Step 4: 터널 전개도 특수 처리**

```
터널 내면을 원통으로 모델링:

전개도 x좌표(px) → 터널 내면 호의 길이
전개도 y좌표(px) → 터널 종방향 위치(측점, STA)

원주 = π × 내경(m)
각도 = (x_px / total_width_px) × 360°

→ 3D 좌표 복원 가능, GIS 연동 시 활용
```

**Step 5: 검증**

```
생성된 DXF를 미리보기로 표시 → 사용자 확인
오차 허용범위: ±50mm (현장 실용 기준)
오차 초과 시: 재캘리브레이션 요청
```

---

## 7. 핵심 주의사항 3 - 법적 감사 로그 & 데이터 불변성

### Event Sourcing 기반 설계

모든 행위는 "이벤트"로 기록되며 수정/삭제 불가.

```
이벤트 스트림 예시:

t=09:00  INSPECTION_STARTED   {inspectorId, facilityId, gps}
t=09:05  DRAWING_OPENED       {drawingId, fileName}
t=09:10  ANNOTATION_CREATED   {annotId, type, coords, ...}
t=09:15  PHOTO_TAKEN          {photoId, gps, damage, ...}
t=09:20  DAMAGE_UPDATED       {damageId, field, oldValue, newValue}  ← 이전값 보존
t=09:25  OCR_EXTRACTED        {tableId, rawText, cells}
t=10:30  INSPECTION_ENDED     {inspectorId, summary}
t=11:00  REPORT_EXPORTED      {format, fileHash, recipient}
```

### 데이터 불변성 3중 보장

**Layer 1: 해시 체인**

```
Event_1: {data, hash: SHA256(data)}
Event_2: {data, prevHash: Event_1.hash, hash: SHA256(data+prevHash)}
Event_N: {data, prevHash: Event_N-1.hash, hash: ...}

→ 중간 이벤트 변조 시 이후 모든 해시 불일치 → 즉시 탐지
```

**Layer 2: 디지털 서명**

```json
{
  "eventId": "uuid",
  "data": {"..."},
  "inspectorSignature": "ECDSA 서명값",
  "timestamp": "RFC3339",
  "gpsSnapshot": {"lat": 37.1234, "lng": 127.5678, "accuracy": 5}
}
```

**Layer 3: 공인 타임스탬프 (KISA TSA)**

```
중요 이벤트 (점검완료, 보고서 생성)는
KISA 타임스탬프 서비스에 해시값 등록
→ 법적 효력 있는 시간 증명
→ 국내: KISA RFC3161 TSA 서비스 활용
```

### 데이터 보존 정책

| 보존 구간 | 스토리지 | 비용 |
|----------|---------|------|
| 0~2년 (Hot) | PostgreSQL + S3 Standard | 높음 |
| 2~5년 (Warm) | S3 Standard-IA | 중간 |
| 5~10년+ (Cold) | S3 Glacier | 낮음 |

**법정 보존 기간**

| 점검 유형 | 보존 기간 |
|----------|---------|
| 정기점검 | 10년 |
| 정밀안전진단 | 준공 시까지 (수십년) |
| 긴급점검 | 10년 |

**자동화 정책**

- 보존 기간 만료 60일 전 담당자 알림
- 단계적 삭제 승인 (담당자 → 관리자 → 최종 확인)
- 삭제도 이벤트로 기록 (삭제 사유, 승인자 포함)

---

## 8. 데이터베이스 스키마

```sql
-- ============================================
-- 시설물 플러그인 등록
-- ============================================
CREATE TABLE facility_types (
  code            VARCHAR(2) PRIMARY KEY,  -- BR, TN, DM, RD
  name            VARCHAR NOT NULL,
  plugin_version  VARCHAR,
  config          JSONB NOT NULL,          -- 플러그인 설정 전체
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 시설물 (교량/터널/댐 공통)
-- ============================================
CREATE TABLE facilities (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_type   VARCHAR(2) REFERENCES facility_types(code),
  code            VARCHAR NOT NULL UNIQUE,  -- BR-001, TN-042
  name            VARCHAR NOT NULL,
  location_name   VARCHAR,
  geofence_type   VARCHAR,   -- circular | linear
  geofence_data   JSONB,     -- 교량:{center_lat,lng,radius} 터널:{polyline,buffer}
  facility_meta   JSONB,     -- 교량:{교장,폭원} / 터널:{연장,내경}
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 점검
-- ============================================
CREATE TABLE inspections (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id     UUID REFERENCES facilities(id),
  inspector_id    UUID REFERENCES inspectors(id),
  inspection_type VARCHAR,   -- ROUTINE | PRECISE | EMERGENCY
  status          VARCHAR,   -- DRAFT | IN_PROGRESS | COMPLETED | EXPORTED
  started_at      TIMESTAMPTZ,
  ended_at        TIMESTAMPTZ,
  gps_track       JSONB,     -- [{lat,lng,time,accuracy},...]
  device_info     JSONB,     -- {deviceId,os,appVersion}
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 도면
-- ============================================
CREATE TABLE drawings (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inspection_id    UUID REFERENCES inspections(id),
  drawing_type     VARCHAR,   -- 플러그인 정의 코드 (LD/CD/UD 등)
  file_url         VARCHAR,   -- S3 URL
  page_number      INTEGER,
  transform_matrix JSONB,     -- {scaleX,scaleY,offsetX,offsetY,rotation}
  calibration_pts  JSONB,     -- 보정에 사용된 기준점들
  scale_text       VARCHAR,   -- OCR 추출 축척 ("1:100")
  coord_system     VARCHAR    -- cartesian | unfolded | section
);

-- ============================================
-- 어노테이션 (도면 위 마킹)
-- ============================================
CREATE TABLE annotations (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drawing_id       UUID REFERENCES drawings(id),
  type             VARCHAR,   -- pen | text | voice | shape | marker
  layer            VARCHAR,   -- damage_new | damage_exist | expanded | repaired
  coordinates      JSONB,     -- PDF 픽셀 좌표
  real_coordinates JSONB,     -- 변환된 실제 좌표 (mm)
  content          TEXT,
  damage_record_id UUID REFERENCES damage_records(id),
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 손상 기록 (시설물 유형 무관)
-- ============================================
CREATE TABLE damage_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inspection_id   UUID REFERENCES inspections(id),
  damage_code     VARCHAR,   -- 플러그인 정의 코드 (C1, L1, R1 등)
  location_data   JSONB,     -- 교량:{member,span} / 터널:{station,ring,position}
  dimensions      JSONB,     -- 손상 규모 (플러그인이 필드 정의)
  severity_grade  VARCHAR,   -- A~E
  is_new          BOOLEAN DEFAULT TRUE,
  is_expanded     BOOLEAN DEFAULT FALSE,
  is_repaired     BOOLEAN DEFAULT FALSE,
  repair_date     DATE,
  prev_record_id  UUID REFERENCES damage_records(id),  -- 이전 점검 연결
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 사진
-- ============================================
CREATE TABLE photos (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  photo_number     VARCHAR UNIQUE,  -- BR001-G3-CR-004
  damage_record_id UUID REFERENCES damage_records(id),
  file_url         VARCHAR,
  thumbnail_url    VARCHAR,
  gps              JSONB,
  exif_data        JSONB,
  ai_analysis      JSONB,     -- YOLOv8 분석 결과
  taken_at         TIMESTAMPTZ
);

-- ============================================
-- 점검자
-- ============================================
CREATE TABLE inspectors (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR,
  license_no      VARCHAR UNIQUE,
  license_type    VARCHAR,
  company_id      UUID,
  face_embedding  VECTOR(512),  -- 안면인식 벡터 (pgvector)
  public_key      TEXT,         -- 디지털 서명용 공개키
  is_active       BOOLEAN DEFAULT TRUE
);

-- ============================================
-- 불변 감사 로그 (Append-Only)
-- INSERT만 허용, UPDATE/DELETE 불가
-- ============================================
CREATE TABLE audit_events (
  id            BIGSERIAL PRIMARY KEY,
  event_type    VARCHAR NOT NULL,
  inspection_id UUID,
  actor_id      UUID,
  entity_type   VARCHAR,  -- drawing | annotation | photo | damage
  entity_id     UUID,
  payload       JSONB,    -- 변경 전/후 값 모두 포함
  gps_snapshot  JSONB,
  prev_hash     VARCHAR,  -- 이전 이벤트 해시
  event_hash    VARCHAR,  -- SHA256(payload + prev_hash)
  signature     TEXT,     -- 점검자 개인키 서명
  tsa_token     TEXT,     -- 공인 타임스탬프 (중요 이벤트만)
  created_at    TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Append-Only 강제 (Row-Level Security)
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_insert_only ON audit_events
  FOR INSERT WITH CHECK (true);
-- SELECT는 허용, UPDATE/DELETE는 정책 없음 → 자동 거부
```

---

## 9. 기술 스택

| 레이어 | 기술 | 선택 이유 |
|--------|------|----------|
| **모바일 앱** | Flutter | 고성능 Canvas, iOS/Android 동시 지원, 오프라인 SQLite |
| **PDF/Canvas** | PSPDFKit SDK | 건설도면 수준의 어노테이션 기능 |
| **로컬 DB** | Drift (SQLite) | Flutter 최적화 오프라인 ORM |
| **오프라인 동기화** | PowerSync | 오프라인 싱크 전문 솔루션 |
| **음성 입력** | OpenAI Whisper API | 한국어 인식 최고 수준 |
| **OCR** | PaddleOCR | 한글 표 인식 특화 |
| **손상 AI** | YOLOv8 (커스텀 학습) | 교량/터널 손상 특화 학습 |
| **백엔드** | Python FastAPI | AI 라이브러리 생태계, 비동기 처리 |
| **CAD 변환** | ezdxf | DXF 생성 표준 라이브러리 |
| **DB** | PostgreSQL + pgvector | 안면인식 벡터, 파티셔닝 지원 |
| **파일 저장** | NCloud Object Storage | 국내 데이터 주권 |
| **캐시** | Redis | 세션 관리, 동기화 큐 |
| **엑셀 생성** | openpyxl | 복잡한 양식, 셀 병합 등 지원 |
| **웹 포털** | Next.js | 관리자/보고서 대시보드 |
| **인프라** | NCloud Kubernetes | 국내, 컨테이너 오케스트레이션 |
| **타임스탬프** | KISA TSA | 법적 효력 있는 시간 증명 |
| **감사 로그 강제** | PostgreSQL RLS | Append-Only 정책 강제 |

---

## 10. 개발 로드맵 (AI 활용 기준)

### AI 코딩 도구 활용 전제

- Claude Code / GitHub Copilot 풀 활용
- 보일러플레이트, CRUD, API 연동은 AI가 즉시 생성
- 핵심 로직(좌표 변환, OCR 파이프라인, 동기화 엔진)은 AI 초안 → 사람 검증
- 테스트 코드 AI 자동 생성

### 현실적 일정 (AI 보조 개발 기준)

```
Week 1~2: 기반 인프라 + 교량 플러그인 코어
    ├── 프로젝트 구조 세팅 (Flutter + FastAPI)
    ├── DB 스키마 생성 + 마이그레이션
    ├── 교량 플러그인 JSON 설정
    ├── 인증 서비스 (JWT + GPS 기본)
    └── PDF 뷰어 + 기본 어노테이션 (펜/텍스트)

Week 3~4: 핵심 기능 구현
    ├── 카메라 + 사진 메타데이터 자동부여
    ├── 오프라인 SQLite + Sync Queue 기본
    ├── GPS 지오펜스 검증
    └── 기본 엑셀 내보내기

Week 5~6: 고급 기능 구현
    ├── CAD 좌표 정합 + DXF 생성
    ├── OCR 손상현황표 추출 파이프라인
    ├── 음성 입력 (Whisper 연동)
    └── 감사 로그 + 해시 체인

Week 7~8: 고도화 + 터널 확장
    ├── YOLOv8 손상 탐지 (기학습 모델 파인튜닝)
    ├── 터널 플러그인 (전개도 좌표 변환 포함)
    ├── KISA TSA 연동
    └── 외부 솔루션 API 연동

Week 9~10: 안정화 + 완성
    ├── 오프라인 동기화 고도화 + 충돌 해결
    ├── GPS 스푸핑 탐지
    ├── 웹 관리자 포털 (기본)
    ├── 통합 테스트 + 보안 점검
    └── 베타 배포
```

> **일정 현실성 메모**
> AI 코딩 도구를 최대한 활용해도 단순히 "빠른 타이핑"이 아니라 **설계 결정, 검증, 통합 테스트**가 병목이 됨.
> 외부 의존성(KISA TSA, KISCON API 계약, PSPDFKit 라이선스, 기관 승인)은 AI와 무관하게 시간 소요.
> 핵심 MVP(기능 1~3 + GPS 인증 + 엑셀 내보내기)는 2~3주에 가능하나,
> 법적 요건(감사로그, TSA)과 CAD 좌표 정합의 정밀도 검증은 단축 불가.

---

## 11. 새 시설물 확장 방법

### 단계별 프로세스

```
1단계: 플러그인 설정 파일 작성 (개발 없이 가능)
    /plugins/{type}/config.json          ← 손상코드, 도면유형, 양식
    /plugins/{type}/excel_template.xlsx  ← 엑셀 표준양식
    /plugins/{type}/severity_matrix.json ← 상태등급 판정표

2단계: 특수 좌표계가 있으면 변환 모듈 추가
    /plugins/{type}/coordinate_transform.py
    (터널 전개도처럼 특수한 경우에만 해당)

3단계: DB에 플러그인 등록
    INSERT INTO facility_types VALUES ('{code}', '{name}', '1.0.0', <config>);

4단계: 완료
    앱에서 시설물 유형 선택 시 자동으로 해당 모드로 동작
```

### 확장 소요 시간 예상

| 시설물 유형 | 작업 내용 | 소요 시간 |
|------------|---------|---------|
| 도로(포장) | 설정파일만 | 1~2일 |
| 건축물 | 설정파일 + 층별 도면 처리 | 3~5일 |
| 터널 | 설정파일 + 전개도 좌표 변환 | 1~2주 |
| 댐 | 설정파일 + 수위/침투 특수 처리 | 1~2주 |

---

## 부록 - 외부 API 연동 목록

| API | 용도 | 비고 |
|-----|------|------|
| KISCON API | 건설업체/기술자 면허 조회 | 국토부 |
| 정부24 API | 실명 확인 | 행정안전부 |
| KISA TSA | 공인 타임스탬프 | 법적 효력 |
| OpenAI Whisper | 음성→텍스트 | 한국어 최고 수준 |
| Google Vision API | OCR 보조 | PaddleOCR 보완 |
| NCloud API | 파일 저장, 인프라 | 국내 데이터 주권 |

---

*이 문서는 AI 기반 아키텍처 설계 초안입니다. 실제 개발 진행 중 변경될 수 있습니다.*
