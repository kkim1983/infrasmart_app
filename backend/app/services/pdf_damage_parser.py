"""
PDF 외관조사망도 손상물량표 파서
동적 테이블 감지 방식 - 도면마다 위치가 달라도 동작

핵심 전략:
1. 페이지에서 '손상물량표' 헤더 텍스트로 테이블 우측 경계 감지
2. '번호', '신/구', '부재명' 헤더 행으로 컬럼 x 위치 동적 계산
3. 하단 타이틀블록 '위치' 셀에서 위치코드 추출
4. 페이지 상단 섹션 제목에서 부재 유형 추출
5. 한글 텍스트 정규화 (중복음절 제거, 내부공백 제거)
"""
import re
from collections import defaultdict
from typing import Optional, List, Dict, Tuple

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ── 알려진 부재명 ──────────────────────────────────────────────
KNOWN_MEMBERS = [
    "가로보", "거더", "교각", "교대", "교량받침", "교면포장",
    "바닥판", "방호벽", "배수시설", "신축이음장치", "점검로",
    "중앙분리대", "캔틸레버",
]

SECTION_MEMBER_MAP = {
    '교각': '교각', '교대': '교대', '교량받침': '교량받침',
    '바닥판': '바닥판', '바닥판하면': '바닥판',
    '거더': '거더', '거더및가로보': '거더', '가로보': '가로보',
    '신축이음장치': '신축이음장치', '신축이음': '신축이음장치',
    '교면포장': '교면포장',
    '난간중분대': '방호벽',
    '방호벽': '방호벽', '중앙분리대': '중앙분리대',
}

# 기본 컬럼 상대적 오프셋 (테이블 좌측 가장자리 기준, pt 단위)
# '번호' 컬럼이 테이블 왼쪽 기준점
# ※ 경계가 겹치지 않도록 설계 (damage ← num1 ← num2 순으로 명확히 분리)
DEFAULT_COL_OFFSETS = {
    'row_num': (0, 28),
    'new_old':  (28, 50),
    'member':   (50, 80),
    'damage':   (80, 122),   # num1 시작 전에 끝남
    'num1':     (122, 147),  # 균열폭(mm)  ← m 단위 전용
    'num2':     (147, 172),  # 길이(m)     ← m/㎡ 공통
    'num3':     (172, 198),  # 너비(m)     ← ㎡ 단위 전용
    'unit':     (196, 218),
    'count':    (216, 238),
    'qty':      (236, 260),
    'note':     (258, 380),
}


# ── 텍스트 정규화 ──────────────────────────────────────────────
def normalize_korean(text: str) -> str:
    """중복 음절 제거 + 한글 내부 공백 제거"""
    if not text:
        return ''
    text = text.strip()
    # 연속 중복 문자 압축 (한글)
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        j = i + 1
        while j < len(text) and text[j] == ch:
            j += 1
        out.append(ch)
        i = j
    text = ''.join(out)
    # 한글 사이 공백 제거
    text = re.sub(r'(?<=[\uAC00-\uD7A3])\s+(?=[\uAC00-\uD7A3])', '', text)
    return text.strip()


def normalize_member(raw: str, section_default: str = '') -> str:
    """부재명 → 표준 부재명"""
    text = normalize_korean(raw or '')
    if not text:
        return section_default
    for m in KNOWN_MEMBERS:
        if m in text:
            return m
    return text or section_default


