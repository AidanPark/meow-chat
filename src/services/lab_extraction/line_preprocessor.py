"""
라인 전처리 모듈 (4.x 단계)

- 4.1: OCR 결과에서 토큰 추출(기하 포함)
- 4.2: y-기반 라인 인덱스 부여
- 4.3: 라인 단위 그룹핑
- 4.4: 라인 선두(Name 열) 분리 토큰 병합(괄호형 등) + 괄호 앞 공백 제거
- 4.5: 값/단위 분리(보존-분리)
- 4.6: 값 경고 플래그(H/L/N) 경량 주석
- 4.7: 상태 토큰 제거(NORMAL/LOW/HIGH)

구성 옵션을 가진 클래스 API(LinePreprocessor)와 간단한 함수형 API를 함께 제공합니다.
PaddleOCRService에 있던 동일 로직을 모듈로 분리하여 재사용성을 높였습니다.
모든 주석/문서화는 한국어로 제공됩니다.
"""
from __future__ import annotations

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json
import re

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

# -----------------------
# 공개 API
# -----------------------

def extract_tokens_with_geometry(ocr_result) -> List[Dict[str, object]]:
    """OCR 결과에서 텍스트/신뢰도/좌표 파생값을 추출하여 리스트로 반환.

    반환 토큰(dict) 필드:
      - text: str
      - confidence: float | None
      - y_top, y_bottom, y_center: int | None
      - raw_h: int | None
      - x_left, x_right: int | None
    """
    # 안전 추출
    rec_texts = getattr(ocr_result, 'rec_texts', None)
    if rec_texts is None and isinstance(ocr_result, dict):
        rec_texts = ocr_result.get('rec_texts')
    if rec_texts is None:
        print("❌ rec_texts를 찾을 수 없습니다.")
        return []

    rec_scores = getattr(ocr_result, 'rec_scores', None)
    if rec_scores is None and isinstance(ocr_result, dict):
        rec_scores = ocr_result.get('rec_scores')
    if rec_scores is None:
        print("❌ rec_scores를 찾을 수 없습니다.")
        return []

    rec_polys = getattr(ocr_result, 'rec_polys', None)
    if rec_polys is None and isinstance(ocr_result, dict):
        rec_polys = ocr_result.get('rec_polys')
    dt_polys = getattr(ocr_result, 'dt_polys', None)
    if dt_polys is None and isinstance(ocr_result, dict):
        dt_polys = ocr_result.get('dt_polys')

    def _center_y_from_poly(poly) -> Optional[int]:
        try:
            if poly is None:
                return None
            # numpy array 처리
            if np is not None and isinstance(poly, np.ndarray):
                arr = poly
                if arr.ndim == 1 and len(arr) == 8:
                    arr = arr.reshape(4, 2)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    ys = [float(y) for y in arr[:, 1]]
                else:
                    return None
            # 리스트 처리
            elif isinstance(poly, list):
                if len(poly) == 8 and all(isinstance(x, (int, float)) for x in poly):
                    ys = [float(poly[i + 1]) for i in range(0, 8, 2)]
                elif len(poly) > 0 and isinstance(poly[0], (list, tuple)) and len(poly[0]) >= 2:
                    ys = [float(p[1]) for p in poly]
                else:
                    return None
            else:
                return None
            if not ys:
                return None
            cy = sum(ys) / len(ys)
            return int(round(cy))
        except Exception:
            return None

    def _y_bounds_from_poly(poly) -> Tuple[Optional[int], Optional[int]]:
        """폴리곤에서 y_top(최소 Y), y_bottom(최대 Y)을 계산."""
        try:
            if poly is None:
                return None, None
            if np is not None and isinstance(poly, np.ndarray):
                arr = poly
                if arr.ndim == 1 and len(arr) == 8:
                    arr = arr.reshape(4, 2)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    ys = [float(y) for y in arr[:, 1]]
                else:
                    return None, None
            elif isinstance(poly, list):
                if len(poly) == 8 and all(isinstance(x, (int, float)) for x in poly):
                    ys = [float(poly[i + 1]) for i in range(0, 8, 2)]
                elif len(poly) > 0 and isinstance(poly[0], (list, tuple)) and len(poly[0]) >= 2:
                    ys = [float(p[1]) for p in poly]
                else:
                    return None, None
            else:
                return None, None
            if not ys:
                return None, None
            y_top_f = min(ys)
            y_bottom_f = max(ys)
            return int(round(y_top_f)), int(round(y_bottom_f))
        except Exception:
            return None, None

    def _x_left_from_poly(poly) -> Optional[int]:
        try:
            if poly is None:
                return None
            if np is not None and isinstance(poly, np.ndarray):
                arr = poly
                if arr.ndim == 1 and len(arr) == 8:
                    arr = arr.reshape(4, 2)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    xs = [float(x) for x in arr[:, 0]]
                else:
                    return None
            elif isinstance(poly, list):
                if len(poly) == 8 and all(isinstance(x, (int, float)) for x in poly):
                    xs = [float(poly[i]) for i in range(0, 8, 2)]
                elif len(poly) > 0 and isinstance(poly[0], (list, tuple)) and len(poly[0]) >= 2:
                    xs = [float(p[0]) for p in poly]
                else:
                    return None
            else:
                return None
            if not xs:
                return None
            xl = min(xs)
            return int(round(xl))
        except Exception:
            return None

    def _x_right_from_poly(poly) -> Optional[int]:
        try:
            if poly is None:
                return None
            if np is not None and isinstance(poly, np.ndarray):
                arr = poly
                if arr.ndim == 1 and len(arr) == 8:
                    arr = arr.reshape(4, 2)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    xs = [float(x) for x in arr[:, 0]]
                else:
                    return None
            elif isinstance(poly, list):
                if len(poly) == 8 and all(isinstance(x, (int, float)) for x in poly):
                    xs = [float(poly[i]) for i in range(0, 8, 2)]
                elif len(poly) > 0 and isinstance(poly[0], (list, tuple)) and len(poly[0]) >= 2:
                    xs = [float(p[0]) for p in poly]
                else:
                    return None
            else:
                return None
            if not xs:
                return None
            xr = max(xs)
            return int(round(xr))
        except Exception:
            return None

    # rec_texts와 rec_scores 길이가 같을 때만 처리
    if rec_scores and len(rec_texts) == len(rec_scores):
        result_list: List[Dict[str, object]] = []
        for i in range(len(rec_texts)):
            text = rec_texts[i]
            confidence = rec_scores[i]
            # 폴리곤 선택: rec_polys 우선, 없으면 dt_polys
            poly = None
            if isinstance(rec_polys, (list,)) and i < len(rec_polys):
                poly = rec_polys[i]
            elif isinstance(dt_polys, (list,)) and i < len(dt_polys):
                poly = dt_polys[i]

            y_center = _center_y_from_poly(poly)
            y_top, y_bottom = _y_bounds_from_poly(poly)
            x_left = _x_left_from_poly(poly)
            x_right = _x_right_from_poly(poly)
            raw_h: Optional[int] = None
            if y_top is not None and y_bottom is not None:
                raw_h = int(max(0, round(y_bottom - y_top)))

            result_list.append({
                "text": text,
                "confidence": float(confidence) if confidence is not None else None,
                "y_top": y_top,
                "y_bottom": y_bottom,
                "y_center": y_center,
                "raw_h": raw_h,
                "x_left": x_left,
                "x_right": x_right,
            })
        return result_list
    else:
        return []


