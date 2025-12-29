"""이미지 전처리 모듈 테스트

Step 2.5: image_preprocessor.py 기능 검증
"""

import io
import pytest
import numpy as np
from PIL import Image

from src.services.preprocessing.image_preprocessor import (
    # 유틸
    _pil_to_cv,
    _cv_to_pil,
    _norm_minmax,
    # 로드/저장
    open_with_exif,
    save_png_bytes,
    # 기본 변환
    flatten_transparency,
    normalize_mode,
    to_grayscale,
    add_white_border,
    # 크롭/리사이즈
    auto_crop_with_margin,
    upscale_min_resolution,
    downscale_target_long_edge,
    # 대비/샤프닝
    weak_autocontrast,
    apply_clahe,
    conservative_sharpen,
    illumination_flatten,
    suppress_glare,
    # 색상 처리
    blacken_reddish_text,
    blacken_bluish_text,
    # 고급 보정
    detect_document_quad,
    perspective_unwarp,
    # 클래스
    Settings,
    ImagePreprocessor,
    apply_pipeline,
)


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def sample_rgb_image():
    """100x100 RGB 이미지"""
    return Image.new("RGB", (100, 100), color=(200, 200, 200))


@pytest.fixture
def sample_rgba_image():
    """100x100 RGBA 이미지 (투명 채널 포함)"""
    img = Image.new("RGBA", (100, 100), color=(200, 200, 200, 128))
    return img


@pytest.fixture
def sample_grayscale_image():
    """100x100 그레이스케일 이미지"""
    return Image.new("L", (100, 100), color=150)


@pytest.fixture
def sample_image_with_content():
    """내용이 있는 이미지 (크롭 테스트용)"""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    # 중앙에 검은 사각형
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (0, 0, 0))
    return img


@pytest.fixture
def sample_image_bytes(sample_rgb_image):
    """PNG 바이트 데이터"""
    buf = io.BytesIO()
    sample_rgb_image.save(buf, format="PNG")
    return buf.getvalue()


# =============================================================================
# Step 2.5.1: 기본 유틸 함수 테스트
# =============================================================================

class TestBasicUtils:
    """기본 유틸 함수 테스트"""

    def test_pil_to_cv_rgb(self, sample_rgb_image):
        """PIL RGB → CV BGR 변환"""
        cv_img = _pil_to_cv(sample_rgb_image)
        assert isinstance(cv_img, np.ndarray)
        assert cv_img.shape == (100, 100, 3)

    def test_pil_to_cv_grayscale(self, sample_grayscale_image):
        """PIL L → CV 변환"""
        cv_img = _pil_to_cv(sample_grayscale_image)
        assert isinstance(cv_img, np.ndarray)
        assert cv_img.shape == (100, 100)

    def test_pil_to_cv_rgba(self, sample_rgba_image):
        """PIL RGBA → CV BGR 변환"""
        cv_img = _pil_to_cv(sample_rgba_image)
        assert cv_img.shape == (100, 100, 3)

    def test_cv_to_pil_bgr(self):
        """CV BGR → PIL RGB 변환"""
        cv_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv_img[:, :, 0] = 255  # Blue channel in BGR
        pil_img = _cv_to_pil(cv_img)
        assert pil_img.mode == "RGB"
        # BGR에서 Blue(인덱스 0)가 RGB에서 Blue(인덱스 2)로 변환되어야 함
        r, g, b = pil_img.getpixel((0, 0))
        assert b == 255
        assert r == 0

    def test_cv_to_pil_grayscale(self):
        """CV grayscale → PIL L 변환"""
        cv_img = np.zeros((100, 100), dtype=np.uint8)
        cv_img[:] = 128
        pil_img = _cv_to_pil(cv_img)
        assert pil_img.mode == "L"

    def test_norm_minmax(self):
        """배열 정규화"""
        arr = np.array([0, 50, 100], dtype=np.float32)
        result = _norm_minmax(arr)
        assert result.min() == 0
        assert result.max() == 255
        assert result.dtype == np.uint8


# =============================================================================
# Step 2.5.2: 로드/저장 함수 테스트
# =============================================================================

