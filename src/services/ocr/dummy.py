"""더미 OCR 구현 (테스트용)"""

from PIL import Image

from .base import BaseOCRService, OCRResult


class DummyOCR(BaseOCRService):
    """테스트용 더미 OCR 서비스"""

    def extract_text(self, image: Image.Image) -> OCRResult:
        """더미 텍스트 반환

        Args:
            image: PIL Image 객체

        Returns:
            OCRResult 객체
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

        return OCRResult(
            text=dummy_text,
            confidence=1.0,
            metadata={"source": "dummy", "image_size": image.size},
        )