def assign_line_indices_by_y(items: List[Dict], alpha: float = 0.7) -> List[Dict]:
    """y 파생값을 사용해 같은 라인끼리 묶고 line_index를 부여(제자리 수정).

    정책:
    - y_center 기준 정렬 후 위→아래 스윕하며 라인 형성
    - tau = median(raw_h) * alpha
    - 고정 밴드 [seed_center - tau, seed_center + tau] 안에 들어오면 같은 라인
    """
    if not items:
        return items

    def _to_int_or_none(v):
        try:
            return int(v) if v is not None else None
        except Exception:
            try:
                return int(round(float(v)))
            except Exception:
                return None

    def _ensure_bounds(it: Dict) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        y_top = _to_int_or_none(it.get("y_top"))
        y_bottom = _to_int_or_none(it.get("y_bottom"))
        y_center = _to_int_or_none(it.get("y_center"))
        raw_h = _to_int_or_none(it.get("raw_h"))
        if (y_top is None or y_bottom is None) and (y_center is not None and (raw_h is not None and raw_h > 0)):
            half = int(round(raw_h / 2))
            if y_top is None:
                y_top = y_center - half
            if y_bottom is None:
                y_bottom = y_center + half
        return y_top, y_bottom, y_center, raw_h

    raw_h_vals: List[int] = []
    for it in items:
        v = _to_int_or_none(it.get("raw_h"))
        if v is not None and v > 0:
            raw_h_vals.append(v)
    if raw_h_vals:
        s = sorted(raw_h_vals)
        n = len(s)
        median_h = s[n // 2] if n % 2 == 1 else int(round((s[n // 2 - 1] + s[n // 2]) / 2))
    else:
        median_h = 16
    tau = max(1, int(round(median_h * alpha)))

    def _sort_key(idx_item: Tuple[int, Dict]):
        _, it = idx_item
        y_top, y_bottom, y_center, _ = _ensure_bounds(it)
        if y_center is not None:
            return (y_center, y_top if y_top is not None else y_center)
        if y_top is not None:
            return (y_top, y_top)
        if y_bottom is not None:
            return (y_bottom, y_bottom)
        return (0, 0)

    indexed_items = list(enumerate(items))
    sorted_items = sorted(indexed_items, key=_sort_key)

    current_line = -1
    cluster_top = None
    cluster_bottom = None
    cluster_center = None
    band_top = None
    band_bottom = None

    for idx, it in sorted_items:
        y_top, y_bottom, y_center, _ = _ensure_bounds(it)
        same_line = False
        if current_line >= 0:
            cand_center = y_center
            if cand_center is None and (y_top is not None and y_bottom is not None):
                cand_center = int(round((y_top + y_bottom) / 2))
            if cand_center is not None and (band_top is not None and band_bottom is not None):
                if band_top <= cand_center <= band_bottom:
                    same_line = True
        if not same_line:
            current_line += 1
            if y_top is not None and y_bottom is not None:
                cluster_top = y_top
                cluster_bottom = y_bottom
                cluster_center = int(round((y_top + y_bottom) / 2))
            else:
                cluster_center = y_center if y_center is not None else 0
                cluster_top = cluster_center
                cluster_bottom = cluster_center
            seed_center = cluster_center if cluster_center is not None else (y_center if y_center is not None else 0)
            band_top = seed_center - tau
            band_bottom = seed_center + tau
        else:
            if y_top is not None:
                cluster_top = y_top if cluster_top is None else min(cluster_top, y_top)
            if y_bottom is not None:
                cluster_bottom = y_bottom if cluster_bottom is None else max(cluster_bottom, y_bottom)
            if cluster_top is not None and cluster_bottom is not None:
                cluster_center = int(round((cluster_top + cluster_bottom) / 2))
        it["line_index"] = current_line

    return items


def group_tokens_by_line(items: List[Dict], order: str = "x_left", alpha: float = 0.7) -> List[List[Dict]]:
    """line_index가 부여된 토큰을 라인 단위로 묶어 2차원 배열로 반환.

    - 라인 순서: line_index 오름차순
    - 라인 내 정렬: 기본 x_left 오름차순, 불가 시 입력 순서 유지
    - line_index가 없으면 내부적으로 assign_line_indices_by_y 실행
    """
    if not items:
        return []
    if any("line_index" not in it for it in items):
        assign_line_indices_by_y(items, alpha=alpha)

    groups: Dict[int, List[Tuple[int, Dict]]] = {}
    for src_idx, it in enumerate(items):
        li = it.get("line_index")
        if not isinstance(li, int):
            continue
        groups.setdefault(li, []).append((src_idx, it))

    sorted_line_indices = sorted(groups.keys())

    def sort_line_entries(entries: List[Tuple[int, Dict]]) -> List[Dict]:
        if order == "x_left":
            x_vals = [e[1].get("x_left") for e in entries]
            all_numeric = all(isinstance(x, (int, float)) for x in x_vals)
            none_exists = any(x is None for x in x_vals)
            if all_numeric and not none_exists:
                entries_sorted = sorted(entries, key=lambda e: (int(e[1]["x_left"]), e[0]))
            else:
                entries_sorted = sorted(entries, key=lambda e: e[0])
        else:
            entries_sorted = sorted(entries, key=lambda e: e[0])
        return [tok for _, tok in entries_sorted]

    grouped: List[List[Dict]] = []
    for li in sorted_line_indices:
        entries = groups[li]
        grouped.append(sort_line_entries(entries))

    return grouped


def extract_and_group_lines(
    ocr_result,
    order: str = "x_left",
    alpha: float = 0.7,
    isDebug: bool = True,
    unit_lexicon: Optional[Dict[str, object]] = None,
    min_confidence: float = 0.5,
) -> List[List[Dict]]:
    """통합 실행: 4.1~4.7 단계 수행.

    순서:
      4.1 토큰 추출 → 신뢰도 필터링 → 4.2 라인 인덱스 → 4.3 라인 그룹핑 →
      4.4 선두 이름 병합(괄호형 등) → 4.5 값/단위 분리 →
      4.6 값 경고 플래그 주석 → 4.7 상태 토큰 제거

    Args:
        min_confidence: 최소 신뢰도 임계값 (기본값: 0.5)
                       이 값 미만인 토큰은 노이즈로 간주하여 제외합니다.

    기하 정보(x_left/x_right, y_top/y_bottom/center, line_index)는 항상 유지되어
    후속 단계(예: 기하 기반 Filling)가 활용할 수 있습니다.
    """
    def _dbg_print(title: str, data):
        try:
            if isinstance(data, list):
                count = len(data)
                preview = data if count <= 50 else data[:50]
                print(f"[DEBUG] {title}: count={count}")
                print(json.dumps(preview, indent=2, ensure_ascii=False))
                if count > 50:
                    print(f"[DEBUG] {title}: ... truncated {count-50} more items ...")
            else:
                print(f"[DEBUG] {title}:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print(f"[DEBUG] {title}: (non-serializable) {type(data)}")

    items = extract_tokens_with_geometry(ocr_result)
    # if isDebug:
    #     _dbg_print("tokens_with_geometry", items)
    if not items:
        return []

    # 신뢰도 기반 필터링: min_confidence 미만인 토큰 제외
    if min_confidence > 0:
        before_count = len(items)
        filtered_items = []
        dropped_items = []
        for item in items:
            conf = item.get("confidence")
            if conf is not None and conf < min_confidence:
                dropped_items.append(item)
            else:
                filtered_items.append(item)
        items = filtered_items
        if isDebug and dropped_items:
            print(f"[DEBUG] confidence_filter: dropped {len(dropped_items)} tokens (min_confidence={min_confidence})")
            for d in dropped_items[:5]:  # 최대 5개만 표시
                print(f"  - '{d.get('text', '')}' (conf={d.get('confidence', 0):.2f})")
            if len(dropped_items) > 5:
                print(f"  ... and {len(dropped_items) - 5} more")

    if not items:
        return []

    items = assign_line_indices_by_y(items, alpha=alpha)
    # if isDebug:
    #     _dbg_print("tokens_with_line_index", items)

    grouped = group_tokens_by_line(items, order=order, alpha=alpha)
    # if isDebug:
    #     _dbg_print("grouped_lines_before_split", grouped)

    # 4.4 라인 선두(Name 열) 분리 토큰 병합
    # - 괄호형: 예) POTASSIUM | (K+) → POTASSIUM(K+)
    # - 병합은 라인 선두(Name 영역)에서만 시도하며, 숫자/범위/단위/헤더 키워드를 만나면 중단
    # - 지오메트리(x-gap) 보수 임계 하에서만 수행
    paren_re = re.compile(r"^\([^)]{1,12}\)$")

    def _int_or_none(v):
        try:
            return int(v) if v is not None else None
        except Exception:
            try:
                return int(round(float(v)))
            except Exception:
                return None

    def _median_gap_x(tokens: List[Dict]) -> int:
        # x_left 기준 정렬 후 인접 간격의 중앙값
        xs = []
        for t in tokens:
            xl = _int_or_none(t.get("x_left"))
            xr = _int_or_none(t.get("x_right"))
            if xl is not None and xr is not None and xr >= xl:
                xs.append((xl, xr))
        if len(xs) < 2:
            return 0
        xs.sort(key=lambda p: p[0])
        gaps: List[int] = []
        for i in range(len(xs) - 1):
            g = xs[i + 1][0] - xs[i][1]
            if g >= 0:
                gaps.append(int(g))
        if not gaps:
            return 0
        gaps.sort()
        return gaps[len(gaps)//2]

    def _is_numeric_or_range_or_unit(text: str) -> bool:
        s = (text or "").strip().replace("·", ".").replace(",", ".")
        if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?(?:[HhLlNn])?", s):
            return True
        if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?\s*[-–~]\s*[+-]?\d+(?:[.,]\d+)?", s):
            return True
        unit_pat = re.compile(
            r"^(?:%|‰|g/dl|mg/dl|u/l|iu/l|mmol/l|meq/l|fL|fl|pg|ng/ml|k/µl|k/μl|k/u?l|m/µl|m/μl|m/u?l|10\^?\d+/(?:l|ul|µl|μl))$",
            re.IGNORECASE,
        )
        if unit_pat.match(s) or ("%" in s and len(s) <= 4):
            return True
        return False

    def _merge_name_fragments(lines_2d: List[List[Dict]]) -> List[List[Dict]]:
        merged_lines: List[List[Dict]] = []
        for line in lines_2d:
            if not line or len(line) < 2:
                merged_lines.append(line)
                continue
            # 선두 영역에서만 후보 탐색
            med_gap = _median_gap_x(line)
            gap_thresh = max(14, int(round((med_gap or 0) * 1.6)))
            # 인접 두 토큰만 보수적으로 병합 (괄호형 전용)
            i = 0
            changed = False
            new_line = list(line)
            while i < len(new_line) - 1:
                t0 = new_line[i]
                t1 = new_line[i + 1]
                s0 = str(t0.get("text", "") or "").strip()
                s1 = str(t1.get("text", "") or "").strip()
                # 경계 신호를 만나면 선두 병합 탐색 종료
                if i == 0 and _is_numeric_or_range_or_unit(s0):
                    break
                # 괄호형만 대상: (K+), (Na+), (Magnesium) ... 길이<=12
                if paren_re.match(s1) and not _is_numeric_or_range_or_unit(s0):
                    xl0 = _int_or_none(t0.get("x_left")); xr0 = _int_or_none(t0.get("x_right"))
                    xl1 = _int_or_none(t1.get("x_left")); xr1 = _int_or_none(t1.get("x_right"))
                    if None not in (xl0, xr0, xl1, xr1) and xr0 is not None and xl1 is not None:
                        gap = xl1 - xr0
                        if gap <= gap_thresh:
                            # 병합 텍스트: 괄호 앞 공백 제거 규칙 적용
                            merged_text = f"{s0}{s1}"
                            merged_tok = dict(t0)
                            merged_tok["text"] = merged_text
                            merged_tok["_origin"] = "name_merge_4_4"
                            # 기하는 min/max로 확장
                            # 안전 정수화 후 좌우 경계 확장
                            l0 = int(xl0) if xl0 is not None else 0
                            r0v = int(xr0) if xr0 is not None else l0
                            l1 = int(xl1) if xl1 is not None else 0
                            r1v = int(xr1) if xr1 is not None else l1
                            merged_tok["x_left"] = min(l0, l1)
                            merged_tok["x_right"] = max(r0v, r1v)
                            yts = [v for v in (t0.get("y_top"), t1.get("y_top")) if isinstance(v, (int, float))]
                            ybs = [v for v in (t0.get("y_bottom"), t1.get("y_bottom")) if isinstance(v, (int, float))]
                            if yts:
                                merged_tok["y_top"] = int(min(yts))
                            if ybs:
                                merged_tok["y_bottom"] = int(max(ybs))
                            # 교체
                            new_line = new_line[:i] + [merged_tok] + new_line[i+2:]
                            changed = True
                            # 선두만 처리하고 종료(보수 운영)
                            break
                # 다음으로 진행, 단 선두 병합만 허용하므로 i 증가 시도 후 즉시 종료
                break
            merged_lines.append(new_line)
            if isDebug and changed:
                try:
                    before = " | ".join([str(x.get("text", "")) for x in line])
                    after = " | ".join([str(x.get("text", "")) for x in new_line])
                    print(f"[DEBUG] 4.4 name_merge: {before}  →  {after}")
                except Exception:
                    pass
        return merged_lines

    grouped = _merge_name_fragments(grouped)
    # if isDebug:
    #     _dbg_print("grouped_lines_after_4_4_name_merge", grouped)

    # 4.4-보강: 첫 번째 컬럼 텍스트에서 괄호 앞 공백 제거 (예: 'SODIUM (Na+)' → 'SODIUM(Na+)')
    try:
        fixed = 0
        for line in grouped:
            if not line:
                continue
            first = line[0]
            if isinstance(first, dict):
                txt = str(first.get("text", "") or "")
                new_txt = re.sub(r"\s+\(", "(", txt)
                if new_txt != txt:
                    first["text"] = new_txt
                    first.setdefault("_first_col_norm", []).append("no_space_before_paren")
                    fixed += 1
        if isDebug and fixed:
            print(f"[DEBUG] 4.4 first_col_paren_space_removed: {fixed} lines")
    except Exception:
        pass

    # 4.5 값/단위 분리
    # 공백 기반 분리 + 공백 없는 붙어있는 형태도 분리(예: <5ug/mL, 1.9mg/dL, 7.34%)
    # - 비교기( <, >, <=, >=, ≤, ≥, ~, ≈ )를 숫자 앞에서 허용
    _comp = r"(?:[<>]=?|[≤≥≈~])?"  # 선택적 비교기
    _num  = r"[-+]?(?:\d+(?:[.,]\d+)?|\.\d+)(?:\s*(?:x|×)\s*10\s*\^?\s*[-+]?\d+)?"  # 숫자 + (선택)지수형
    _unit = r"[A-Za-zµμ%‰/][\w%‰/µμ]*"  # 단위 토큰 시작은 문자/기호, 이어서 단위 구성 가능 문자

    # 공백 분리형: (<) 5  +  단위
    full_pat  = re.compile(rf"^\s*({_comp})\s*({_num})\s+(.+?)\s*$")
    # 붙어있는형: (<)5 + 단위
    glued_pat = re.compile(rf"^\s*({_comp})\s*({_num})({_unit})\s*$")
    range_seps = ("-", "–", "~")

    def _to_int_or_none(v):
        try:
            return int(v) if v is not None else None
        except Exception:
            try:
                return int(round(float(v)))
            except Exception:
                return None

    def _split_line_tokens_preserve_fields(line_tokens: List[Dict]) -> List[Dict]:
        out: List[Dict] = []
        for tok in line_tokens:
            text = str(tok.get("text", "") or "")
            conf = tok.get("confidence", None)
            m = None
            value_str = None
            unit_str = None
            # 먼저 공백 기반 분리 시도 (비교기 포함)
            m = full_pat.match(text)
            if m:
                comp = (m.group(1) or "").strip()
                num  = (m.group(2) or "").strip()
                value_str = f"{comp}{num}" if comp else num
                unit_str = m.group(3).strip()
            else:
                # 공백 없는 붙은 형태도 시도: (비교기 포함) 숫자 + 단위토큰
                mg = glued_pat.match(text)
                if mg:
                    comp = (mg.group(1) or "").strip()
                    num  = (mg.group(2) or "").strip()
                    unit = (mg.group(3) or "").strip()
                    value_str = f"{comp}{num}" if comp else num
                    unit_str = unit
            if value_str is None or unit_str is None:
                out.append(tok)
                continue
            # H/L/N 접미(경고 플래그)로 오인 분리 방지: 단일 문자 H/L/N은 단위로 보지 않음
            if re.fullmatch(r"[HhLlNn]", unit_str):
                out.append(tok)
                continue
            # 범위/이상치 구분자 포함 시는 단위로 보지 않음
            if any(sep in unit_str for sep in range_seps):
                out.append(tok)
                continue
            # 단위 길이 보수 제한
            if len(unit_str) == 0 or len(unit_str) > 12:
                out.append(tok)
                continue
            left_tok = dict(tok)
            right_tok = dict(tok)
            left_tok["text"] = value_str
            left_tok["confidence"] = conf
            left_tok["_origin"] = "split_value"
            right_tok["text"] = unit_str
            right_tok["confidence"] = conf
            right_tok["_origin"] = "split_unit_candidate"
            xl = _to_int_or_none(tok.get("x_left"))
            xr = _to_int_or_none(tok.get("x_right"))
            if xl is not None and xr is not None:
                if xr < xl:
                    xl, xr = xr, xl
                mid = int(round((xl + xr) / 2))
                if mid < xl:
                    mid = xl
                if mid > xr:
                    mid = xr
                left_tok["x_left"], left_tok["x_right"] = xl, mid
                right_tok["x_left"], right_tok["x_right"] = mid, xr
            out.append(left_tok)
            out.append(right_tok)
        return out

    grouped_after_split: List[List[Dict]] = []
    for line in grouped:
        grouped_after_split.append(_split_line_tokens_preserve_fields(line))
    grouped = grouped_after_split
    # if isDebug:
    #     _dbg_print("grouped_lines_after_split", grouped)

    # 4.5 분리 직후 1차 단위 처리(표시만)
    # - 중복 정규화를 피하기 위해 이 단계에서는 단위를 '표시/주석'만 하고 텍스트를 변경하지 않습니다.
    # - 최종 canonical 확정은 Step 11에서 한 번만 수행합니다.
    if unit_lexicon:
        try:
            marked = 0
            for line in grouped:
                for tok in line:
                    if tok.get("_origin") == "split_unit_candidate":
                        # 원문 단위를 보존 표기만 (중복 방지용)
                        txt = str(tok.get("text", "") or "")
                        if txt and "raw_unit" not in tok:
                            tok["raw_unit"] = txt
                            marked += 1
            if isDebug and marked:
                print(f"[DEBUG] unit_first_pass_marked: {marked} tokens (no canonicalization at Step 4.x)")
        except Exception as _e:
            if isDebug:
                print(f"[DEBUG] unit_first_pass_mark_error: {_e}")

    # 4.6 값 경고 플래그 주석(경량) — 공백 없는 접미 H/L/N만
    # - 원문 text는 변경하지 않음
    # - value_num(숫자 부분), value_flag(H|L|N), value_norm_stage(first_pass)를 주석으로 추가
    # - 단위 후보(_origin == split_unit_candidate)는 제외
    try:
        value_flag_pat = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)([HLN])\s*$", re.IGNORECASE)
        ann_count = 0
        for line in grouped:
            for tok in line:
                if tok.get("_origin") == "split_unit_candidate":
                    continue
                if "value_flag" in tok and tok.get("value_flag"):
                    continue
                s = str(tok.get("text", "") or "")
                m = value_flag_pat.match(s)
                if not m:
                    continue
                num_str = m.group(1)
                flag_str = m.group(2).upper()
                tok.setdefault("raw_value", s)
                tok["value_num"] = num_str
                tok["value_flag"] = flag_str
                tok["value_norm_stage"] = "first_pass"
                ann_count += 1
        if isDebug and ann_count:
            print(f"[DEBUG] value_flag_first_pass_annotated: {ann_count} tokens")
    except Exception as _e:
        if isDebug:
            print(f"[DEBUG] value_flag_first_pass_error: {_e}")

    # 4.7 상태 토큰 제거(NORMAL/LOW/HIGH)
    # - 데이터 셀로 간주되지 않는 라벨성 토큰을 조용히 제거하여 바디 라인을 정제
    try:
        statuses = {"normal", "low", "high"}
        removed = 0
        def _is_status(tok: Dict) -> bool:
            try:
                s = str(tok.get("text", "") or "").strip().lower()
            except Exception:
                return False
            return s in statuses
        new_grouped: List[List[Dict]] = []
        for line in grouped:
            kept = [tok for tok in line if not _is_status(tok)]
            removed += (len(line) - len(kept))
            new_grouped.append(kept)
        grouped = new_grouped
        if isDebug and removed:
            print(f"[DEBUG] status_tokens_removed_4_7: {removed}")
    except Exception as _e:
        if isDebug:
            print(f"[DEBUG] status_tokens_remove_error_4_7: {_e}")

    return grouped


# -----------------------
# 클래스 기반 API
# -----------------------

@dataclass
class Settings:
    """라인 전처리 설정값.

    - order: 라인 내 정렬 기준
    - alpha: 라인 병합 민감도 (tau = median(raw_h) * alpha)
    - debug: 디버그 로그 출력 여부
    - min_confidence: 최소 신뢰도 임계값 (이 값 미만인 토큰은 제외)
    """
    order: str = "x_left"
    alpha: float = 0.7
    debug: bool = True
    # 최소 신뢰도 임계값 (기본값: 0.5, 0.5 미만인 토큰은 노이즈로 간주하여 제외)
    min_confidence: float = 0.5
    # unit 1차 정규화 사용 여부(lexicon이 주입되었을 때만 동작). 단일 정규화 포인트로 변경하여 기본 False
    normalize_units_first_pass: bool = False


class LinePreprocessor:
    """라인 전처리 클래스 버전.

    함수형 API와 동일한 동작을 제공하며, 의존성 주입과 설정 공유를 용이하게 합니다.
    """

    def __init__(self, settings: Optional[Settings] = None, unit_lexicon: Optional[Dict[str, object]] = None):
        self.settings = settings or Settings()
        self.unit_lexicon = unit_lexicon

    # 공개 메서드: 함수형 API를 thin wrapper로 호출
    def extract_tokens_with_geometry(self, ocr_result) -> List[Dict[str, object]]:
        return extract_tokens_with_geometry(ocr_result)

    def assign_line_indices_by_y(self, items: List[Dict]) -> List[Dict]:
        return assign_line_indices_by_y(items, alpha=self.settings.alpha)

    def group_tokens_by_line(self, items: List[Dict]) -> List[List[Dict]]:
        return group_tokens_by_line(items, order=self.settings.order, alpha=self.settings.alpha)

    def extract_and_group_lines(self, ocr_result) -> List[List[Dict]]:
        return extract_and_group_lines(
            ocr_result,
            order=self.settings.order,
            alpha=self.settings.alpha,
            isDebug=self.settings.debug,
            unit_lexicon=self.unit_lexicon if self.settings.normalize_units_first_pass else None,
            min_confidence=self.settings.min_confidence,
        )

