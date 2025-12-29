"""PaddleOCR 기반 OCR 서비스

PaddlePaddle OCR을 사용하여 한국어 텍스트 인식을 제공합니다.
로컬 환경에서는 CPU 모드, 클라우드 배포 시 GPU 모드 자동 전환.
OCRResultEnvelope 형태로 결과를 반환하여 line_preprocessor와 호환.

사용 예시:
    from src.services.ocr.paddle_ocr import MyPaddleOCR

    # 로컬 (CPU)
    ocr = MyPaddleOCR(use_gpu=False)

    # 클라우드 (GPU)
    ocr = MyPaddleOCR(use_gpu=True)

    result = ocr.extract_text(image)
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union

import cv2
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


class MyPaddleOCR(BaseOCRService):
    """PaddleOCR 기반 OCR 서비스

    CPU/GPU 자동 전환 지원:
    - 로컬 개발: CPU 모드 (RTX 5060 호환성 문제 회피)
    - 클라우드 배포: GPU 모드 (Tesla T4 등 지원)

    이전 프로젝트(meow-chat-old)의 검증된 코드 기반으로 구현.
    동시성 제어(Semaphore/RLock)로 멀티스레드 환경에서 안정적 동작.

    Attributes:
        lang: 인식 언어 (기본값: 'korean')
        use_gpu: GPU 사용 여부 (자동 감지)

    Examples:
        >>> # CPU 모드 (로컬)
        >>> ocr = MyPaddleOCR(use_gpu=False)
        >>> result = ocr.extract_text(image)

        >>> # GPU 모드 (클라우드)
        >>> ocr = MyPaddleOCR(use_gpu=True)
        >>> result = ocr.extract_text(image)
    """

    # 클래스 전역 OCR 동시성 제어자 (lazy-init)
    _OCR_SEMAPHORE: Optional[threading.Semaphore] = None
    _OCR_SEMAPHORE_MAX: Optional[int] = None

    def __init__(
        self,
        lang: str = "korean",
        use_gpu: bool = False,  # 기본값 CPU (안전)
        enable_ocr_lock: bool = True,
        ocr_max_concurrency: int = 2,
        ocr_use_thread_pool: bool = False,
        ocr_pool_size: Optional[int] = None,
        **kwargs,
    ):
        """MyPaddleOCR 초기화

        Args:
            lang: 인식 언어 ('korean', 'en', 'ch' 등)
            use_gpu: GPU 사용 시도 여부 (호환성 자동 확인)
            enable_ocr_lock: OCR 호출 시 락 사용 여부
            ocr_max_concurrency: 최대 동시 OCR 실행 수
            ocr_use_thread_pool: 스레드 풀 사용 여부
            ocr_pool_size: 스레드 풀 크기
            **kwargs: 추가 PaddleOCR 옵션
        """
        self.lang = lang
        self._requested_gpu = use_gpu
        self.use_gpu = self._check_gpu_compatibility() if use_gpu else False
        self._ocr_engine = None
        self._init_kwargs = kwargs.copy()

        # 동시성 설정
        self.enable_ocr_lock = enable_ocr_lock
        self.ocr_max_concurrency = ocr_max_concurrency
        self.ocr_use_thread_pool = ocr_use_thread_pool
        self.ocr_pool_size = ocr_pool_size

        # 인스턴스 락
        self._ocr_lock: Optional[threading.RLock] = (
            threading.RLock() if self.enable_ocr_lock else None
        )

        # 클래스 전역 세마포어 lazy-init
        self._init_semaphore()

        # 선택적 스레드 풀
        self._executor: Optional[ThreadPoolExecutor] = None
        if self.ocr_use_thread_pool:
            pool_size = (
                self.ocr_pool_size
                if self.ocr_pool_size and self.ocr_pool_size > 0
                else max(1, self.ocr_max_concurrency)
            )
            try:
                self._executor = ThreadPoolExecutor(
                    max_workers=pool_size, thread_name_prefix="paddleocr"
                )
            except Exception:
                self._executor = None

        logger.info(
            f"PaddleOCR 초기화: lang={lang}, "
            f"requested_gpu={use_gpu}, actual_gpu={self.use_gpu}"
        )

    def _init_semaphore(self) -> None:
        """클래스 전역 세마포어 초기화"""
        try:
            m = int(self.ocr_max_concurrency or 0)
            if m > 0:
                cls = self.__class__
                if (
                    getattr(cls, "_OCR_SEMAPHORE", None) is None
                    or getattr(cls, "_OCR_SEMAPHORE_MAX", None) != m
                ):
                    cls._OCR_SEMAPHORE = threading.Semaphore(m)
                    cls._OCR_SEMAPHORE_MAX = m
        except Exception:
            pass

    def _check_gpu_compatibility(self) -> bool:
        """PaddlePaddle GPU 호환성 확인

        Returns:
            True: GPU 사용 가능
            False: CPU 폴백 필요
        """
        try:
            import paddle

            if not paddle.device.is_compiled_with_cuda():
                logger.warning(
                    "PaddlePaddle이 CUDA 없이 컴파일됨. CPU 모드로 전환."
                )
                return False

            # GPU 장치 확인
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count == 0:
                logger.warning("사용 가능한 GPU가 없습니다. CPU 모드로 전환.")
                return False

            gpu_name = paddle.device.cuda.get_device_name(0)
            logger.info(f"PaddlePaddle GPU 감지: {gpu_name}")
            return True

        except ImportError:
            logger.error(
                "PaddlePaddle이 설치되지 않았습니다. "
                "pip install paddlepaddle 로 설치하세요."
            )
            return False
        except Exception as e:
            logger.warning(f"GPU 호환성 확인 실패: {e}. CPU 모드로 폴백.")
            return False

    @property
    def ocr(self):
        """PaddleOCR 인스턴스 (lazy initialization)"""
        if self._ocr_engine is None:
            self._ocr_engine = self._create_ocr()
        return self._ocr_engine

    def _create_ocr(self):
        """PaddleOCR 인스턴스 생성"""
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise ImportError(
                "paddleocr 패키지가 설치되지 않았습니다. "
                "pip install paddleocr 로 설치해주세요."
            ) from e

        logger.info(
            f"PaddleOCR 생성: lang={self.lang}, use_gpu={self.use_gpu}"
        )

        # PaddleOCR 3.x 호환 설정 (이전 프로젝트와 동일)
        paddle_kwargs = {
            'lang': self.lang,
            'use_doc_orientation_classify': True,  # 문서 방향 분류/교정 모델 로드
            'use_doc_unwarping': True,             # 문서 휘어짐 보정
            'use_textline_orientation': True,      # 방향 분류 활성화
        }

        # 추가 kwargs 병합
        paddle_kwargs.update(self._init_kwargs)

        return PaddleOCR(**paddle_kwargs)

    def _predict_guarded(self, inp) -> List[Dict[str, Any]]:
        """세마포어/락으로 OCR 호출 보호

        Args:
            inp: 이미지 입력 (파일 경로, numpy array)

        Returns:
            PaddleOCR 결과 리스트
        """
        sem = getattr(self.__class__, "_OCR_SEMAPHORE", None)
        lock = self._ocr_lock if self.enable_ocr_lock else None

        if sem is not None:
            sem.acquire()
        try:
            if lock is not None:
                lock.acquire()
            try:
                # PaddleOCR 3.x에서는 predict() 메서드 사용
                # cls 인자는 없어지고, use_textline_orientation은 초기화 시 설정
                if self._executor is not None:
                    fut = self._executor.submit(self.ocr.predict, inp)
                    return fut.result()
                else:
                    return self.ocr.predict(inp)
            finally:
                if lock is not None:
                    try:
                        lock.release()
                    except Exception:
                        pass
        finally:
            if sem is not None:
                try:
                    sem.release()
                except Exception:
                    pass

    def _convert_to_ocr_item(self, raw_results) -> OCRItem:
        """PaddleOCR 결과를 OCRItem으로 변환

        Args:
            raw_results: PaddleOCR 3.x 결과 (list[OCRResult] 형식)

        Returns:
            OCRItem 인스턴스
        """
        rec_texts: List[str] = []
        rec_scores: List[float] = []
        dt_polys: List[List[List[float]]] = []

        if raw_results is None:
            return OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])

        # PaddleOCR 3.x는 list[OCRResult] 형식으로 반환
        # result[0]이 OCRResult 객체이며, rec_texts, rec_scores, dt_polys 속성을 가짐
        if isinstance(raw_results, list) and len(raw_results) > 0:
            ocr_result = raw_results[0]  # 첫 번째 페이지/이미지 결과

            # OCRResult 객체에서 속성 추출 (속성 또는 딕셔너리 접근)
            if hasattr(ocr_result, 'rec_texts'):
                rec_texts_raw = ocr_result.rec_texts
            elif isinstance(ocr_result, dict):
                rec_texts_raw = ocr_result.get('rec_texts', [])
            else:
                rec_texts_raw = []

            if hasattr(ocr_result, 'rec_scores'):
                rec_scores_raw = ocr_result.rec_scores
            elif isinstance(ocr_result, dict):
                rec_scores_raw = ocr_result.get('rec_scores', [])
            else:
                rec_scores_raw = []

            if hasattr(ocr_result, 'dt_polys'):
                dt_polys_raw = ocr_result.dt_polys
            elif isinstance(ocr_result, dict):
                dt_polys_raw = ocr_result.get('dt_polys', [])
            else:
                dt_polys_raw = []

            # 리스트로 변환
            if rec_texts_raw is not None:
                for i, text in enumerate(rec_texts_raw):
                    rec_texts.append(str(text))

            if rec_scores_raw is not None:
                for score in rec_scores_raw:
                    try:
                        rec_scores.append(float(score))
                    except (TypeError, ValueError):
                        rec_scores.append(0.0)

            if dt_polys_raw is not None:
                for bbox in dt_polys_raw:
                    try:
                        # numpy array -> list 변환
                        if isinstance(bbox, np.ndarray):
                            bbox = bbox.tolist()
                        elif not isinstance(bbox, list):
                            bbox = [list(point) for point in bbox]
                        dt_polys.append(bbox)
                    except Exception:
                        dt_polys.append([])

        # 딕셔너리 형식 (하위 호환)
        elif isinstance(raw_results, dict):
            dt_polys_raw = raw_results.get('dt_polys', [])
            rec_texts_raw = raw_results.get('rec_texts', raw_results.get('rec_text', []))
            rec_scores_raw = raw_results.get('rec_scores', raw_results.get('rec_score', []))

            for i in range(len(rec_texts_raw)):
                try:
                    text = str(rec_texts_raw[i]) if i < len(rec_texts_raw) else ""
                    score = float(rec_scores_raw[i]) if i < len(rec_scores_raw) else 0.0
                    bbox = dt_polys_raw[i] if i < len(dt_polys_raw) else []

                    if isinstance(bbox, np.ndarray):
                        bbox = bbox.tolist()
                    elif not isinstance(bbox, list):
                        bbox = [list(point) for point in bbox]

                    rec_texts.append(text)
                    rec_scores.append(score)
                    dt_polys.append(bbox)
                except Exception as e:
                    logger.warning(f"OCR 결과 변환 실패: {e}, index={i}")
                    continue

        logger.info(f"OCR 변환 완료: {len(rec_texts)}개 텍스트")
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
            result = self._predict_guarded(file_path)

            # PaddleOCR 3.x 결과를 OCRItem으로 변환
            item = self._convert_to_ocr_item(result)

            return OCRResultEnvelope(
                stage="ocr",
                data=OCRData(items=[item]),
                meta=OCRMeta(
                    items=len(item.rec_texts),
                    source="path",
                    lang=self.lang,
                    engine="PaddleOCR",
                ),
            )
        except Exception as e:
            logger.error(f"파일 OCR 실패: {e}")
            return None

    def run_ocr_from_nparray(
        self, image_array: np.ndarray
    ) -> Optional[OCRResultEnvelope]:
        """numpy 배열에서 OCR 실행

        Args:
            image_array: 이미지 numpy 배열 (RGB 또는 BGR)

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            result = self._predict_guarded(image_array)

            # PaddleOCR 3.x 결과를 OCRItem으로 변환
            item = self._convert_to_ocr_item(result)

            return OCRResultEnvelope(
                stage="ocr",
                data=OCRData(items=[item]),
                meta=OCRMeta(
                    items=len(item.rec_texts),
                    source="nparray",
                    lang=self.lang,
                    engine="PaddleOCR",
                ),
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
            # 바이트를 numpy 배열로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if cv_image is None:
                logger.error(
                    "이미지 디코딩 실패: 지원되지 않는 형식이거나 손상된 이미지"
                )
                return None

            return self.run_ocr_from_nparray(cv_image)

        except Exception as e:
            logger.error(f"바이트 OCR 실패: {e}")
            return None

    def run_ocr(
        self, image: Union[str, np.ndarray, Image.Image, bytes]
    ) -> Optional[OCRResultEnvelope]:
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
                stage="ocr",
                data=OCRData(
                    items=[OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])]
                ),
                meta=OCRMeta(
                    items=0, source="nparray", lang=self.lang, engine="PaddleOCR"
                ),
            )
        return result

    @property
    def is_gpu_enabled(self) -> bool:
        """GPU 사용 여부"""
        return self.use_gpu

    def get_device_info(self) -> dict:
        """디바이스 정보 반환"""
        info = {
            "engine": "PaddleOCR",
            "use_gpu": self.use_gpu,
            "requested_gpu": self._requested_gpu,
            "lang": self.lang,
        }

        try:
            import paddle

            info["paddle_version"] = paddle.__version__
            info["compiled_with_cuda"] = paddle.device.is_compiled_with_cuda()

            if self.use_gpu:
                info["gpu_count"] = paddle.device.cuda.device_count()
                if info["gpu_count"] > 0:
                    info["gpu_name"] = paddle.device.cuda.get_device_name(0)
        except ImportError:
            info["paddle_installed"] = False

        return info


__all__ = ["MyPaddleOCR"]