# ── 위치코드 추출 ──────────────────────────────────────────────
def extract_location_from_title_block(words: list) -> Optional[str]:
    """
    하단 타이틀블록 '위치' 셀에서 위치코드 추출.
    '위치' 레이블 우측 값 읽기. 복수 위치인 경우 마지막 값 사용.
    다양한 y좌표를 처리하기 위해 상대적 탐색 사용.
    """
    # '위치' 레이블 찾기 (여러 셀로 쪼개질 수 있음: '위', '치')
    loc_label_words = [
        w for w in words
        if w['text'].strip() in ('위치', '위', '치') and w['top'] > 540
    ]
    if not loc_label_words:
        return None

    # 레이블 y 범위 기준
    label_tops = [w['top'] for w in loc_label_words]
    label_y_min = min(label_tops) - 3
    label_y_max = max(label_tops) + 3
    label_x_max = max(w['x1'] for w in loc_label_words)

    # 레이블 우측, 같은 y 범위 단어들 = 위치값
    loc_words = [
        w for w in words
        if label_y_min <= w['top'] <= label_y_max
        and w['x0'] > label_x_max + 5
        and w['x0'] < label_x_max + 150
        and w['text'].strip() not in ('도면번호', '위치', '위', '치', '')
    ]

    if not loc_words:
        return None

    # x 정렬 → 마지막 값
    sorted_lw = sorted(loc_words, key=lambda w: w['x0'])
    last_text = sorted_lw[-1]['text'].strip().rstrip(',')
    base = re.sub(r'\(\d+\)$', '', last_text).strip()

    if re.match(r'^[SPA]\d{1,2}$', base):
        return base

    all_text = ' '.join(w['text'] for w in sorted_lw)
    m = re.search(r'\b([SPA]\d{1,2})\b', all_text)
    return m.group(1) if m else None


def extract_section_from_header(words: list) -> Optional[str]:
    """
    페이지 상단 섹션 제목에서 부재 유형 추출.
    우선순위: 상단 헤더(top<45) > 하단 도면명 셀
    """
    # 1순위: 상단 섹션 헤더 (top<45, 페이지 우측 중간 또는 중앙)
    # 섹션 제목은 보통 '손상물량표' 헤더 텍스트 근처 왼쪽
    header_words = [w for w in words if w['top'] < 45 and w['x0'] > page_width(words) * 0.6]
    if header_words:
        htext = normalize_korean(
            ' '.join(w['text'] for w in sorted(header_words, key=lambda w: w['x0']))
        )
        htext_clean = re.sub(r'\([^)]*\)', '', htext)
        htext_clean = re.sub(r'\s+', '', htext_clean)
        for key, val in SECTION_MEMBER_MAP.items():
            if key in htext_clean:
                return val

    # 2순위 폴백: 하단 도면명 셀
    dname_words = [
        w for w in words
        if w['top'] > 540 and w['top'] < 555
        and w['x0'] > 440 and w['x0'] < 540
        and '외관조사' not in w['text'] and '도면명' not in w['text']
    ]
    if dname_words:
        dname = normalize_korean(
            ' '.join(w['text'] for w in sorted(dname_words, key=lambda w: w['x0']))
        )
        dname_clean = re.sub(r'\s+', '', dname)
        for key, val in SECTION_MEMBER_MAP.items():
            if key in dname_clean:
                return val

    return None


def page_width(words: list) -> float:
    """단어들의 최대 x 값으로 페이지 너비 추정"""
    if not words:
        return 595.0  # A4 기본
    return max(w['x1'] for w in words)


# ── 동적 테이블 경계 감지 ──────────────────────────────────────
def detect_table_region(words: list) -> Optional[Tuple[float, float]]:
    """
    '손상물량표' 헤더 텍스트 위치로 테이블 영역 감지.
    반환: (table_left_x, table_right_x)
    """
    # '손상물량표' 텍스트 찾기
    qty_header = [w for w in words if '손상물량표' in w['text'] and w['top'] < 50]
    if qty_header:
        hdr = qty_header[0]
        # 테이블은 보통 손상물량표의 왼쪽에서 시작
        # 실제 테이블 컬럼 헤더('번호')의 x0를 찾아야 함
        pass

    # '번호' 헤더 찾기 (테이블 첫 컬럼)
    num_headers = [w for w in words if w['text'] == '번호' and 45 < w['top'] < 58]
    if num_headers:
        table_left = min(w['x0'] for w in num_headers) - 5
        # 비고 컬럼의 오른쪽 끝
        note_words = [w for w in words if w['text'] in ('비고', '비', '고') and 45 < w['top'] < 58]
        if note_words:
            table_right = max(w['x1'] for w in note_words) + 50
        else:
            table_right = table_left + 400  # 기본 너비
        return (table_left, table_right)

    return None


