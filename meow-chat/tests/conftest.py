import pytest

@pytest.fixture
def my_paddle_ocr():
    from app.services.ocr.paddle_ocr import MyPaddleOCR
    return MyPaddleOCR(lang='en')

def test_my_paddle_ocr_initialization(my_paddle_ocr):
    assert my_paddle_ocr is not None

def test_my_paddle_ocr_method(my_paddle_ocr):
    # Add specific method tests here
    pass