import io
from typing import List, Dict, Any, Tuple, Callable, Sequence, Optional
import fitz
import tempfile
from PIL import Image, ImageFilter, ImageOps
import numpy as np
from pytesseract import image_to_data, Output
import cv2
import os

# ---------- 공통 보조 ----------
def _pil_to_cv(img: Image.Image) -> np.ndarray:
    arr = np.array(img)
    if arr.ndim == 2:
        return arr
    if arr.shape[2] == 4:
        # RGBA -> RGB
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB) if cv2 is not None else arr[:, :, :3]
    # RGB -> BGR
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if cv2 is not None else arr[:, :, ::-1]

def _cv_to_pil(arr: np.ndarray) -> Image.Image:
    if arr.ndim == 2:
        return Image.fromarray(arr)
    # BGR -> RGB
    if cv2 is not None:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    else:
        arr = arr[:, :, ::-1]
    return Image.fromarray(arr)

def _order_quad(pts: np.ndarray) -> np.ndarray:
    # pts: (4,2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)

def pdf_to_images(pdf_path: str, resolution_scale: float = 1.5) -> List[bytes]:
    """
    PDF 파일 경로를 받아 각 페이지를 PNG 바이트로 변환해 리스트로 반환
    """
    png_list: List[bytes] = []
    doc = None
    try:
        doc = fitz.open(pdf_path)
        mat = fitz.Matrix(resolution_scale, resolution_scale)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_list.append(pix.tobytes("png"))
    finally:
        try:
            if doc is not None:
                doc.close()
        except Exception:
            pass
    return png_list