def detect_columns(words: list, table_left: float) -> dict:
    """
    테이블 헤더 행(top 45~58)에서 컬럼 x 위치 동적 감지.
    번호, 신/구, 부재명, 단위, 개소, 물량 키워드의 실제 x 위치 사용.
    """
    header_words = [w for w in words if 45 < w['top'] < 58 and w['x0'] > table_left]

    anchors = {}
    for w in header_words:
        cx = (w['x0'] + w['x1']) / 2
        txt = w['text'].strip()
        if txt == '번호':
            anchors['row_num'] = cx
        elif txt == '신/구':
            anchors['new_old'] = cx
        elif txt == '부재명':
            anchors['member'] = cx
        elif txt == '단위':
            anchors['unit'] = cx
        elif txt == '개소':
            anchors['count'] = cx
        elif txt == '물량':
            anchors['qty'] = cx
        elif (
            '폭(mm)' in txt or '폭(㎜)' in txt
            or txt in ('균열폭', '폭')
            or ('폭' in txt and ('mm' in txt.lower() or '㎜' in txt))
        ):
            # '폭(mm)길이(m)너비(m)' 처럼 3개 컬럼이 합쳐진 경우,
            # 중앙값 대신 좌측 끝(x0)을 사용해야 num1/num2 경계가 정확함
            anchors['dim'] = w['x0']

    if len(anchors) < 3:
        # 감지 실패 - 기본 오프셋 사용
        col_x = {}
        for col, (lo, hi) in DEFAULT_COL_OFFSETS.items():
            col_x[col] = (table_left + lo, table_left + hi)
        return col_x

    # 감지된 앵커 기준 경계 계산
    col_x = {}
    rn = anchors.get('row_num', table_left + 15)
    no = anchors.get('new_old', rn + 20)
    mb = anchors.get('member', no + 25)
    dm = anchors.get('dim', mb + 75)
    un = anchors.get('unit', dm + 45)
    ct = anchors.get('count', un + 20)
    qt = anchors.get('qty', ct + 22)

    def mid(a, b): return (a + b) / 2

    col_x['row_num'] = (rn - 15, mid(rn, no))
    col_x['new_old']  = (mid(rn, no), mid(no, mb))
    col_x['member']   = (mid(no, mb), mid(mb, mb + (dm - mb) * 0.4))
    # damage 는 num1(균열폭) 시작점보다 8pt 앞에서 끝남 → 겹침 방지
    col_x['damage']   = (mid(mb, mb + (dm - mb) * 0.4), dm - 8)
    # 수치 컬럼 3분할:
    #   num1 = 균열폭(mm)  ← m 단위 행의 첫 번째 숫자 (x ≈ dm+6)
    #   num2 = 길이(m)     ← m/㎡ 공통 두 번째 숫자  (x ≈ dm+26)
    #   num3 = 너비(m)     ← ㎡ 단위 행의 세 번째 숫자 (x ≈ dm+47)
    _n_lo = dm - 8
    _n_hi = un - 5
    _n_w  = (_n_hi - _n_lo) / 3
    col_x['num1'] = (_n_lo,            _n_lo + _n_w)
    col_x['num2'] = (_n_lo + _n_w,     _n_lo + 2 * _n_w)
    col_x['num3'] = (_n_lo + 2 * _n_w, _n_hi)
    col_x['unit']     = (un - 10, mid(un, ct))
    col_x['count']    = (mid(un, ct), mid(ct, qt))
    col_x['qty']      = (mid(ct, qt), qt + 18)
    col_x['note']     = (qt + 18, qt + 120)

    return col_x


def classify_word(w: dict, col_x: dict) -> Optional[str]:
    cx = (w['x0'] + w['x1']) / 2
    for col, (lo, hi) in col_x.items():
        if lo <= cx <= hi:
            return col
    return None


def is_number(s: str) -> bool:
    try:
        float(str(s).replace(',', '').strip())
        return True
    except:
        return False


