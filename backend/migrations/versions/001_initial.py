"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # facility_types
    op.create_table('facility_types',
        sa.Column('code', sa.String(2), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('plugin_version', sa.String(20), default='1.0.0'),
        sa.Column('config', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # companies
    op.create_table('companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('registration_no', sa.String(20), unique=True),
        sa.Column('license_no', sa.String(50)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # inspectors
    op.create_table('inspectors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('license_no', sa.String(50), unique=True, nullable=False),
        sa.Column('license_type', sa.String(100)),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(200)),
        sa.Column('password_hash', sa.String(200), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id')),
        sa.Column('public_key', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # facilities
    op.create_table('facilities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('facility_type', sa.String(2), sa.ForeignKey('facility_types.code'), nullable=False),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('location_name', sa.String(200)),
        sa.Column('geofence_type', sa.String(20), default='circular'),
        sa.Column('geofence_data', JSONB),
        sa.Column('facility_meta', JSONB),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # inspections
    op.create_table('inspections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('facility_id', UUID(as_uuid=True), sa.ForeignKey('facilities.id'), nullable=False),
        sa.Column('inspector_id', UUID(as_uuid=True), sa.ForeignKey('inspectors.id'), nullable=False),
        sa.Column('inspection_type', sa.String(20), default='ROUTINE'),
        sa.Column('status', sa.String(20), default='DRAFT'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('gps_track', JSONB, default=list),
        sa.Column('device_info', JSONB),
        sa.Column('notes', sa.String(2000)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # drawings
    op.create_table('drawings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('inspection_id', UUID(as_uuid=True), sa.ForeignKey('inspections.id'), nullable=False),
        sa.Column('drawing_type', sa.String(10), nullable=False),
        sa.Column('drawing_name', sa.String(200)),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('page_number', sa.Integer, default=1),
        sa.Column('transform_matrix', JSONB),
        sa.Column('calibration_points', JSONB),
        sa.Column('scale_text', sa.String(20)),
        sa.Column('coord_system', sa.String(20), default='cartesian'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # damage_records
    op.create_table('damage_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('inspection_id', UUID(as_uuid=True), sa.ForeignKey('inspections.id'), nullable=False),
        sa.Column('damage_code', sa.String(10), nullable=False),
        sa.Column('damage_name', sa.String(100)),
        sa.Column('location_data', JSONB),
        sa.Column('dimensions', JSONB),
        sa.Column('severity_grade', sa.String(2)),
        sa.Column('is_new', sa.Boolean, default=True),
        sa.Column('is_expanded', sa.Boolean, default=False),
        sa.Column('is_repaired', sa.Boolean, default=False),
        sa.Column('repair_date', sa.Date),
        sa.Column('repair_method', sa.String(200)),
        sa.Column('notes', sa.Text),
        sa.Column('prev_record_id', UUID(as_uuid=True), sa.ForeignKey('damage_records.id')),
        sa.Column('drawing_ref', JSONB),
        sa.Column('local_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # annotations
    op.create_table('annotations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('drawing_id', UUID(as_uuid=True), sa.ForeignKey('drawings.id'), nullable=False),
        sa.Column('ann_type', sa.String(20), nullable=False),
        sa.Column('layer', sa.String(30), nullable=False),
        sa.Column('coordinates', JSONB, nullable=False),
        sa.Column('real_coordinates', JSONB),
        sa.Column('content', sa.Text),
        sa.Column('style', JSONB),
        sa.Column('damage_record_id', UUID(as_uuid=True), sa.ForeignKey('damage_records.id')),
        sa.Column('local_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('inspectors.id')),
    )

    # photos
    op.create_table('photos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('inspection_id', UUID(as_uuid=True), sa.ForeignKey('inspections.id'), nullable=False),
        sa.Column('damage_record_id', UUID(as_uuid=True), sa.ForeignKey('damage_records.id')),
        sa.Column('photo_number', sa.String(50), unique=True, nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('file_size', sa.Integer),
        sa.Column('gps', JSONB),
        sa.Column('exif_data', JSONB),
        sa.Column('damage_code', sa.String(10)),
        sa.Column('damage_description', sa.Text),
        sa.Column('drawing_ref', JSONB),
        sa.Column('ai_analysis', JSONB),
        sa.Column('taken_at', sa.DateTime(timezone=True)),
        sa.Column('taken_by', UUID(as_uuid=True), sa.ForeignKey('inspectors.id')),
        sa.Column('local_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # audit_events (Append-Only)
    op.create_table('audit_events',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('inspection_id', UUID(as_uuid=True)),
        sa.Column('actor_id', UUID(as_uuid=True)),
        sa.Column('entity_type', sa.String(30)),
        sa.Column('entity_id', UUID(as_uuid=True)),
        sa.Column('payload', JSONB, nullable=False, server_default='{}'),
        sa.Column('gps_snapshot', JSONB),
        sa.Column('prev_hash', sa.String(64)),
        sa.Column('event_hash', sa.String(64)),
        sa.Column('signature', sa.Text),
        sa.Column('tsa_token', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 인덱스
    op.create_index('ix_inspections_inspector', 'inspections', ['inspector_id'])
    op.create_index('ix_inspections_facility', 'inspections', ['facility_id'])
    op.create_index('ix_drawings_inspection', 'drawings', ['inspection_id'])
    op.create_index('ix_annotations_drawing', 'annotations', ['drawing_id'])
    op.create_index('ix_photos_inspection', 'photos', ['inspection_id'])
    op.create_index('ix_audit_inspection', 'audit_events', ['inspection_id'])
    op.create_index('ix_audit_created', 'audit_events', ['created_at'])

    # 교량 플러그인 기본 데이터 삽입
    op.execute("""
        INSERT INTO facility_types (code, name, plugin_version, config) VALUES (
            'BR', '교량', '1.0.0',
            '{"facilityType": "BR", "name": "교량", "version": "1.0.0"}'::jsonb
        ) ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('photos')
    op.drop_table('annotations')
    op.drop_table('damage_records')
    op.drop_table('drawings')
    op.drop_table('inspections')
    op.drop_table('facilities')
    op.drop_table('inspectors')
    op.drop_table('companies')
    op.drop_table('facility_types')