# ---------- 로드+EXIF 회전 교정 ----------
def open_with_exif(img_bytes: bytes):
    """
    1) 로드 + EXIF 회전 교정: 카메라 회전 정보가 있으면 실제 픽셀을 회전
    """
    img = Image.open(io.BytesIO(img_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img

# ---------- 투명 채널 플래튼 ----------
def flatten_transparency(img: Image.Image) -> Image.Image:
    """
    2) 투명 채널 플래튼: RGBA/LA → 흰 배경 위에 합성 (기호/점 주변 헤일로 방지)
    """
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        return Image.composite(img.convert("RGB"), bg, alpha)
    return img

# ---------- 여백 기반 자동 크롭 ----------
def auto_crop_with_margin(img: Image.Image, margin: int = 20) -> Image.Image:
    """
    3) 자동 크롭: 흰 배경을 기준으로 내용물 bbox를 찾고 margin만큼 여유
    """
    gray = img.convert("L")
    inv = ImageOps.invert(gray)  # 흰색 배경 → 0, 잉크 → 양수
    bbox = inv.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - margin)
    y0 = max(0, y0 - margin)
    x1 = min(img.width,  x1 + margin)
    y1 = min(img.height, y1 + margin)
    return img.crop((x0, y0, x1, y1))

# ---------- 문서 외곽 사변형 경계 탐지 ----------
def detect_document_quad(img: Image.Image, min_area_ratio: float = 0.2, debug: bool = False) -> Optional[List[Tuple[int, int]]]:
    """
    new detect_document_quad(문서 외곽 사변형 경계 탐지)
    - 성공 시 좌상, 우상, 우하, 좌하 4점 반환, 실패 시 None
    """
    if cv2 is None:
        if debug: print("[detect_document_quad] OpenCV 미설치 - 건너뜀")
        return None
    im = _pil_to_cv(img)
    h, w = im.shape[:2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((5,5), np.uint8), iterations=1)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    img_area = w*h
    for c in cnts[:8]:
        area = cv2.contourArea(c)
        if area < img_area * min_area_ratio:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            quad = approx.reshape(-1, 2).astype(np.float32)
            quad = _order_quad(quad)
            if debug: print(f"[detect_document_quad] 사변형 발견 - area ratio={area/img_area:.2f}")
            return [(int(x), int(y)) for x, y in quad]
    if debug: print("[detect_document_quad] 사변형 미발견")
    return None

# ---------- 사변형 → 직사각 투시 보정 ----------
def perspective_unwarp(img: Image.Image, quad: Optional[List[Tuple[int,int]]] = None, keep_aspect: bool = True, padding: int = 0, debug: bool = False) -> Image.Image:
    """
    new perspective_unwarp(사변형 → 직사각 투시 보정)
    - quad가 없으면 자동 검출을 시도
    """
    if cv2 is None:
        if debug: print("[perspective_unwarp] OpenCV 미설치 - 원본 반환")
        return img
    if quad is None:
        quad = detect_document_quad(img, debug=debug)
    if quad is None:
        if debug: print("[perspective_unwarp] 경계 미검출 - 원본 반환")
        return img

    im = _pil_to_cv(img)
    h, w = im.shape[:2]
    src = np.array(quad, dtype=np.float32)

    # 목표 크기 추정
    tl, tr, br, bl = src
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    dst_w = int(max(widthA, widthB))
    dst_h = int(max(heightA, heightB))
    if keep_aspect and dst_w > 0 and dst_h > 0:
        aspect = dst_w / (dst_h + 1e-6)
        # 의료 양식(세로형)이 흔해 약간의 정규화
        if aspect < 0.6:  # 너무 세로 길면 살짝 보정
            dst_w = int(dst_h * 0.7)

    dst = np.array([[0,0],[dst_w-1,0],[dst_w-1,dst_h-1],[0,dst_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(im, M, (dst_w, dst_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    if padding > 0:
        warped = cv2.copyMakeBorder(warped, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=(255,255,255))
    if debug: print(f"[perspective_unwarp] 완료 → {dst_w}x{dst_h}")
    return _cv_to_pil(warped)

# ---------- OSD + 텍스트 라인 기반 미세 기울기 보정 ----------
def deskew_textlines(
    img: Image.Image,
    max_angle: float = 12.0,
    refine: bool = True,
    refine_range: float = 1.0,   # ± 탐색 범위(도)
    refine_step: float = 0.05,   # 탐색 간격(도)
    pad: int = 12,               # 회전 전 여백(클리핑 방지)
    debug: bool = True,
) -> Image.Image:
    """
    Tesseract OSD로 '초기 각도' 추정 후, 작은 범위에서
    행 프로젝션 점수로 정밀 탐색해 교정. OSD 실패 시 Hough 변환 사용.
    """
    if cv2 is None:
        if debug: print("[deskew_textlines] OpenCV 미설치 - 원본 반환")
        return img

    # 1) Tesseract OSD로 초기 각도 추정
    osd_angle = 0.0
    try:
        from pytesseract import image_to_osd, Output
        osd = image_to_osd(img, output_type=Output.DICT, config="--psm 0")
        # Tesseract는 시계 방향을 양수로 보고, 우리는 반시계 방향을 양수로 사용하므로 부호 반전
        angle_candidate = -float(osd.get('rotate', 0))
        if abs(angle_candidate) <= max_angle:
            osd_angle = angle_candidate
            if debug: print(f"[deskew_textlines] Tesseract OSD angle: {osd_angle:.2f}°")
    except Exception as e:
        if debug: print(f"[deskew_textlines] Tesseract OSD 실패: {e}, Hough 변환으로 대체")
        osd_angle = 0.0 # 실패 시 0으로 초기화

    im0 = _pil_to_cv(img)
    if pad > 0:
        im = cv2.copyMakeBorder(im0, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    else:
        im = im0

    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    h, w = gray.shape[:2]

    # 2) OSD 각도가 0에 가까우면 Hough 변환으로 보조/대체
    coarse = osd_angle
    if abs(osd_angle) < 0.1:
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thr = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        bw_inv = 255 - thr

        kx = max(21, w // 30)
        hker = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, 1))
        horiz = cv2.morphologyEx(bw_inv, cv2.MORPH_OPEN, hker)
        edges = cv2.max(cv2.Canny(bw_inv, 50, 150), cv2.Canny(horiz, 50, 150))

        min_len = max(60, int(w * 0.35))
        linesP = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=max(50, int(0.0025 * w)),
            minLineLength=min_len,
            maxLineGap=30
        )
        angles, weights = [], []
        if linesP is not None:
            for x1, y1, x2, y2 in linesP[:, 0]:
                ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if -max_angle <= ang <= max_angle:
                    L = float(np.hypot(x2 - x1, y2 - y1))
                    angles.append(ang); weights.append(L)
        
        hough_angle = float(np.average(angles, weights=weights)) if angles else 0.0
        if debug: print(f"[deskew_textlines] Hough angle: {hough_angle:.2f}°")
        # OSD 결과가 거의 없을 때만 Hough 결과 사용
        if abs(osd_angle) < 0.1 and abs(hough_angle) > abs(osd_angle):
             coarse = hough_angle

    final_angle = coarse

    # 3) 정밀 탐색(±refine_range, step=refine_step) - 행 프로젝션 점수 최대화
    if refine and abs(coarse) < max_angle : # coarse가 max_angle을 넘으면 refine 건너뜀
        # 이진화 이미지가 필요하므로 여기서 다시 계산
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thr = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        bw_inv = 255 - thr

        scale = 1000.0 / max(h, w)
        small = cv2.resize(bw_inv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else bw_inv
        sh, sw = small.shape[:2]

        def score(a_deg: float) -> float:
            M = cv2.getRotationMatrix2D((sw / 2, sh / 2), a_deg, 1.0)
            r = cv2.warpAffine(small, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            proj = r.mean(axis=1)
            d = np.diff(proj)
            return float(proj.var() + 0.5 * (d * d).mean())

        best_s, best_a = -1e9, coarse
        for a in np.arange(coarse - refine_range, coarse + refine_range + 1e-9, refine_step):
            s = score(a)
            if s > best_s:
                best_s, best_a = s, a
        final_angle = best_a

    if debug:
        print(f"[deskew_textlines] coarse={coarse:.2f}°, final={final_angle:.2f}°")

    if abs(final_angle) < 0.05:
        return img

    M = cv2.getRotationMatrix2D((w / 2, h / 2), final_angle, 1.0)
    rotated = cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    if pad > 0 and rotated.shape[0] > 2 * pad and rotated.shape[1] > 2 * pad:
        rotated = rotated[pad:-pad, pad:-pad]
    return _cv_to_pil(rotated)

# ---------- 페이지 말림/곡면 보정·필요 시만 ----------
def conditional_dewarp(
    img: Image.Image,
    strength: float = 0.6,
    min_lines: int = 10,
    min_amplitude_px: float = 2.0,   # 곡률 진폭이 이 미만이면 스킵
    r2_min: float = 0.85,            # 2차 다항 적합 품질 하한
    r2_gain_min: float = 0.03,       # 선형→2차로의 개선폭 하한
    max_shift_px: float = 6.0,       # 컬럼별 최대 세로 이동 클램프
    debug: bool = True
) -> Image.Image:
    """
    페이지 말림/곡면 보정(필요 시만)
    - 수평 라인 샘플 → x-좌표에 대한 베이스라인을 2차 다항으로 근사
    - '곡률이 충분히 클 때'에만 적용. 반듯한 문서는 스킵.
    """
    if cv2 is None:
        if debug: print("[conditional_dewarp] OpenCV 미설치 - 원본 반환")
        return img

    im = _pil_to_cv(img)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 35, 15)

    lines = cv2.HoughLinesP(
        bw, 1, np.pi/180, threshold=100,
        minLineLength=max(40, gray.shape[1]//10),
        maxLineGap=10
    )
    if lines is None:
        if debug: print("[conditional_dewarp] 라인 미검출 - 스킵")
        return img

    pts_x, pts_y = [], []
    for x1, y1, x2, y2 in lines[:, 0]:
        if abs(y2 - y1) <= 2:  # 더 엄격한 수평 판정
            pts_x.append(0.5*(x1+x2))
            pts_y.append(0.5*(y1+y2))

    if len(pts_x) < min_lines:
        if debug: print(f"[conditional_dewarp] 유효 수평 라인 부족({len(pts_x)}<{min_lines}) - 스킵")
        return img

    x = np.asarray(pts_x, dtype=np.float32)
    y = np.asarray(pts_y, dtype=np.float32)

    # 선형/2차 모두 적합 후 품질 비교
    p1 = np.poly1d(np.polyfit(x, y, deg=1))
    p2 = np.poly1d(np.polyfit(x, y, deg=2))
    yhat1 = p1(x)
    yhat2 = p2(x)
    ss_tot = float(((y - y.mean())**2).sum()) + 1e-6
    r2_lin = 1.0 - float(((y - yhat1)**2).sum())/ss_tot
    r2_quad = 1.0 - float(((y - yhat2)**2).sum())/ss_tot
    r2_gain = r2_quad - r2_lin

    h, w = gray.shape[:2]
    xs = np.arange(w, dtype=np.float32)
    curve = p2(xs).astype(np.float32)
    amplitude = float(np.percentile(curve, 95) - np.percentile(curve, 5))

    if debug:
        print(f"[conditional_dewarp] r2_lin={r2_lin:.3f}, r2_quad={r2_quad:.3f}, gain={r2_gain:.3f}, amp={amplitude:.2f}px")

    # 안전 게이트: 곡률·적합 품질이 충분할 때만 적용
    if (amplitude < min_amplitude_px) or (r2_quad < r2_min) or (r2_gain < r2_gain_min):
        if debug: print("[conditional_dewarp] 곡률/적합 품질 부족 - 스킵")
        return img

    # 강도 자동 조절 + 이동량 클램프
    strength_eff = min(strength, max_shift_px / (0.5*amplitude + 1e-6))
    shift = (curve - curve.mean()) * strength_eff
    shift = np.clip(shift, -max_shift_px, max_shift_px).astype(np.float32)

    map_x = np.tile(xs, (h, 1)).astype(np.float32)
    ys = np.arange(h, dtype=np.float32)
    map_y = (np.tile(ys[:, None], (1, w)) - shift[None, :]).astype(np.float32)
    map_y = np.clip(map_y, 0, h - 1)

    dewarped = cv2.remap(im, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    if debug: print("[conditional_dewarp] 디워프 적용 (안전 게이트 통과)")
    return _cv_to_pil(dewarped)

# ---------- 최소 해상도 확보 업스케일 ----------
def upscale_min_resolution(img: Image.Image, min_long_edge: int = 1920) -> Image.Image:
    """
    4) 해상도 표준화(업스케일만): 소수점/기호 선명도를 위해 최소 해상도 확보, 과대 크기는 축소하지 않음
    """
    w, h = img.size
    long_edge = max(w, h)
    if long_edge < min_long_edge:
        scale = min_long_edge / float(long_edge)
        img = img.resize((int(round(w * scale)), int(round(h * scale))), Image.LANCZOS)
    return img

# ---------- 배경 평탄화·그라디언트/그림자 제거 ----------
def illumination_flatten(img: Image.Image, blur_ratio: float = 0.03, debug: bool = False) -> Image.Image:
    """
    new illumination_flatten(배경 평탄화·그림자 제거)
    - 큰 가우시안 블러로 배경을 추정 후 L(밝기) 채널에서 평탄화
    """
    if cv2 is None:
        if debug: print("[illumination_flatten] OpenCV 미설치 - 원본 반환")
        return img
    im = _pil_to_cv(img)
    if im.ndim == 3:
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
        k = max(3, int(round(max(im.shape[:2]) * blur_ratio)) | 1)
        bg = cv2.GaussianBlur(L, (k, k), 0)
        flat = cv2.normalize(cv2.subtract(L, bg) + 128, None, 0, 255, cv2.NORM_MINMAX)
        lab = cv2.merge([flat, A, B])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        k = max(3, int(round(max(im.shape[:2]) * blur_ratio)) | 1)
        bg = cv2.GaussianBlur(im, (k, k), 0)
        out = cv2.normalize(cv2.subtract(im, bg) + 128, None, 0, 255, cv2.NORM_MINMAX)
    if debug: print(f"[illumination_flatten] k={k} 적용")
    return _cv_to_pil(out)

# ---------- 하이라이트/빛반사 감쇠 ----------
def suppress_glare(img: Image.Image, v_high: int = 230, s_low: int = 40, debug: bool = False) -> Image.Image:
    """
    new suppress_glare(하이라이트/빛반사 감쇠)
    - HSV에서 S 낮고 V 높은 영역을 완만히 억제
    """
    if cv2 is None:
        if debug: print("[suppress_glare] OpenCV 미설치 - 원본 반환")
        return img
    im = _pil_to_cv(img)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV) if im.ndim == 3 else cv2.cvtColor(cv2.cvtColor(im, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)
    mask = cv2.inRange(S, 0, s_low) & cv2.inRange(V, v_high, 255)
    # 밝기 완만 감소
    V2 = V.copy()
    V2[mask > 0] = (0.85 * V2[mask > 0]).astype(np.uint8)
    hsv2 = cv2.merge([H, S, V2])
    out = cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)
    if debug: print("[suppress_glare] 글레어 감쇠 적용")
    return _cv_to_pil(out)

# ---------- 이미지 모드 정규화 ----------
def normalize_mode(img: Image.Image) -> Image.Image:
    """
    5) 모드 정규화: 이후 연산 호환을 위해 L 또는 RGB로 제한
    """
    if img.mode not in ("L", "RGB"):
        return img.convert("RGB")
    return img

# ---------- 약한 전역 대비 보정 ----------
def weak_autocontrast(img: Image.Image, cutoff: float = 0.4) -> Image.Image:
    """
    6) 자동 대비: 낮은 컷오프(0.4%)로 미세 픽셀(소수점·단위) 클리핑 방지
    """
    return ImageOps.autocontrast(img, cutoff=cutoff)

# ---------- 로컬 대비 향상·과도 시 비활성화 ----------
def apply_clahe(img: Image.Image, clip_limit: float = 2.0, tile_grid: Tuple[int,int] = (8,8), debug: bool = False) -> Image.Image:
    """
    new apply_clahe(로컬 대비 향상·과도 시 비활성화)
    """
    if cv2 is None:
        if debug: print("[apply_clahe] OpenCV 미설치 - 원본 반환")
        return img
    im = _pil_to_cv(img)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    if im.ndim == 3:
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
        L2 = clahe.apply(L)
        lab2 = cv2.merge([L2, A, B])
        out = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
    else:
        out = clahe.apply(im)
    if debug: print("[apply_clahe] 적용 완료")
    return _cv_to_pil(out)

# ---------- 보수적 샤프닝 ----------
def conservative_sharpen(img: Image.Image, radius: float = 1.0, percent: int = 120, threshold: int = 4) -> Image.Image:
    """
    7) 보수적 샤픈: 소수점 주변 헤일로 없이 스트로크만 강화
    """
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))

# ---------- 적-흑 변환 ----------
def blacken_reddish_text(
    img: Image.Image,
    hue_band: int = 8,     # 0°(빨강) 주변 허용 범위(도, OpenCV는 0~180 스케일)
    sat_thr: int = 70,      # 채도 임계
    min_v: int = 70,        # 최소 명도(배경 제외)
    darken: float = 0.10,   # V(밝기) 감쇠 비율(0~1, 낮을수록 더 검게)
    thicken: int = 0,       # 마스크 팽창 횟수(획 보강)
    debug: bool = False
) -> Image.Image:
    """
    붉은/주황 계열 텍스트를 그레이스케일 변환 전에 '검정에 가깝게' 어둡게 만든다.
    - 흰 배경과의 대비를 키워 OCR에서 옅어지는 현상을 완화.
    - HSV에서 빨강(0° 부근, 0~hue_band 또는 180-hue_band~180)을 잡아 V를 감쇠.
    """
    if cv2 is None:
        if debug: print("[blacken_reddish_text] OpenCV 미설치 - 원본 반환")
        return img

    arr = _pil_to_cv(img)
    if arr.ndim == 2:
        return img  # 이미 그레이스케일

    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)

    band = int(max(1, min(hue_band, 30)))
    # 빨강 영역 마스크: 0~band 또는 180-band~180
    mask_red = ((H <= band) | (H >= 180 - band)) & (S >= sat_thr) & (V >= min_v)
    mask = mask_red.astype(np.uint8) * 255

    if thicken > 0:
        ker = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, ker, iterations=int(thicken))

    V2 = V.copy()
    V2[mask > 0] = (V2[mask > 0].astype(np.float32) * float(max(0.01, min(darken, 1.0)))).astype(np.uint8)

    hsv2 = cv2.merge([H, S, V2])
    out = cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)
    if debug: print("[blacken_reddish_text] 적용 완료")
    return _cv_to_pil(out)

# ---------- 청-흑 변환 ----------
def blacken_bluish_text(
    img: Image.Image,
    hue_center: int = 120,  # 파랑 중심 Hue(0~180, OpenCV HSV 스케일에서 파랑≈120)
    hue_band: int = 16,     # 중심 주변 허용 범위
    sat_thr: int = 55,      # 채도 임계
    min_v: int = 55,        # 최소 명도(배경 제외)
    darken: float = 0.1,   # V(밝기) 감쇠 비율(0~1, 낮을수록 더 검게)
    thicken: int = 0.3,       # 마스크 팽창(획 보강)
    debug: bool = False
) -> Image.Image:
    """
    파란/청록 계열 텍스트를 그레이스케일 변환 전에 '검정에 가깝게' 어둡게 만든다.
    - 흰 배경과의 대비를 키워 OCR에서 옅어지는 현상을 완화.
    - HSV에서 hue_center±hue_band 범위를 잡아 V를 감쇠.
    """
    if cv2 is None:
        if debug: print("[blacken_bluish_text] OpenCV 미설치 - 원본 반환")
        return img

    arr = _pil_to_cv(img)
    if arr.ndim == 2:
        return img  # 이미 그레이스케일

    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)

    band = int(max(1, min(hue_band, 30)))
    c = int(np.clip(hue_center, 0, 180))
    low, high = c - band, c + band
    if low >= 0 and high <= 180:
        mask_h = (H >= low) & (H <= high)
    else:
        # 0~180 경계랩 처리
        mask_h = (H >= (low % 180)) | (H <= (high % 180))

    mask = (mask_h & (S >= sat_thr) & (V >= min_v)).astype(np.uint8) * 255

    if thicken > 0:
        ker = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, ker, iterations=int(thicken))

    V2 = V.copy()
    V2[mask > 0] = (V2[mask > 0].astype(np.float32) * float(max(0.01, min(darken, 1.0)))).astype(np.uint8)

    hsv2 = cv2.merge([H, S, V2])
    out = cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)
    if debug: print("[blacken_bluish_text] 적용 완료 (center=%d, band=%d)" % (c, band))
    return _cv_to_pil(out)

