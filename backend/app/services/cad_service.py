"""
CAD 서비스 - DXF 파일 생성 (Phase 2)

어노테이션 JSON → AutoCAD DXF 변환
ezdxf 라이브러리 기반, 레이어별 색상 매핑
"""

import math
import io
from typing import List, Dict, Any, Optional
import ezdxf
from ezdxf import colors
from ezdxf.math import Vec3


# 레이어 → DXF 색상 매핑 (ACI Color Index)
LAYER_COLOR_MAP = {
    "damage_new": colors.RED,           # 1 - 신규 손상 (빨강)
    "damage_exist": colors.YELLOW,      # 2 - 기존 손상 (노랑)
    "damage_expanded": colors.MAGENTA,  # 6 - 확장 손상 (주황/마젠타)
    "repaired": colors.GREEN,           # 3 - 보수 완료 (초록)
    "note": colors.WHITE,               # 7 - 메모 (흰색)
}

LAYER_LINETYPE_MAP = {
    "damage_new": "CONTINUOUS",
    "damage_exist": "DASHED",
    "damage_expanded": "DASHDOT",
    "repaired": "DOTTED",
    "note": "CONTINUOUS",
}

LAYER_LINEWEIGHT_MAP = {
    "damage_new": 50,      # 0.50mm
    "damage_exist": 35,    # 0.35mm
    "damage_expanded": 50,
    "repaired": 25,        # 0.25mm
    "note": 18,            # 0.18mm
}


