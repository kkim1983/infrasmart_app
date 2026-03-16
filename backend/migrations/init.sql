-- InfraSmart DB 초기화 SQL
-- Docker 컨테이너 최초 실행 시 자동 적용

-- pgvector 확장 (Phase 2: 안면인식)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 텍스트 검색

-- audit_events Append-Only 강제
-- (Alembic 마이그레이션 후 아래 정책 적용)
-- ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY audit_insert_only ON audit_events FOR INSERT WITH CHECK (true);

-- 기본 시설물 유형 (교량) 초기 데이터
-- Alembic seed 후 실행됩니다