# ---------- 그레이스케일 변환 ----------
def to_grayscale(img: Image.Image) -> Image.Image:
    """
    8) 그레이스케일: 문서형 이미지에서 텍스트 대비를 높여 인식 안정화
    """
    if img.mode != "L":
        return img.convert("L")
    return img

# ---------- 적응형 이진화·문서용 ----------
def adaptive_binarize_for_ocr(img: Image.Image, block_size: int = 25, k: float = 0.15, debug: bool = False) -> Image.Image:
    """
    new adaptive_binarize_for_ocr(적응형 이진화·문서용)
    - scikit-image의 Sauvola가 있으면 사용, 없으면 OpenCV 가우시안 적응 이진화
    """
    arr = _pil_to_cv(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if (cv2 is not None and arr.ndim == 3) else (arr if arr.ndim == 2 else arr[:, :, 0])
    try:
        from skimage.filters import threshold_sauvola  # type: ignore
        win = block_size if block_size % 2 == 1 else block_size + 1
        thresh = threshold_sauvola(gray, window_size=win, k=k)
        bw = (gray > thresh).astype(np.uint8) * 255
        if debug: print("[adaptive_binarize_for_ocr] Sauvola 적용")
    except Exception:
        if cv2 is None:
            if debug: print("[adaptive_binarize_for_ocr] OpenCV/Skimage 없음 - 원본 반환")
            return img
        win = block_size if block_size % 2 == 1 else block_size + 1
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, win, 10)
        if debug: print("[adaptive_binarize_for_ocr] OpenCV 적응 이진화 적용")
    return Image.fromarray(bw)

