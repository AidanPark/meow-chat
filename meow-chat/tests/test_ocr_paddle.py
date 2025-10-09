class TestMyPaddleOCR:
    def test_initialization(self):
        ocr = MyPaddleOCR(lang='en')
        assert ocr is not None

    def test_process_image(self):
        ocr = MyPaddleOCR(lang='en')
        result = ocr.process_image('path/to/image.jpg')
        assert isinstance(result, dict)

    def test_handle_attribute_error(self):
        try:
            ocr = MyPaddleOCR(lang='invalid_lang')
            ocr.process_image('path/to/image.jpg')
        except AttributeError as e:
            assert str(e) == "'paddle.base.libpaddle.AnalysisConfig' object has no attribute 'set_optimization_level'"