class CadService:

    def generate_dxf(
        self,
        annotations: List[Dict[str, Any]],
        transform_matrix: Optional[Dict[str, Any]],
        drawing_meta: Dict[str, Any],
    ) -> bytes:
        """
        어노테이션 목록 → DXF bytes 생성

        transform_matrix: {scale_x, scale_y, offset_x, offset_y, rotation}
        drawing_meta: {drawing_name, drawing_type, facility_code, inspection_date}
        """
        doc = ezdxf.new(dxfversion="R2018")
        msp = doc.modelspace()

        # 기본 레이어 설정
        for layer_name, color in LAYER_COLOR_MAP.items():
            if layer_name not in doc.layers:
                layer = doc.layers.add(layer_name)
                layer.color = color
                layer.lineweight = LAYER_LINEWEIGHT_MAP.get(layer_name, 25)
            # linetype 설정 (DASHED, DOTTED는 로드 필요)

        # 도면 정보 블록 (우측 하단 타이틀블록)
        self._add_title_block(msp, drawing_meta)

        # 어노테이션 → DXF 엔티티 변환
        for ann in annotations:
            layer = ann.get("layer", "note")
            ann_type = ann.get("ann_type", "pen")
            coords = ann.get("coordinates", [])
            content = ann.get("content", "")
            style = ann.get("style", {})

            # 실제 좌표 우선, 없으면 픽셀 좌표 변환
            real_coords = ann.get("real_coordinates")
            if real_coords:
                transformed = real_coords
            elif transform_matrix:
                transformed = self._transform_coords(coords, ann_type, transform_matrix)
            else:
                # 변환 행렬 없으면 픽셀 좌표 그대로 (mm 단위 가정)
                transformed = coords

            self._draw_entity(msp, ann_type, layer, transformed, content, style)

        # DXF bytes 반환
        stream = io.BytesIO()
        doc.write(stream)
        stream.seek(0)
        return stream.read()

    def _transform_coords(
        self,
        coords: Any,
        ann_type: str,
        matrix: Dict[str, Any],
    ) -> Any:
        """픽셀 좌표 → 실제 좌표(mm) 변환"""
        sx = matrix.get("scale_x", 1.0)
        sy = matrix.get("scale_y", 1.0)
        ox = matrix.get("offset_x", 0.0)
        oy = matrix.get("offset_y", 0.0)
        rot = matrix.get("rotation", 0.0)

        def transform_point(px, py):
            # 스케일
            rx = px * sx
            ry = py * sy
            # 회전
            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            rx2 = rx * cos_r - ry * sin_r
            ry2 = rx * sin_r + ry * cos_r
            # 오프셋
            return rx2 + ox, ry2 + oy

        if ann_type == "pen" and isinstance(coords, list):
            return [{"x": transform_point(p["x"], p["y"])[0],
                     "y": transform_point(p["x"], p["y"])[1]}
                    for p in coords if "x" in p and "y" in p]
        elif isinstance(coords, dict):
            result = {}
            if "x" in coords and "y" in coords:
                result["x"], result["y"] = transform_point(coords["x"], coords["y"])
            if "w" in coords:
                result["w"] = coords["w"] * sx
            if "h" in coords:
                result["h"] = coords["h"] * sy
            return result
        return coords

    def _draw_entity(
        self,
        msp,
        ann_type: str,
        layer: str,
        coords: Any,
        content: str,
        style: Dict[str, Any],
    ):
        """어노테이션 → DXF 엔티티"""
        dxf_attribs = {"layer": layer}
        color = LAYER_COLOR_MAP.get(layer, colors.WHITE)
        dxf_attribs["color"] = color

        if ann_type == "pen" and isinstance(coords, list) and len(coords) >= 2:
            points = [(p["x"], p["y"], 0) for p in coords]
            if len(points) >= 2:
                msp.add_lwpolyline(points, dxfattribs=dxf_attribs)

        elif ann_type in ("circle", "rect"):
            if isinstance(coords, dict):
                x = coords.get("x", 0)
                y = coords.get("y", 0)
                w = coords.get("w", 10)
                h = coords.get("h", 10)
                if ann_type == "circle":
                    radius = max(w, h) / 2
                    msp.add_circle((x, y, 0), radius=radius, dxfattribs=dxf_attribs)
                else:
                    # 직사각형 → 4선 폴리라인
                    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                    msp.add_lwpolyline(pts, close=True, dxfattribs=dxf_attribs)

        elif ann_type == "arrow" and isinstance(coords, list) and len(coords) >= 2:
            start = (coords[0]["x"], coords[0]["y"], 0)
            end = (coords[-1]["x"], coords[-1]["y"], 0)
            # 화살표 선
            msp.add_line(start, end, dxfattribs=dxf_attribs)
            # 화살촉 (짧은 두 선)
            self._draw_arrowhead(msp, start, end, layer, color)

        elif ann_type in ("text", "voice") and content:
            if isinstance(coords, dict):
                x = coords.get("x", 0)
                y = coords.get("y", 0)
            elif isinstance(coords, list) and len(coords) > 0:
                x = coords[0].get("x", 0)
                y = coords[0].get("y", 0)
            else:
                x, y = 0, 0
            font_size = style.get("fontSize", 3.0)
            msp.add_text(
                content,
                dxfattribs={
                    "layer": layer,
                    "color": color,
                    "height": font_size,
                    "insert": (x, y, 0),
                },
            )

    def _draw_arrowhead(self, msp, start, end, layer, color):
        """화살촉 생성"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx ** 2 + dy ** 2)
        if length == 0:
            return
        ux, uy = dx / length, dy / length
        arrow_size = min(length * 0.15, 5.0)  # 화살촉 크기 (최대 5mm)

        # 좌우 날개
        perp_x, perp_y = -uy, ux
        wing1 = (
            end[0] - ux * arrow_size + perp_x * arrow_size * 0.4,
            end[1] - uy * arrow_size + perp_y * arrow_size * 0.4,
            0,
        )
        wing2 = (
            end[0] - ux * arrow_size - perp_x * arrow_size * 0.4,
            end[1] - uy * arrow_size - perp_y * arrow_size * 0.4,
            0,
        )
        dxf_attribs = {"layer": layer, "color": color}
        msp.add_line(end, wing1, dxfattribs=dxf_attribs)
        msp.add_line(end, wing2, dxfattribs=dxf_attribs)

    def _add_title_block(self, msp, meta: Dict[str, Any]):
        """도면 제목 블록 (우측 하단)"""
        x0, y0 = 0, -50  # 타이틀블록 위치
        info_lines = [
            f"시설물: {meta.get('facility_code', '')}",
            f"도면유형: {meta.get('drawing_type', '')}",
            f"도면명: {meta.get('drawing_name', '')}",
            f"점검일: {meta.get('inspection_date', '')}",
            f"생성: InfraSmart v1.0",
        ]
        for i, line in enumerate(info_lines):
            msp.add_text(
                line,
                dxfattribs={
                    "layer": "note",
                    "height": 2.5,
                    "insert": (x0, y0 - i * 5, 0),
                    "color": colors.WHITE,
                },
            )


cad_service = CadService()