# ── 페이지 파싱 ──────────────────────────────────────────────
def parse_page(page, page_num: int, bridge_name: str = '') -> Tuple[List[dict], Optional[str], Optional[str]]:
    """
    한 PDF 페이지에서 손상 레코드 추출.
    
    반환: (records, location_code, section_name)
    """
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)

    if not words:
        return [], None, None

    # 테이블 영역 감지
    table_region = detect_table_region(words)
    if not table_region:
        return [], None, None

    table_left, table_right = table_region
    table_words = [w for w in words if w['x0'] >= table_left - 5]

    if not table_words:
        return [], None, None

    # 위치코드 + 섹션명
    location = extract_location_from_title_block(words)
    section  = extract_section_from_header(words)

    # 동적 컬럼 경계
    col_x = detect_columns(words, table_left)

    # 데이터 영역 (테이블 헤더 아래 ~ 범례 위)
    # 헤더 행 y: 보통 45~58
    data_min_y = 60
    data_max_y = 420  # 범례 영역 제외

    data_words = [w for w in table_words if data_min_y < w['top'] < data_max_y]
    if not data_words:
        return [], location, section

    # y 그루핑 (3pt 허용)
    row_groups: dict = defaultdict(list)
    for w in data_words:
        y_key = round(w['top'] / 3) * 3
        row_groups[y_key].append(w)

    records: list = []
    current: Optional[dict] = None

    for y in sorted(row_groups.keys()):
        row_words = sorted(row_groups[y], key=lambda w: w['x0'])

        cols: dict = defaultdict(list)
        for w in row_words:
            col = classify_word(w, col_x)
            if col:
                cols[col].append(w['text'])

        if not cols:
            continue

        if 'row_num' in cols:
            num_txt = ' '.join(cols['row_num']).strip()
            if is_number(num_txt):
                if current:
                    records.append(current)
                def _nums(col_key):
                    """num1/num2/num3 컬럼에서 숫자 토큰만 추출.
                    손상명 텍스트(예: '균열')가 숫자 컬럼 영역에 흘러들어올 때 제거."""
                    return ' '.join(t for t in cols.get(col_key, []) if is_number(t)).strip()

                current = {
                    'row_num': num_txt,
                    'new_old': ' '.join(cols.get('new_old', [])).strip(),
                    'member':  ' '.join(cols.get('member', [])).strip(),
                    'damage':  ' '.join(cols.get('damage', [])).strip(),
                    'num1':    _nums('num1'),
                    'num2':    _nums('num2'),
                    'num3':    _nums('num3'),
                    'unit':    ' '.join(cols.get('unit', [])).strip(),
                    'count':   ' '.join(cols.get('count', [])).strip(),
                    'qty':     ' '.join(cols.get('qty', [])).strip(),
                    'note':    ' '.join(cols.get('note', [])).strip(),
                }
        elif current is not None:
            # 이전 레코드 계속
            if 'damage' in cols:
                extra = ' '.join(cols['damage'])
                current['damage'] = (current['damage'] + ' ' + extra).strip()
            for f in ('new_old', 'member', 'unit', 'count', 'qty', 'note'):
                if f in cols and not current.get(f):
                    current[f] = ' '.join(cols[f]).strip()
            for f in ('num1', 'num2', 'num3'):
                if f in cols and not current.get(f):
                    current[f] = ' '.join(t for t in cols[f] if is_number(t)).strip()

    if current:
        records.append(current)

    # 후처리
    result = []
    for r in records:
        member = normalize_member(r['member'], section or '')
        damage = normalize_korean(r['damage'])
        unit   = r['unit'].strip()
        if unit.lower() in ('ea',):
            unit = 'EA'

        num1 = r['num1'].strip()
        num2 = r['num2'].strip()
        num3 = r.get('num3', '').strip()
        crack_w: Optional[float] = None
        length:  Optional[float] = None
        width:   Optional[float] = None

        def to_float(s: str) -> Optional[float]:
            try:
                return float(s.replace(',', ''))
            except Exception:
                return None

        if unit == 'm':
            # 3컬럼 분리: num1=균열폭, num2=길이
            crack_w = to_float(num1)
            length  = to_float(num2)
        elif unit == '㎡':
            # 3컬럼 분리: num2=길이, num3=너비
            length = to_float(num2)
            width  = to_float(num3)
        elif unit == 'EA':
            pass
        else:
            # 알 수 없는 단위: 가용한 숫자 중 첫 번째
            length = to_float(num2) or to_float(num1)

        count_s = r['count'].strip()
        # 개소 → int (가능한 경우)
        try:
            count_val: int | str = int(float(count_s)) if count_s else 1
        except Exception:
            count_val = count_s or 1

        # 번호 → int
        try:
            row_num_val: int | str = int(float(r['row_num']))
        except Exception:
            row_num_val = r['row_num']

        result.append({
            '교량명':    bridge_name,
            '부재명':    member,
            '부재위치':  location or '',
            '세부위치':  '',
            '번호':      row_num_val,
            '신/구':     r['new_old'].strip() or '구',
            '손상내용':  damage,
            '균열폭(㎜)': crack_w,   # float or None
            '길이(m)':   length,     # float or None
            '너비(m)':   width,      # float or None
            '개소':      count_val,
            '단위':      unit,
            '결함상태':  '',
            '비고':      r['note'],
            '_page':     page_num,
            '_section':  section or '',
        })

    return result, location, section


