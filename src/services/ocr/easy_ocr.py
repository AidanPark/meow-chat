"""EasyOCR 기반 OCR 서비스

PyTorch와 EasyOCR을 사용하여 GPU 가속 OCR을 제공합니다.
OCRResultEnvelope 형태로 결과를 반환하여 line_preprocessor와 호환됩니다.

사용 예시:
    from src.services.ocr.easyocr_service import MyEasyOCR

    ocr = MyEasyOCR()
    result = ocr.run_ocr(image)
    # result.data.items[0].rec_texts
"""
from __future__ import annotations

import logging
from typing import List, Optional, Union

import numpy as np
from PIL import Image

from src.models.envelopes import (
    OCRData,
    OCRItem,
    OCRMeta,
    OCRResultEnvelope,
)
from .base import BaseOCRService

logger = logging.getLogger(__name__)


class MyEasyOCR(BaseOCRService):
    """EasyOCR 기반 OCR 서비스 (GPU 가속)

    PaddleOCR 대신 EasyOCR을 사용하여 RTX 5060 등 최신 GPU 지원.
    OCRResultEnvelope 형태로 결과를 반환하여 line_preprocessor와 호환.
    BaseOCRService를 상속하여 통일된 인터페이스 제공.

    Attributes:
        lang: 인식 언어 (기본값: 'korean')
        languages: EasyOCR 언어 리스트 (기본값: ['ko', 'en'])
        use_gpu: GPU 사용 여부

    Examples:
        >>> ocr = MyEasyOCR()
        >>> result = ocr.run_ocr_from_path("lab_result.png")
        >>> texts = result.data.items[0].rec_texts
    """

    def __init__(
        self,
        lang: str = "korean",
        languages: Optional[List[str]] = None,
        use_gpu: bool = True,
        **kwargs
    ):
        """MyEasyOCR 초기화

        Args:
            lang: 인식 언어 식별자 (메타데이터용)
            languages: EasyOCR 언어 리스트 (기본값: ['ko', 'en'])
            use_gpu: GPU 사용 여부 (기본값: True, 자동 감지)
            **kwargs: 추가 옵션 (현재 미사용)
        """
        self.lang = lang
        self.languages = languages or ['ko', 'en']
        self.use_gpu = use_gpu
        self._reader = None

        # GPU 사용 가능 여부 확인
        if self.use_gpu:
            try:
                import torch
                if not torch.cuda.is_available():
                    logger.warning(
                        "GPU 모드가 요청되었으나 CUDA를 사용할 수 없습니다. "
                        "CPU 모드로 전환합니다."
                    )
                    self.use_gpu = False
                else:
                    gpu_name = torch.cuda.get_device_name(0)
                    logger.info(f"GPU 모드 활성화: {gpu_name}")
            except ImportError:
                logger.warning("PyTorch가 설치되지 않았습니다. CPU 모드로 전환합니다.")
                self.use_gpu = False

    @property
    def reader(self):
        """EasyOCR Reader 인스턴스 (lazy initialization)"""
        if self._reader is None:
            self._reader = self._create_reader()
        return self._reader

    def _create_reader(self):
        """EasyOCR Reader 생성"""
        try:
            import easyocr
        except ImportError as e:
            raise ImportError(
                "easyocr 패키지가 설치되지 않았습니다. "
                "pip install easyocr 로 설치해주세요."
            ) from e

        logger.info(
            f"EasyOCR Reader 초기화: languages={self.languages}, gpu={self.use_gpu}"
        )

        return easyocr.Reader(
            lang_list=self.languages,
            gpu=self.use_gpu,
            verbose=False,
        )

    def _predict(self, image_input) -> List:
        """EasyOCR 실행 (내부용)

        Args:
            image_input: 이미지 (파일 경로, numpy array, PIL Image)

        Returns:
            EasyOCR 결과 리스트: [(bbox, text, confidence), ...]
        """
        return self.reader.readtext(image_input, detail=1, paragraph=False)

    def _convert_to_ocr_item(self, raw_results: List) -> OCRItem:
        """EasyOCR 결과를 OCRItem으로 변환

        Args:
            raw_results: EasyOCR 결과 [(bbox, text, confidence), ...]

        Returns:
            OCRItem 인스턴스
        """
        rec_texts: List[str] = []
        rec_scores: List[float] = []
        dt_polys: List[List[List[float]]] = []

        for result in raw_results:
            try:
                bbox, text, confidence = result

                # bbox 변환: numpy array -> list
                if isinstance(bbox, np.ndarray):
                    bbox = bbox.tolist()
                else:
                    bbox = [list(point) for point in bbox]

                rec_texts.append(str(text))
                rec_scores.append(float(confidence))
                dt_polys.append(bbox)

            except Exception as e:
                logger.warning(f"OCR 결과 변환 실패: {e}, result={result}")
                continue

        return OCRItem(
            rec_texts=rec_texts,
            rec_scores=rec_scores,
            dt_polys=dt_polys,
        )

    def run_ocr_from_path(self, file_path: str) -> Optional[OCRResultEnvelope]:
        """파일 경로에서 OCR 실행

        Args:
            file_path: 이미지 파일 경로

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            raw_results = self._predict(file_path)
            item = self._convert_to_ocr_item(raw_results)

            return OCRResultEnvelope(
                stage='ocr',
                data=OCRData(items=[item]),
                meta=OCRMeta(
                    items=len(item),
                    source='path',
                    lang=self.lang,
                    engine='EasyOCR'
                )
            )
        except Exception as e:
            logger.error(f"파일 OCR 실패: {e}")
            return None

    def run_ocr_from_nparray(self, image_array: np.ndarray) -> Optional[OCRResultEnvelope]:
        """numpy 배열에서 OCR 실행

        Args:
            image_array: 이미지 numpy 배열 (RGB 또는 BGR)

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            raw_results = self._predict(image_array)
            item = self._convert_to_ocr_item(raw_results)

            return OCRResultEnvelope(
                stage='ocr',
                data=OCRData(items=[item]),
                meta=OCRMeta(
                    items=len(item),
                    source='nparray',
                    lang=self.lang,
                    engine='EasyOCR'
                )
            )
        except Exception as e:
            logger.error(f"배열 OCR 실패: {e}")
            return None

    def run_ocr_from_bytes(self, image_bytes: bytes) -> Optional[OCRResultEnvelope]:
        """바이트 데이터에서 OCR 실행

        Args:
            image_bytes: 이미지 바이트 데이터

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            import cv2

            # 바이트를 numpy 배열로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if cv_image is None:
                logger.error("이미지 디코딩 실패: 지원되지 않는 형식이거나 손상된 이미지")
                return None

            # BGR to RGB (EasyOCR은 RGB 기대)
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

            return self.run_ocr_from_nparray(cv_image)

        except Exception as e:
            logger.error(f"바이트 OCR 실패: {e}")
            return None

    def run_ocr(self, image: Union[str, np.ndarray, Image.Image, bytes]) -> Optional[OCRResultEnvelope]:
        """통합 OCR 실행 메서드

        입력 타입을 자동 감지하여 적절한 메서드 호출.

        Args:
            image: 이미지 (파일 경로, numpy array, PIL Image, bytes)

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        if isinstance(image, str):
            return self.run_ocr_from_path(image)
        elif isinstance(image, bytes):
            return self.run_ocr_from_bytes(image)
        elif isinstance(image, Image.Image):
            # PIL Image -> numpy array
            return self.run_ocr_from_nparray(np.array(image))
        elif isinstance(image, np.ndarray):
            return self.run_ocr_from_nparray(image)
        else:
            logger.error(f"지원하지 않는 이미지 타입: {type(image)}")
            return None

    def extract_text(self, image: Image.Image) -> OCRResultEnvelope:
        """이미지에서 텍스트 추출 (BaseOCRService 인터페이스 구현)

        Args:
            image: PIL Image 객체

        Returns:
            OCRResultEnvelope 객체
        """
        result = self.run_ocr(image)
        if result is None:
            # 실패 시 빈 결과 반환
            return OCRResultEnvelope(
                stage='ocr',
                data=OCRData(items=[OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])]),
                meta=OCRMeta(items=0, source='nparray', lang=self.lang, engine='EasyOCR')
            )
        return result

    @property
    def is_gpu_enabled(self) -> bool:
        """GPU 사용 여부"""
        return self.use_gpu

    def get_device_info(self) -> dict:
        """디바이스 정보 반환"""
        info = {
            "engine": "EasyOCR",
            "use_gpu": self.use_gpu,
            "languages": self.languages,
            "lang": self.lang,
        }

        if self.use_gpu:
            try:
                import torch
                info["cuda_available"] = torch.cuda.is_available()
                if torch.cuda.is_available():
                    info["gpu_name"] = torch.cuda.get_device_name(0)
                    info["gpu_memory_gb"] = round(
                        torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
                    )
            except ImportError:
                info["cuda_available"] = False

        return info


__all__ = ["MyEasyOCR"]