class TestLoadSave:
    """로드/저장 함수 테스트"""

    def test_open_with_exif(self, sample_image_bytes):
        """EXIF 보정하여 로드"""
        img = open_with_exif(sample_image_bytes)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_save_png_bytes(self, sample_rgb_image):
        """PNG 바이트로 저장"""
        result = save_png_bytes(sample_rgb_image)
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG 매직 넘버 확인
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_save_png_bytes_compress_level(self, sample_rgb_image):
        """압축 레벨에 따른 크기 차이"""
        result_low = save_png_bytes(sample_rgb_image, compress_level=1)
        result_high = save_png_bytes(sample_rgb_image, compress_level=9)
        # 높은 압축 레벨이 더 작거나 같아야 함
        assert len(result_high) <= len(result_low)


# =============================================================================
# Step 2.5.3: 기본 변환 함수 테스트
# =============================================================================

class TestBasicTransform:
    """기본 변환 함수 테스트"""

    def test_flatten_transparency(self, sample_rgba_image):
        """투명 채널 플래튼"""
        result = flatten_transparency(sample_rgba_image)
        assert result.mode == "RGB"

    def test_flatten_transparency_rgb_passthrough(self, sample_rgb_image):
        """RGB 이미지는 그대로 반환"""
        result = flatten_transparency(sample_rgb_image)
        assert result.mode == "RGB"

    def test_normalize_mode(self, sample_rgba_image):
        """모드 정규화"""
        result = normalize_mode(sample_rgba_image)
        assert result.mode == "RGB"

    def test_normalize_mode_rgb_passthrough(self, sample_rgb_image):
        """RGB는 그대로"""
        result = normalize_mode(sample_rgb_image)
        assert result.mode == "RGB"

    def test_to_grayscale(self, sample_rgb_image):
        """그레이스케일 변환"""
        result = to_grayscale(sample_rgb_image)
        assert result.mode == "L"

    def test_add_white_border(self, sample_rgb_image):
        """흰색 테두리 추가"""
        border = 10
        result = add_white_border(sample_rgb_image, border=border)
        assert result.size == (120, 120)


# =============================================================================
# Step 2.5.4: 크롭/리사이즈 함수 테스트
# =============================================================================

class TestCropResize:
    """크롭/리사이즈 함수 테스트"""

    def test_auto_crop_with_margin(self, sample_image_with_content):
        """자동 크롭"""
        result = auto_crop_with_margin(sample_image_with_content, margin=10)
        # 원본 200x200에서 중앙 100x100 + margin 10 = 약 120x120
        assert result.size[0] < 200
        assert result.size[1] < 200

    def test_upscale_min_resolution(self):
        """최소 해상도 업스케일"""
        small_img = Image.new("RGB", (100, 100), color="white")
        result = upscale_min_resolution(small_img, min_long_edge=200)
        assert max(result.size) == 200

    def test_upscale_no_change_if_large(self):
        """이미 큰 이미지는 변경 없음"""
        large_img = Image.new("RGB", (500, 500), color="white")
        result = upscale_min_resolution(large_img, min_long_edge=200)
        assert result.size == (500, 500)

    def test_downscale_target_long_edge(self):
        """타겟 크기 다운스케일"""
        large_img = Image.new("RGB", (400, 300), color="white")
        result = downscale_target_long_edge(large_img, target_long_edge=200)
        assert max(result.size) == 200

    def test_downscale_no_change_if_small(self):
        """이미 작은 이미지는 변경 없음"""
        small_img = Image.new("RGB", (100, 100), color="white")
        result = downscale_target_long_edge(small_img, target_long_edge=200)
        assert result.size == (100, 100)


# =============================================================================
# Step 2.5.5: 대비/샤프닝 함수 테스트
# =============================================================================

class TestContrastSharpen:
    """대비/샤프닝 함수 테스트"""

    def test_weak_autocontrast(self, sample_rgb_image):
        """약한 자동 대비"""
        result = weak_autocontrast(sample_rgb_image)
        assert isinstance(result, Image.Image)
        assert result.size == sample_rgb_image.size

    def test_apply_clahe(self, sample_rgb_image):
        """CLAHE 적용"""
        result = apply_clahe(sample_rgb_image)
        assert isinstance(result, Image.Image)
        assert result.size == sample_rgb_image.size

    def test_conservative_sharpen(self, sample_rgb_image):
        """보수적 샤프닝"""
        result = conservative_sharpen(sample_rgb_image)
        assert isinstance(result, Image.Image)
        assert result.size == sample_rgb_image.size

    def test_illumination_flatten(self, sample_rgb_image):
        """배경 평탄화"""
        result = illumination_flatten(sample_rgb_image)
        assert isinstance(result, Image.Image)
        assert result.size == sample_rgb_image.size

    def test_suppress_glare(self, sample_rgb_image):
        """글레어 감쇠"""
        result = suppress_glare(sample_rgb_image)
        assert isinstance(result, Image.Image)
        assert result.size == sample_rgb_image.size


