"""더미 OCR 구현 (테스트용)"""

from PIL import Image

from src.models.envelopes import OCRData, OCRItem, OCRMeta, OCRResultEnvelope
from .base import BaseOCRService


class DummyOCR(BaseOCRService):
    """테스트용 더미 OCR 서비스"""

    def extract_text(self, image: Image.Image) -> OCRResultEnvelope:
        """더미 텍스트 반환

        Args:
            image: PIL Image 객체

        Returns:
            OCRResultEnvelope 객체
        """
        dummy_text = """
[더미 OCR 결과]

고양이 건강검진 결과지

환자명: 나비
품종: 코리안 숏헤어
나이: 3세
성별: 중성화 암컷

검진 항목:
- 체중: 4.2kg
- 체온: 38.5°C
- 심박수: 180회/분

혈액 검사:
- WBC: 8.5 (정상)
- RBC: 7.2 (정상)
- ALT: 45 (정상)
- BUN: 25 (정상)
- CRE: 1.2 (정상)

소견:
전반적으로 건강 상태 양호. 
정기적인 검진 권장.

담당 수의사: 김냥이
검진 날짜: 2024-12-20
""".strip()

        # 단순 텍스트만 - 상세 위치 정보 없음
        item = OCRItem(
            rec_texts=[dummy_text],
            rec_scores=[1.0],
            dt_polys=[],  # 더미는 위치 정보 없음
        )

        return OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(
                items=1,
                source='nparray',
                lang='korean',
                engine='DummyOCR'
            )
        )