# ── 전체 PDF 파싱 ─────────────────────────────────────────────
def parse_pdf(pdf_path: str, bridge_name: str = '') -> Dict:
    """
    PDF 전체 파싱 → 손상 레코드 리스트 반환.
    
    반환 형식:
    {
        "bridge_name": str,
        "total_pages": int,
        "total_records": int,
        "records": [...],
        "page_summary": [...]
    }
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber 패키지가 필요합니다: pip install pdfplumber")

    all_records  = []
    page_summary = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            recs, loc, sec = parse_page(page, i + 1, bridge_name)
            if recs:
                all_records.extend(recs)
                page_summary.append({
                    'page': i + 1,
                    'location': loc,
                    'section': sec,
                    'count': len(recs),
                })

    return {
        'bridge_name':   bridge_name,
        'total_pages':   total_pages,
        'total_records': len(all_records),
        'records':       all_records,
        'page_summary':  page_summary,
    }


# ── Excel 내보내기 ────────────────────────────────────────────
def export_to_excel(records: List[dict], output_path: str, bridge_name: str = '') -> str:
    """
    레코드 목록 → Excel 파일 생성.
    참조 Excel 형식과 동일한 컬럼 구조 사용.
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl 패키지가 필요합니다: pip install openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "손상물량표"

    # 참조 파일과 동일한 22열 구조
    # A-O: 기본 15열, P: 손상면적(면적율), Q: 손상정도 수식
    COLS = [
        '교량명', '부재명', '부재위치', '세부위치', '번 호', '신/구',
        '손상내용', '균열폭\n(㎜)', '길이\n(m)', '너비\n(m)', '개소', '단위',
        '결함\n상태', '손상물량', '비고', '손상면적\n(면적율)', '손상정도',
    ]
    # 컬럼 인덱스 (1-based)
    COL_L = 12   # 단위
    COL_I = 9    # 길이(m)
    COL_J = 10   # 너비(m)
    COL_K = 11   # 개소
    COL_N = 14   # 손상물량
    COL_H = 8    # 균열폭(㎜)

    H_FILL = PatternFill('solid', fgColor='1F4E79')
    H_FONT = Font(color='FFFFFF', bold=True, size=9)
    THIN   = Side(style='thin')
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    C_FILLS = {
        'S': PatternFill('solid', fgColor='DDEEFF'),
        'P': PatternFill('solid', fgColor='FFEEEE'),
        'A': PatternFill('solid', fgColor='EEFFEE'),
    }

    for ci, h in enumerate(COLS, 1):
        c = ws.cell(1, ci, h)
        c.fill, c.font, c.border = H_FILL, H_FONT, BORDER
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[1].height = 24

    for ri, rec in enumerate(records, 2):
        loc  = rec.get('부재위치', '')
        fill = C_FILLS.get(loc[:1] if loc else '', PatternFill('solid', fgColor='FFFFFF'))

        # 길이/너비/균열폭: float 또는 None (공백 문자열 대신)
        length_v = rec.get('길이(m)')
        width_v  = rec.get('너비(m)')
        crack_v  = rec.get('균열폭(㎜)')

        vals = [
            rec.get('교량명', bridge_name),   # A
            rec.get('부재명', ''),             # B
            rec.get('부재위치', ''),            # C
            rec.get('세부위치', ''),            # D
            rec.get('번호', ''),               # E
            rec.get('신/구', ''),              # F
            rec.get('손상내용', ''),            # G
            crack_v if crack_v is not None else '',  # H 균열폭
            length_v if length_v is not None else '',  # I 길이
            width_v if width_v is not None else '',    # J 너비
            rec.get('개소', ''),               # K
            rec.get('단위', ''),               # L
            rec.get('결함상태', ''),            # M
            None,                             # N 손상물량 (수식으로 채움)
            rec.get('비고', ''),               # O
            None,                             # P 손상면적(면적율)
            None,                             # Q 손상정도 (수식으로 채움)
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(ri, ci, v)
            c.fill, c.border = fill, BORDER
            c.font = Font(size=9)
            c.alignment = Alignment(
                horizontal='center' if ci in (5, 6, 8, 9, 10, 11, 12, 14) else 'left'
            )

        # 손상물량 수식 (N열): =IF(L{r}="m",I{r}*K{r},IF(L{r}="㎡",I{r}*J{r}*K{r},IF(L{r}="EA",K{r},"")))
        qty_cell = ws.cell(ri, COL_N)
        qty_cell.value = (
            f'=IF(L{ri}="m",I{ri}*K{ri},'
            f'IF(L{ri}="㎡",I{ri}*J{ri}*K{ri},'
            f'IF(L{ri}="EA",K{ri},"")))'
        )
        qty_cell.fill, qty_cell.border = fill, BORDER
        qty_cell.font = Font(size=9)
        qty_cell.alignment = Alignment(horizontal='center')
        qty_cell.number_format = '0.00'

        # 손상정도 수식 (Q열): =IF(AND(H{r}>=0.2,L{r}="m"),N{r}*0.25,IF(AND(0.1<=H{r},L{r}="m"),0,N{r}))
        deg_cell = ws.cell(ri, 17)
        deg_cell.value = (
            f'=IF(AND(H{ri}>=0.2,L{ri}="m"),N{ri}*0.25,'
            f'IF(AND(0.1<=H{ri},L{ri}="m"),0,N{ri}))'
        )
        deg_cell.fill, deg_cell.border = fill, BORDER
        deg_cell.font = Font(size=9)
        deg_cell.alignment = Alignment(horizontal='center')

    for ci, w in enumerate([10, 10, 8, 8, 5, 5, 22, 8, 8, 8, 5, 5, 8, 8, 15, 10, 10], 1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}1"
    ws.freeze_panes = 'A2'

    # 부재별 요약 시트
    ws2 = wb.create_sheet("부재별요약")
    ws2.append(['부재명', '부재위치', '건수', '균열길이합(m)', '면적합(㎡)', 'EA합'])
    summ: dict = defaultdict(lambda: {'n': 0, 'm': 0.0, 'm2': 0.0, 'ea': 0})
    for r in records:
        k = (r.get('부재명', ''), r.get('부재위치', ''))
        summ[k]['n'] += 1
        try:
            cnt = float(r.get('개소') or 1)
            if r.get('단위') == 'm' and r.get('길이(m)') is not None:
                summ[k]['m'] += float(r['길이(m)']) * cnt
            elif r.get('단위') == '㎡' and r.get('길이(m)') is not None and r.get('너비(m)') is not None:
                summ[k]['m2'] += float(r['길이(m)']) * float(r['너비(m)']) * cnt
            elif r.get('단위') == 'EA':
                summ[k]['ea'] += int(cnt)
        except Exception:
            pass
    for (mem, loc), st in sorted(summ.items()):
        ws2.append([mem, loc, st['n'], round(st['m'], 2), round(st['m2'], 2), st['ea']])

    wb.save(output_path)
    return output_path


# ── CLI ───────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        print("사용법: python pdf_damage_parser.py <PDF경로> [교량명] [출력경로]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    bridge   = sys.argv[2] if len(sys.argv) > 2 else ''
    out_xlsx = sys.argv[3] if len(sys.argv) > 3 else pdf_path.replace('.pdf', '_추출.xlsx')

    result = parse_pdf(pdf_path, bridge)
    print(f"총 {result['total_records']}건 추출 (전체 {result['total_pages']}페이지)")

    export_to_excel(result['records'], out_xlsx, bridge)
    print(f"Excel 저장: {out_xlsx}")
