import pytest
from app.services.ocr.paddle_ocr import MyPaddleOCR

def test_my_paddle_ocr_initialization():
    ocr = MyPaddleOCR(lang='en')
    assert ocr is not None
    assert ocr.lang == 'en'

def test_my_paddle_ocr_method_behavior():
    ocr = MyPaddleOCR(lang='en')
    # Assuming there is a method called process_image
    result = ocr.process_image('path/to/image.jpg')
    assert result is not None  # Replace with actual expected behavior

def test_my_paddle_ocr_error_handling():
    ocr = MyPaddleOCR(lang='en')
    with pytest.raises(AttributeError):
        ocr.some_method_that_causes_error()  # Replace with actual method that raises error