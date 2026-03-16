import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"


class PluginService:
    """시설물 플러그인 관리 서비스"""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def load_plugin(self, facility_type: str) -> dict:
        """플러그인 설정 로드 (캐시)"""
        if facility_type not in self._cache:
            config_path = PLUGINS_DIR / facility_type.lower() / "config.json"
            if not config_path.exists():
                raise ValueError(f"플러그인을 찾을 수 없습니다: {facility_type}")
            with open(config_path, encoding="utf-8") as f:
                self._cache[facility_type] = json.load(f)
        return self._cache[facility_type]

    def get_damage_codes(self, facility_type: str) -> list[dict]:
        config = self.load_plugin(facility_type)
        return config.get("damageCodes", [])

    def get_damage_code(self, facility_type: str, code: str) -> Optional[dict]:
        codes = self.get_damage_codes(facility_type)
        return next((c for c in codes if c["code"] == code), None)

    def get_drawing_types(self, facility_type: str) -> list[dict]:
        config = self.load_plugin(facility_type)
        return config.get("drawingTypes", [])

    def get_severity_grades(self, facility_type: str) -> list[dict]:
        config = self.load_plugin(facility_type)
        return config.get("severityGrades", [])

    def get_geofence_config(self, facility_type: str) -> dict:
        config = self.load_plugin(facility_type)
        return config.get("geofence", {"type": "circular", "bufferMeters": 500})

    def get_cad_layer_config(self, facility_type: str) -> dict:
        config = self.load_plugin(facility_type)
        return config.get("cadLayers", {})

    def get_location_schema(self, facility_type: str) -> dict:
        config = self.load_plugin(facility_type)
        return config.get("locationSchema", {})

    def list_available_plugins(self) -> list[str]:
        """설치된 플러그인 목록"""
        if not PLUGINS_DIR.exists():
            return []
        return [
            d.name.upper()
            for d in PLUGINS_DIR.iterdir()
            if d.is_dir() and (d / "config.json").exists()
        ]

    def generate_photo_number(
        self, facility_code: str, location: str, damage_code: str, sequence: int
    ) -> str:
        """
        사진 번호 자동 생성
        형식: {현장코드}-{위치}-{손상유형}-{순번:03d}
        예: BR001-G3-CR-004
        """
        # 손상코드 → 약어 변환
        code_abbr = {
            "C1": "CR", "C2": "CR",  # 균열
            "S1": "SP", "S2": "SP",  # 박리
            "E1": "RE",              # 철근노출
            "L1": "LK",              # 누수
            "R1": "RP",              # 라이닝박리
        }
        abbr = code_abbr.get(damage_code, damage_code[:2].upper())
        return f"{facility_code}-{location}-{abbr}-{sequence:03d}"


plugin_service = PluginService()