# =============================================================================
# Step 2.5.6: 색상 처리 함수 테스트
# =============================================================================

class TestColorProcess:
    """색상 처리 함수 테스트"""

    def test_blacken_reddish_text(self):
        """붉은 텍스트 검정화"""
        # 빨간색 이미지
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        result = blacken_reddish_text(img)
        assert isinstance(result, Image.Image)

    def test_blacken_bluish_text(self):
        """푸른 텍스트 검정화"""
        # 파란색 이미지
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        result = blacken_bluish_text(img)
        assert isinstance(result, Image.Image)

    def test_blacken_grayscale_passthrough(self, sample_grayscale_image):
        """그레이스케일 이미지는 그대로 반환"""
        result = blacken_reddish_text(sample_grayscale_image)
        assert result.mode == "L"


# =============================================================================
# Step 2.5.7: 고급 보정 함수 테스트
# =============================================================================

class TestAdvancedCorrection:
    """고급 보정 함수 테스트"""

    def test_detect_document_quad_no_document(self, sample_rgb_image):
        """문서 없는 이미지에서 None 반환"""
        result = detect_document_quad(sample_rgb_image)
        # 단색 이미지에서는 문서 경계를 찾지 못함
        assert result is None

    def test_perspective_unwarp_no_quad(self, sample_rgb_image):
        """quad 없으면 원본 반환"""
        result = perspective_unwarp(sample_rgb_image)
        assert result.size == sample_rgb_image.size


# =============================================================================
# Step 2.5.8: Settings 및 ImagePreprocessor 클래스 테스트
# =============================================================================

class TestSettings:
    """Settings 테스트"""

    def test_default_settings(self):
        """기본 설정"""
        settings = Settings()
        assert settings.enable_flatten_transparency is False
        assert settings.enable_to_grayscale is False
        assert settings.debug is False

    def test_custom_settings(self):
        """커스텀 설정"""
        settings = Settings(
            enable_to_grayscale=True,
            debug=True
        )
        assert settings.enable_to_grayscale is True
        assert settings.debug is True


class TestImagePreprocessor:
    """ImagePreprocessor 클래스 테스트"""

    def test_init_default(self):
        """기본 초기화"""
        preprocessor = ImagePreprocessor()
        assert preprocessor.settings is not None

    def test_init_custom_settings(self):
        """커스텀 설정으로 초기화"""
        settings = Settings(enable_to_grayscale=True)
        preprocessor = ImagePreprocessor(settings)
        assert preprocessor.settings.enable_to_grayscale is True

    def test_process_bytes(self, sample_image_bytes):
        """바이트 전처리"""
        preprocessor = ImagePreprocessor()
        result = preprocessor.process_bytes(sample_image_bytes)
        assert isinstance(result, bytes)

    def test_process_bytes_with_grayscale(self, sample_image_bytes):
        """그레이스케일 변환 포함"""
        settings = Settings(enable_to_grayscale=True)
        preprocessor = ImagePreprocessor(settings)
        result = preprocessor.process_bytes(sample_image_bytes)
        assert isinstance(result, bytes)


class TestApplyPipeline:
    """apply_pipeline 함수 테스트"""

    def test_apply_pipeline(self, sample_rgb_image):
        """커스텀 파이프라인 적용"""
        steps = [
            (flatten_transparency, {}),
            (to_grayscale, {}),
        ]
        result = apply_pipeline(sample_rgb_image, steps)
        assert result.mode == "L"

    def test_apply_pipeline_with_params(self, sample_rgb_image):
        """파라미터가 있는 파이프라인"""
        steps = [
            (upscale_min_resolution, {"min_long_edge": 200}),
        ]
        result = apply_pipeline(sample_rgb_image, steps)
        assert max(result.size) == 200

