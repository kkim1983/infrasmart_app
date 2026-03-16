"""
감사 로그 서비스 (Phase 2)

- SHA256 해시 체인: 각 이벤트는 이전 이벤트 해시를 포함 → 위변조 증명
- ECDSA 서명: 점검자 개인키로 서명 → 본인 확인
- Append-Only: INSERT만 허용 (UPDATE/DELETE 없음)
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.audit import AuditEvent


class AuditService:

    async def record_event(
        self,
        db: AsyncSession,
        event_type: str,
        actor_id: Optional[str],
        inspection_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        gps_snapshot: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
    ) -> AuditEvent:
        """
        감사 이벤트 기록 (Append-Only)

        event_type 목록:
          INSPECTION_STARTED | INSPECTION_ENDED
          DRAWING_UPLOADED | ANNOTATION_CREATED | ANNOTATION_SYNCED
          PHOTO_TAKEN | DAMAGE_CREATED | DAMAGE_UPDATED
          OCR_EXTRACTED | REPORT_EXPORTED | VOICE_TRANSCRIBED
          INSPECTOR_LOGIN | GEOFENCE_CHECKED
        """
        if payload is None:
            payload = {}

        # 이전 이벤트 해시 조회 (체인 연결)
        prev_hash = await self._get_last_hash(db, inspection_id)

        # 이벤트 해시 계산
        event_hash = self._compute_event_hash(
            event_type=event_type,
            actor_id=actor_id,
            entity_id=entity_id,
            payload=payload,
            prev_hash=prev_hash,
        )

        event = AuditEvent(
            event_type=event_type,
            inspection_id=uuid.UUID(inspection_id) if inspection_id else None,
            actor_id=uuid.UUID(actor_id) if actor_id else None,
            entity_type=entity_type,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            payload=payload,
            gps_snapshot=gps_snapshot,
            prev_hash=prev_hash,
            event_hash=event_hash,
            signature=signature,
        )

        db.add(event)
        await db.flush()
        await db.refresh(event)
        return event

    async def _get_last_hash(
        self,
        db: AsyncSession,
        inspection_id: Optional[str],
    ) -> Optional[str]:
        """해당 점검의 마지막 이벤트 해시 조회"""
        if inspection_id:
            result = await db.execute(
                select(AuditEvent.event_hash)
                .where(AuditEvent.inspection_id == inspection_id)
                .order_by(AuditEvent.id.desc())
                .limit(1)
            )
        else:
            result = await db.execute(
                select(AuditEvent.event_hash)
                .order_by(AuditEvent.id.desc())
                .limit(1)
            )
        row = result.scalar_one_or_none()
        return row

    def _compute_event_hash(
        self,
        event_type: str,
        actor_id: Optional[str],
        entity_id: Optional[str],
        payload: Dict[str, Any],
        prev_hash: Optional[str],
    ) -> str:
        """SHA256 이벤트 해시 계산"""
        data = {
            "event_type": event_type,
            "actor_id": actor_id or "",
            "entity_id": entity_id or "",
            "payload": json.dumps(payload, sort_keys=True, ensure_ascii=False),
            "prev_hash": prev_hash or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def verify_chain_integrity(
        self,
        db: AsyncSession,
        inspection_id: str,
    ) -> Dict[str, Any]:
        """
        해시 체인 무결성 검증

        Returns:
            {
                "is_valid": bool,
                "total_events": int,
                "broken_at": event_id or None,
                "message": str,
            }
        """
        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.inspection_id == inspection_id)
            .order_by(AuditEvent.id.asc())
        )
        events = result.scalars().all()

        if not events:
            return {
                "is_valid": True,
                "total_events": 0,
                "broken_at": None,
                "message": "감사 이벤트가 없습니다.",
            }

        prev_hash = None
        for event in events:
            # 이전 해시 검증
            if event.prev_hash != prev_hash:
                return {
                    "is_valid": False,
                    "total_events": len(events),
                    "broken_at": event.id,
                    "message": f"이벤트 ID {event.id}에서 해시 체인이 끊어졌습니다. 위변조 가능성이 있습니다.",
                }
            prev_hash = event.event_hash

        return {
            "is_valid": True,
            "total_events": len(events),
            "broken_at": None,
            "message": f"총 {len(events)}개 이벤트의 무결성이 확인되었습니다.",
        }

    def generate_key_pair(self) -> Dict[str, str]:
        """
        ECDSA P-256 키쌍 생성 (점검자 앱 최초 설치 시 호출)

        Returns:
            {"private_key_pem": "...", "public_key_pem": "..."}
        """
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return {
            "private_key_pem": private_pem,
            "public_key_pem": public_pem,
        }

    def sign_event(self, event_hash: str, private_key_pem: str) -> str:
        """이벤트 해시를 개인키로 ECDSA 서명 → base64 서명값"""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
        import base64

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            event_hash.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return base64.b64encode(signature).decode("utf-8")

    def verify_signature(
        self,
        event_hash: str,
        signature_b64: str,
        public_key_pem: str,
    ) -> bool:
        """서명 검증"""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.exceptions import InvalidSignature
        import base64

        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            signature = base64.b64decode(signature_b64)
            public_key.verify(
                signature,
                event_hash.encode("utf-8"),
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except (InvalidSignature, Exception):
            return False


audit_service = AuditService()