# ---------- 모폴로지로 표 수평/수직 라인 약 강화 ----------
def enhance_table_lines(img: Image.Image, strength: float = 0.5, debug: bool = False) -> Image.Image:
    """
    new enhance_table_lines(모폴로지로 표 수평/수직 라인 약 강화)
    - 블랙햇(black-hat)으로 어두운 선을 강조 후 원본에서 소량 감산
    """
    if cv2 is None:
        if debug: print("[enhance_table_lines] OpenCV 미설치 - 원본 반환")
        return img
    im = _pil_to_cv(img)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    h, w = gray.shape[:2]
    hk = max(3, (w // 80) | 1)
    vk = max(3, (h // 80) | 1)
    hker = cv2.getStructuringElement(cv2.MORPH_RECT, (hk, 1))
    vker = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vk))
    hhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, hker)
    vhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, vker)
    comb = cv2.max(hhat, vhat)
    delta = (comb * np.clip(strength, 0.0, 1.0)).astype(np.uint8)
    enhanced = cv2.subtract(gray, delta)
    if im.ndim == 3:
        out = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    else:
        out = enhanced
    if debug: print("[enhance_table_lines] 라인 강화 완료")
    return _cv_to_pil(out)

# ---------- TSV 앵커 기반 테이블 스마트 크롭 ----------
def table_smart_crop(
    img: Image.Image,
    lang: str = "eng+kor",
    conf_min: int = 30,
    top_margin: int = 18,
    bottom_margin: int = 10,
    min_header_hits: int = 2,
    first_col_tolerance: int = 80,
    gap_multiplier: float = 2.8,
    min_rows: int = 5,
    debug: bool = True,
    min_table_height: int = 100,  # 🆕 최소 테이블 높이 파라미터
) -> Image.Image:
    """
    테이블 스마트 크롭(1순위: Tesseract TSV 앵커)
    - 상단: 헤더(국/영 키워드) 또는 바이오마커 열의 첫 클러스터 시작
    - 하단: 다음 헤더 직전 또는 큰 수직 공백(행간 중앙값*k) 직전
    - 여러 테이블이 있어도 가장 위 테이블 1개만 남김
    """
    if debug:
        print(f"[table_smart_crop] 🚀 시작 - 이미지 크기: {img.size}")
    
    try:
        pil = img if img.mode in ("L", "RGB") else img.convert("RGB")
        if debug:
            print(f"[table_smart_crop] 🖼️ 이미지 모드: {pil.mode}")

        # OCR
        if debug:
            print("[table_smart_crop] 📝 OCR 시작 (Tesseract)...")
        config = "--oem 3 --psm 4"
        data = image_to_data(pil, lang=lang, config=config, output_type=Output.DICT)
        n = len(data.get("text", []))
        if debug:
            print(f"[table_smart_crop] 📊 OCR 완료 - 총 {n}개 텍스트 요소 감지")
        
        if n == 0:
            if debug:
                print("[table_smart_crop] ⚠️ OCR 결과 없음 - 원본 반환")
            return img

        # 단어 토큰 필터링
        if debug:
            print(f"[table_smart_crop] 🔍 토큰 필터링 (최소 신뢰도: {conf_min})...")
        tokens = []
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt:
                continue
            try:
                conf = float(data["conf"][i])
            except Exception:
                conf = -1
            if conf < conf_min:
                continue
            tokens.append(
                {
                    "text": txt,
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "w": int(data["width"][i]),
                    "h": int(data["height"][i]),
                    "page": int(data["page_num"][i]),
                    "block": int(data["block_num"][i]),
                    "par": int(data["par_num"][i]),
                    "line": int(data["line_num"][i]),
                }
            )
        
        if debug:
            print(f"[table_smart_crop] ✅ 유효한 토큰: {len(tokens)}개")
        
        if not tokens:
            if debug:
                print("[table_smart_crop] ⚠️ 유효한 토큰 없음 - 원본 반환")
            return img

        # 라인 그룹핑
        if debug:
            print("[table_smart_crop] 📋 라인 그룹핑 시작...")
        from collections import defaultdict
        groups = defaultdict(list)
        for t in tokens:
            key = (t["page"], t["block"], t["par"], t["line"])
            groups[key].append(t)

        lines = []
        for key, group in groups.items():
            x0 = min(g["x"] for g in group)
            y0 = min(g["y"] for g in group)
            x1 = max(g["x"] + g["w"] for g in group)
            y1 = max(g["y"] + g["h"] for g in group)
            text_norm = " ".join(g["text"] for g in group).lower()
            lines.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": text_norm})
        
        if debug:
            print(f"[table_smart_crop] ✅ 라인 그룹핑 완료: {len(lines)}개 라인")
        
        if not lines:
            if debug:
                print("[table_smart_crop] ⚠️ 라인 없음 - 원본 반환")
            return img
        
        lines.sort(key=lambda l: l["y0"])

        # 헤더 후보 판단(국/영 혼합)
        if debug:
            print("[table_smart_crop] 🔎 헤더 라인 검색 중...")
        header_kws = {
            "name", "unit", "result", "reference", "ref", "min", "max",
            "항목", "검사항목", "결과", "단위", "기준치", "참조치", "참고치"
        }
        def is_header(l) -> bool:
            hits = sum(1 for kw in header_kws if kw in l["text"])
            return hits >= min_header_hits and len(l["text"]) >= 4

        header_lines = [l for l in lines if is_header(l)]
        header_lines.sort(key=lambda l: l["y0"])
        
        if debug:
            print(f"[table_smart_crop] 📌 헤더 라인 발견: {len(header_lines)}개")
            if header_lines:
                for idx, h in enumerate(header_lines[:5]):  # 🆕 최대 5개만 출력
                    print(f"[table_smart_crop]    헤더 {idx+1}: y={h['y0']}, text='{h['text'][:50]}...'")

        # 바이오마커 앵커(헤더 실패 대비)
        if debug:
            print("[table_smart_crop] 🧬 바이오마커 검색 중...")
        biomarker_kws = {
            "rbc","hct","hgb","mcv","mch","mchc","plt","wbc",
            "retic","glucose","glu","bun","crea","creatinine","ast","alt","alp",
            "mpv","pct","rdw","neut","lymph","mono","eos","baso"
        }
        def has_biomarker(l) -> bool:
            t = l["text"].replace("−", "-")
            return any(kw in t for kw in biomarker_kws)

        # 상단 y 결정
        if header_lines:
            if debug:
                print("[table_smart_crop] ✅ 헤더 기반으로 상단 계산")
            top_header = header_lines[0]
            y_top = max(0, top_header["y0"] - top_margin)
            anchor_x = top_header["x0"]
            if debug:
                print(f"[table_smart_crop]    y_top={y_top}, anchor_x={anchor_x}")
        else:
            if debug:
                print("[table_smart_crop] 🔄 헤더 없음 - 바이오마커 앵커 사용")
            biomarker_lines = [l for l in lines if has_biomarker(l)]
            if not biomarker_lines:
                if debug:
                    print("[table_smart_crop] ❌ 바이오마커도 없음 - 원본 반환")
                return img
            
            if debug:
                print(f"[table_smart_crop] ✅ 바이오마커 라인: {len(biomarker_lines)}개")
            
            biomarker_lines.sort(key=lambda l: l["y0"])
            xs = np.array([l["x0"] for l in biomarker_lines])
            anchor_x = int(np.percentile(xs, 20))
            first_band = [l for l in biomarker_lines if abs(l["x0"] - anchor_x) <= first_col_tolerance] or biomarker_lines[:1]
            y_top = max(0, min(l["y0"] for l in first_band) - top_margin)
            if debug:
                print(f"[table_smart_crop]    y_top={y_top}, anchor_x={anchor_x}")

        # 🆕 하단 y 결정 (개선된 로직)
        if debug:
            print("[table_smart_crop] 📐 하단 경계 계산 중...")
        
        # 다음 헤더 필터링: 충분히 멀리 떨어진 헤더만 고려
        below_headers = [l for l in header_lines if l["y0"] > y_top + min_table_height]
        
        if debug:
            print(f"[table_smart_crop]    충분히 멀리 떨어진 헤더: {len(below_headers)}개 (최소 거리: {min_table_height}px)")
        
        if below_headers:
            # 다음 테이블의 헤더를 찾았다면 그 직전까지
            y_bottom = max(y_top + min_table_height, below_headers[0]["y0"] - 10)
            if debug:
                print(f"[table_smart_crop] ✅ 다음 테이블 헤더로 하단 결정: y_bottom={y_bottom}")
        else:
            # 다음 헤더가 없으면 공백 분석으로 하단 결정
            if debug:
                print("[table_smart_crop] 🔄 다음 헤더 없음 - 공백 분석으로 하단 결정")
            candidate = [l for l in lines if l["y0"] >= y_top]
            band = [l for l in candidate if abs(l["x0"] - anchor_x) <= first_col_tolerance]
            band.sort(key=lambda l: l["y0"])
            
            if debug:
                print(f"[table_smart_crop]    테이블 후보 라인: {len(band)}개")
            
            if len(band) < min_rows:
                if debug:
                    print(f"[table_smart_crop] ⚠️ 최소 행 수 부족 ({len(band)} < {min_rows})")
                    print(f"[table_smart_crop] 🔄 전체 라인에서 공백 분석 시도...")
                # 🆕 첫 열 제약 완화: 전체 라인에서 y_top 이후 모든 라인 고려
                band = [l for l in lines if l["y0"] >= y_top]
                band.sort(key=lambda l: l["y0"])
                
                if len(band) < min_rows:
                    if debug:
                        print(f"[table_smart_crop] ❌ 전체 라인도 부족 ({len(band)} < {min_rows}) - 원본 반환")
                    return img
            
            gaps = [band[i+1]["y0"] - band[i]["y1"] for i in range(len(band)-1)]
            med_gap = np.median([g for g in gaps if g >= 0]) if gaps else 20
            thresh = max(24, med_gap * gap_multiplier)
            
            if debug:
                print(f"[table_smart_crop]    행간 중앙값: {med_gap:.1f}px, 공백 임계값: {thresh:.1f}px")

            y_bottom = band[0]["y1"]
            prev_y1 = band[0]["y1"]
            row_count = 1
            for l in band[1:]:
                if (l["y0"] - prev_y1) > thresh:
                    if debug:
                        print(f"[table_smart_crop]    큰 공백 감지: {l['y0'] - prev_y1:.1f}px > {thresh:.1f}px")
                    break
                y_bottom = max(y_bottom, l["y1"])
                prev_y1 = l["y1"]
                row_count += 1
            
            y_bottom = min(img.height, int(y_bottom + bottom_margin))
            if debug:
                print(f"[table_smart_crop] ✅ 하단 결정: y_bottom={y_bottom}, 테이블 행 수={row_count}")

        # 최종 검증
        final_height = y_bottom - y_top
        if final_height < 64:
            if debug:
                print(f"[table_smart_crop] ❌ 테이블 높이 부족 ({final_height}px < 64px) - 원본 반환")
            return img

        # 크롭 실행
        cropped = img.crop((0, int(y_top), img.width, int(y_bottom)))
        if debug:
            print(f"[table_smart_crop] ✂️ 크롭 완료")
            print(f"[table_smart_crop]    원본: {img.size} → 크롭: {cropped.size}")
            print(f"[table_smart_crop]    영역: y_top={int(y_top)}, y_bottom={int(y_bottom)}")
            print(f"[table_smart_crop]    크롭 높이: {final_height}px")
        
        return cropped

    except Exception as e:
        if debug:
            print(f"[table_smart_crop] ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        return img

# ---------- 얇은 흰색 테두리 추가 ----------
def add_white_border(img: Image.Image, border: int = 4) -> Image.Image:
    """
    10) 테두리 추가: 가장자리 문자가 잘리지 않도록 얇은 흰색 여백
    """
    if border and border > 0:
        fill = 255 if img.mode == "L" else (255, 255, 255)
        return ImageOps.expand(img, border=border, fill=fill)
    return img

# ---------- 목표 해상도로 다운스케일 ----------
def downscale_target_long_edge(img: Image.Image, target_long_edge: int = 1920) -> Image.Image:
    """
    11) 해상도 표준화(다운스케일 허용): 과대 크기는 축소
    """
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > target_long_edge:
        scale = target_long_edge / float(long_edge)
        img = img.resize((int(round(w * scale)), int(round(h * scale))), Image.LANCZOS)
    return img

# ---------- OCR 품질 게이트 ----------
def _tesseract_metrics(pil_img: Image.Image, lang: str = "eng+kor") -> dict:
    try:
        data = image_to_data(pil_img, lang=lang, config="--oem 3 --psm 6", output_type=Output.DICT)
        confs = []
        for c in data.get("conf", []):
            try:
                v = float(c)
                if v >= 0:
                    confs.append(v)
            except Exception:
                pass
        mean_conf = float(np.mean(confs)) if confs else 0.0
        n_tokens = int(len(confs))
        return {"mean_conf": mean_conf, "tokens": n_tokens}
    except Exception:
        return {"mean_conf": 0.0, "tokens": 0}

def ocr_quality_gate(
    img: Image.Image,
    baseline_img: Optional[Image.Image] = None,
    lang: str = "eng+kor",
    min_delta_conf: float = -1.0,
    min_delta_tokens: int = -9999,
    debug: bool = True,
) -> Image.Image:
    """
    new ocr_quality_gate(토큰 수/평균 conf 기반 품질 점검·악화 시 이전 단계 롤백)
    - baseline_img가 주어지면 현재 이미지가 품질이 더 나쁘면 baseline으로 롤백
    - min_delta_*는 '현재 - 기준'의 최소 허용 변화량(음수 허용). 더 낮으면 롤백.
    """
    cur = _tesseract_metrics(img, lang=lang)
    if baseline_img is None:
        # 메트릭만 기록하고 통과
        try:
            img.info["ocr_quality"] = cur
        except Exception:
            pass
        if debug: print(f"[ocr_quality_gate] conf={cur['mean_conf']:.1f}, tokens={cur['tokens']}")
        return img

    base = _tesseract_metrics(baseline_img, lang=lang)
    d_conf = cur["mean_conf"] - base["mean_conf"]
    d_tok = cur["tokens"] - base["tokens"]
    if debug:
        print(f"[ocr_quality_gate] Δconf={d_conf:.1f}, Δtok={d_tok}")
    worse = (d_conf < min_delta_conf) or (d_tok < min_delta_tokens)
    return baseline_img if worse else img

# ---------- PNG 무손실 저장 ----------
def save_png_bytes(img: Image.Image, compress_level: int = 6) -> bytes:
    """
    12) PNG 저장(무손실): 텍스트/기호 보존에 유리
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=compress_level)
    return buf.getvalue()

def apply_pipeline(img: Image.Image, steps: Sequence[tuple[Callable, dict]]) -> Image.Image:
    """
    체이닝 실행 유틸. [(func, kwargs), ...] 형태로 전달된 스텝을 순서대로 적용.
    """
    for func, kwargs in steps:
        img = func(img, **kwargs)
    return img