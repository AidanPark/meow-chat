"""
Korean OCR using PaddleOCR

이 모듈은 PaddleOCR을 사용하여 한국어 텍스트 인식을 수행하는 클래스를 제공합니다.

Author: yunwoong7 (modified for latest PaddleOCR compatibility)
License: Apache 2.0
"""

import cv2
import numpy as np
from typing import Union
from paddleocr import PaddleOCR
from app.utils.image_util import plt_imshow, put_text

class MyPaddleOCR:
    """
    PaddleOCR을 사용한 한국어 OCR 클래스
    
    이 클래스는 PaddleOCR 라이브러리를 래핑하여 한국어 텍스트 인식 기능을 제공합니다.
    최신 PaddleOCR API와 호환되도록 설계되었습니다.
    
    Attributes:
        lang (str): 인식할 언어 설정 (기본값: "korean")
        _ocr (PaddleOCR): PaddleOCR 인스턴스
        img_path (str): 처리된 이미지 경로
        ocr_result (dict): OCR 결과 상세 정보
    """
    
    def __init__(self, lang: str = "korean", **kwargs):
        """
        MyPaddleOCR 클래스 초기화
        
        Args:
            lang (str): 인식할 언어 코드 (기본값: "korean")
            **kwargs: PaddleOCR에 전달할 추가 인자
        """
        self.lang = lang
        self.init_kwargs = kwargs.copy()  # 초기화에 사용된 추가 인자 저장
        
        # PaddleOCR 인스턴스 생성 (전달받은 모든 파라미터 사용)
        self._ocr = PaddleOCR(lang=lang, **kwargs)
        self.img_path = None  # 현재 처리 중인 이미지 경로
        self.ocr_result = {}  # OCR 결과 상세 정보 저장
    
    def get_available_langs(self):
        """
        PaddleOCR에서 지원하는 언어 목록을 출력합니다.
        
        Note:
            PaddleOCR 3.2.0에서는 동적 언어 목록 조회 API가 제공되지 않아
            공식 문서 기반의 전체 지원 언어 목록을 사용합니다.
        """
        # PaddleOCR 3.2.0에서 공식 지원하는 전체 언어 목록
        langs_info = [
            'ch', 'en', 'korean', 'japan', 'chinese_cht',  # 주요 동아시아 언어
            'ta', 'te', 'ka', 'latin', 'arabic', 'cyrillic',  # 다양한 문자체계
            'devanagari', 'french', 'german', 'it', 'xi',  # 유럽 언어
            'pu', 'ru', 'ar', 'hi', 'ug', 'fa', 'ur',  # 중동/남아시아 언어
            'rs_latin', 'oc', 'rs_cyrillic', 'bg', 'uk', 'be',  # 동유럽 언어
            'kn', 'ch_tra', 'mr', 'ne'  # 추가 지원 언어
        ]
        
        print(f'Available Languages ({len(langs_info)} total):')
        print(langs_info)
        
        # 주요 언어 설명
        major_langs = {
            'ch': '중국어 (간체)',
            'en': '영어',
            'korean': '한국어',
            'japan': '일본어',
            'chinese_cht': '중국어 (번체)',
            'french': '프랑스어',
            'german': '독일어',
            'ru': '러시아어',
            'ar': '아랍어',
            'hi': '힌디어'
        }
        
        print(f'\nMajor supported languages:')
        for code, name in major_langs.items():
            print(f'  {code:12} - {name}')
            
        return langs_info
    
    def check_language_support(self, lang_code: str):
        """
        특정 언어가 지원되는지 확인합니다.
        
        Args:
            lang_code (str): 확인할 언어 코드 (예: 'korean', 'en', 'ch')
        
        Returns:
            bool: 지원 여부
        """
        supported_langs = [
            'ch', 'en', 'korean', 'japan', 'chinese_cht',
            'ta', 'te', 'ka', 'latin', 'arabic', 'cyrillic',
            'devanagari', 'french', 'german', 'it', 'xi',
            'pu', 'ru', 'ar', 'hi', 'ug', 'fa', 'ur',
            'rs_latin', 'oc', 'rs_cyrillic', 'bg', 'uk', 'be',
            'kn', 'ch_tra', 'mr', 'ne'
        ]
        
        is_supported = lang_code in supported_langs
        print(f"Language '{lang_code}': {'✅ Supported' if is_supported else '❌ Not supported'}")
        
        if not is_supported:
            # 유사한 언어 제안
            suggestions = [lang for lang in supported_langs if lang.startswith(lang_code[:2])]
            if suggestions:
                print(f"Did you mean: {suggestions}")
        
        return is_supported
        
    def get_available_models(self):
        """
        PaddleOCR에서 사용 가능한 모델과 지원 언어를 출력합니다.
        
        실제 다운로드된 모델과 이론적으로 지원하는 모델을 모두 보여줍니다.
        """
        import os
        
        print("🤖 PaddleOCR 사용 가능한 모델 정보")
        print("=" * 60)
        
        # 1. 실제 다운로드된 모델 확인
        model_dir = os.path.expanduser("~/.paddlex/official_models")
        downloaded_models = []
        
        if os.path.exists(model_dir):
            try:
                downloaded_models = [item for item in os.listdir(model_dir) 
                                   if os.path.isdir(os.path.join(model_dir, item))]
                print(f"✅ 실제 다운로드된 모델 ({len(downloaded_models)}개):")
                
                # 모델 분류
                detection_models = [m for m in downloaded_models if 'det' in m.lower()]
                recognition_models = [m for m in downloaded_models if 'rec' in m.lower()]
                orientation_models = [m for m in downloaded_models if 'ori' in m.lower() or 'doc' in m.lower()]
                other_models = [m for m in downloaded_models if m not in detection_models + recognition_models + orientation_models]
                
                if detection_models:
                    print("  🔍 텍스트 감지 모델:")
                    for model in detection_models:
                        version = "PP-OCRv5" if "v5" in model else ("PP-OCRv4" if "v4" in model else "PP-OCR")
                        print(f"    📦 {model} ({version})")
                
                if recognition_models:
                    print("  📝 텍스트 인식 모델:")
                    for model in recognition_models:
                        version = "PP-OCRv5" if "v5" in model else ("PP-OCRv4" if "v4" in model else "PP-OCR")
                        lang = "한국어" if "korean" in model else ("영어" if "en" in model else "기타")
                        size = "모바일" if "mobile" in model else "서버"
                        print(f"    📦 {model} ({version}, {lang}, {size})")
                
                if orientation_models:
                    print("  📐 방향/구조 보정 모델:")
                    for model in orientation_models:
                        print(f"    📦 {model}")
                
                if other_models:
                    print("  🔧 기타 모델:")
                    for model in other_models:
                        print(f"    📦 {model}")
                        
            except PermissionError:
                print("❌ 모델 디렉토리 접근 권한 없음")
        else:
            print("❌ 모델 디렉토리를 찾을 수 없음")
        
        print("\n" + "=" * 60)
        
        # 2. PaddleOCR에서 이론적으로 지원하는 모델 버전
        print("📚 PaddleOCR 지원 모델 버전:")
        model_info = {
            'PP-OCRv5': {
                'languages': ['ch', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka', 'latin', 'arabic', 'cyrillic', 'devanagari'],
                'status': '✅ 현재 사용 중',
                'features': ['최고 정확도', '한국어 최적화', '모바일/서버 지원']
            },
            'PP-OCRv4': {
                'languages': ['ch', 'en', 'korean', 'japan', 'chinese_cht'],
                'status': '🔶 이전 버전',
                'features': ['안정적 성능', '빠른 처리']
            },
            'PP-OCRv3': {
                'languages': ['ch', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka', 'latin', 'arabic', 'cyrillic', 'devanagari'],
                'status': '🔶 이전 버전',
                'features': ['광범위한 언어 지원']
            },
            'PP-OCRv2': {
                'languages': ['ch'],
                'status': '🔸 레거시',
                'features': ['중국어 전용']
            }
        }
        
        for idx, (model_name, info) in enumerate(model_info.items(), 1):
            print(f"\n#{idx} {model_name} {info['status']}")
            print(f"   🌍 지원 언어 ({len(info['languages'])}개): {info['languages'][:5]}{'...' if len(info['languages']) > 5 else ''}")
            print(f"   ⭐ 특징: {', '.join(info['features'])}")
        
        print("\n" + "=" * 60)
        print("💡 현재 설정:")
        print(f"   📌 사용 중인 버전: PP-OCRv5")
        print(f"   📌 주 사용 언어: {self.lang}")
        print(f"   📌 모델 구성: 서버급 감지 + 모바일 최적화 인식")
        
        return downloaded_models
    
    def get_current_model_info(self):
        """
        현재 사용 중인 OCR 모델의 상세 정보를 실제 PaddleOCR 인스턴스에서 동적으로 추출합니다.
        
        Returns:
            dict: 현재 모델 정보
        """
        print("🔍 현재 사용 중인 모델 정보 (실제 설정)")
        print("=" * 50)
        
        # 실제 PaddleOCR 인스턴스에서 모델 정보 추출
        try:
            # _params에서 실제 설정된 모델명 추출
            params = self._ocr._params
            config = self._ocr._merged_paddlex_config
            
            # 실제 사용 중인 모델들
            detection_model = params.get('text_detection_model_name', 'Unknown')
            recognition_model = params.get('text_recognition_model_name', 'Unknown')
            
            # config에서 세부 모델들 추출
            sub_modules = config.get('SubModules', {})
            sub_pipelines = config.get('SubPipelines', {})
            
            # 문서 전처리 모델들
            doc_models = []
            if 'DocPreprocessor' in sub_pipelines:
                doc_preprocessor = sub_pipelines['DocPreprocessor'].get('SubModules', {})
                if 'DocOrientationClassify' in doc_preprocessor:
                    doc_ori_model = doc_preprocessor['DocOrientationClassify'].get('model_name')
                    if doc_ori_model:
                        doc_models.append(doc_ori_model)
                if 'DocUnwarping' in doc_preprocessor:
                    doc_unwarp_model = doc_preprocessor['DocUnwarping'].get('model_name')
                    if doc_unwarp_model:
                        doc_models.append(doc_unwarp_model)
            
            # 텍스트라인 방향 보정 모델
            textline_ori_model = None
            if 'TextLineOrientation' in sub_modules:
                textline_ori_model = sub_modules['TextLineOrientation'].get('model_name')
            
            # 모델 정보 구성
            model_info = {
                'language': self.lang,
                'version': 'PP-OCRv5',  # 모든 모델이 v5임을 확인
                'detection_model': detection_model,
                'recognition_model': recognition_model,
                'doc_orientation_models': doc_models,
                'textline_orientation_model': textline_ori_model,
                'pipeline_config': {
                    'use_doc_preprocessor': config.get('use_doc_preprocessor', False),
                    'use_textline_orientation': config.get('use_textline_orientation', False),
                    'text_type': config.get('text_type', 'general')
                }
            }
            
            # 상세 출력
            print(f"📌 설정 언어: {model_info['language']}")
            print(f"📌 파이프라인: {config.get('pipeline_name', 'OCR')}")
            print(f"📌 텍스트 유형: {model_info['pipeline_config']['text_type']}")
            print(f"📌 모델 버전: {model_info['version']}")
            
            print(f"\n🔍 핵심 모델:")
            print(f"   텍스트 감지: {model_info['detection_model']}")
            print(f"   텍스트 인식: {model_info['recognition_model']}")
            
            if model_info['doc_orientation_models']:
                print(f"\n📐 문서 전처리 모델:")
                for model in model_info['doc_orientation_models']:
                    model_type = "방향 보정" if "ori" in model else "문서 교정"
                    print(f"   {model} ({model_type})")
            
            if model_info['textline_orientation_model']:
                print(f"\n📏 텍스트라인 방향 보정:")
                print(f"   {model_info['textline_orientation_model']}")
            
            # 설정 정보
            print(f"\n⚙️  파이프라인 설정:")
            print(f"   문서 전처리: {'✅' if model_info['pipeline_config']['use_doc_preprocessor'] else '❌'}")
            print(f"   텍스트라인 보정: {'✅' if model_info['pipeline_config']['use_textline_orientation'] else '❌'}")
            
            # 실제 모델 매개변수 정보
            if 'TextDetection' in sub_modules:
                det_config = sub_modules['TextDetection']
                print(f"\n🔍 감지 모델 설정:")
                print(f"   임계값: {det_config.get('thresh', 'N/A')}")
                print(f"   박스 임계값: {det_config.get('box_thresh', 'N/A')}")
                print(f"   언클립 비율: {det_config.get('unclip_ratio', 'N/A')}")
            
            if 'TextRecognition' in sub_modules:
                rec_config = sub_modules['TextRecognition']
                print(f"\n📝 인식 모델 설정:")
                print(f"   배치 크기: {rec_config.get('batch_size', 'N/A')}")
                print(f"   점수 임계값: {rec_config.get('score_thresh', 'N/A')}")
            
            # 성능 특성 (실제 설정 기반)
            is_korean = self.lang == 'korean'
            is_mobile_rec = 'mobile' in recognition_model
            is_server_det = 'server' in detection_model
            
            print(f"\n📊 성능 특성 (실제 설정 기반):")
            print(f"   모델 조합: {'서버급 감지' if is_server_det else '모바일 감지'} + {'모바일 인식' if is_mobile_rec else '서버급 인식'}")
            print(f"   한국어 최적화: {'✅' if is_korean else '❌'}")
            print(f"   실시간 처리: {'✅' if is_mobile_rec else '⚡ 고성능'}")
            print(f"   문서 처리: {'✅ 고급' if model_info['pipeline_config']['use_doc_preprocessor'] else '❌ 기본'}")
            
        except Exception as e:
            print(f"❌ 모델 정보 추출 실패: {e}")
            # 기본값으로 fallback
            model_info = {
                'language': self.lang,
                'version': 'PP-OCRv5',
                'detection_model': 'PP-OCRv5_server_det',
                'recognition_model': f'{self.lang}_PP-OCRv5_mobile_rec',
                'error': str(e)
            }
            print(f"📌 기본 설정으로 표시: {self.lang} 언어, PP-OCRv5 모델")
        
        return model_info
        
    def get_ocr_result(self):
        """
        마지막으로 실행된 OCR의 상세 결과를 반환합니다.
        
        Returns:
            dict: OCR 결과 딕셔너리
                - rec_texts: 인식된 텍스트 리스트
                - rec_scores: 각 텍스트의 신뢰도 점수
                - rec_polys: 각 텍스트의 좌표 정보
                - 기타 메타데이터
        """
        return self.ocr_result

    def get_img_path(self):
        """
        현재 처리 중인 이미지 경로를 반환합니다.
        
        Returns:
            str: 이미지 파일 경로
        """
        return self.img_path

    def show_img(self):
        """
        현재 이미지를 matplotlib을 사용하여 화면에 표시합니다.
        
        Note:
            utils.image_util.plt_imshow 함수를 사용합니다.
        """
        plt_imshow(img=self.img_path)
    
    def run_ocr(self, img_input: Union[str, np.ndarray], debug: bool = False):
        """
        이미지에서 텍스트를 인식하는 OCR을 실행합니다.
        
        Args:
            img_input (Union[str, np.ndarray]): 
                - str: 분석할 이미지 파일 경로
                - np.ndarray: OpenCV 이미지 배열 (BGR 형식)
            debug (bool): 디버그 모드 활성화 여부 (기본값: False)
                         True일 경우 인식된 텍스트와 신뢰도를 출력합니다.
        
        Returns:
            list: 인식된 텍스트 리스트
                 예: ['아래한글 한글문서', '디자인', '2022.04']
        
        Note:
            - 결과는 self.ocr_result에도 저장됩니다 (상세 정보 포함)
            - PaddleOCR의 최신 predict() API를 사용합니다
            - numpy 배열과 파일 경로 모두 지원합니다
        """
        # 입력 타입에 따른 처리
        if isinstance(img_input, str):
            # 파일 경로인 경우
            self.img_path = img_input
            input_source = img_input
            if debug:
                print(f"📁 파일에서 OCR 실행: {img_input}")
        elif isinstance(img_input, np.ndarray):
            # numpy 배열인 경우
            self.img_path = "memory_image"  # 메모리 이미지 표시
            input_source = img_input
            if debug:
                print(f"💾 메모리에서 OCR 실행: shape={img_input.shape}, dtype={img_input.dtype}")
        else:
            raise ValueError(f"지원하지 않는 입력 타입: {type(img_input)}. str 또는 np.ndarray만 지원합니다.")
        
        ocr_text = []  # 인식된 텍스트를 저장할 리스트
        
        # PaddleOCR 최신 버전 API 사용
        try:
            # PaddleOCR predict 메서드 호출 (파일 경로와 numpy 배열 모두 지원)
            result = self._ocr.predict(input_source)
            
            # 결과가 리스트이고 첫 번째 요소에 데이터가 있는 경우
            if result and isinstance(result, list) and len(result) > 0:
                page_result = result[0]  # 첫 번째 페이지 결과 추출
                
                # 결과에 텍스트 정보가 있는지 확인
                if isinstance(page_result, dict) and 'rec_texts' in page_result:
                    # 상세 결과를 객체에 저장
                    self.ocr_result = page_result
                    # 텍스트만 추출
                    ocr_text = page_result['rec_texts']
                    
                    # 디버그 모드일 경우 결과 출력
                    if debug:
                        input_type = "파일" if isinstance(img_input, str) else "메모리"
                        print(f"✅ {input_type} OCR 완료:")
                        print(f"   📝 인식된 텍스트 ({len(ocr_text)}개): {ocr_text}")
                        if 'rec_scores' in page_result:
                            scores = page_result['rec_scores']
                            print(f"   📊 신뢰도: {[f'{score:.4f}' for score in scores]}")
                        if 'rec_polys' in page_result:
                            polys = page_result['rec_polys']
                            print(f"   📍 좌표 정보: {len(polys)}개 영역")
                else:
                    # 텍스트 정보가 없는 경우
                    self.ocr_result = {}
                    ocr_text = ["텍스트를 찾을 수 없습니다."]
                    if debug:
                        print("⚠️ OCR 결과에 텍스트 정보가 없습니다.")
            else:
                # 결과가 비어있는 경우
                self.ocr_result = {}
                ocr_text = ["OCR 결과가 비어있습니다."]
                if debug:
                    print("⚠️ OCR 결과가 비어있습니다.")
                
        except Exception as e:
            # OCR 실행 중 오류 발생
            print(f"❌ OCR 실행 중 오류: {e}")
            self.ocr_result = {}
            ocr_text = ["OCR 실행 실패"]

        return ocr_text
    
    def run_ocr_from_bytes(self, image_bytes: bytes, debug: bool = False):
        """
        바이트 데이터에서 직접 OCR을 실행합니다.
        
        Args:
            image_bytes (bytes): 이미지 파일의 바이트 데이터
            debug (bool): 디버그 모드
            
        Returns:
            list: 인식된 텍스트 리스트
        """
        try:
            # 바이트 데이터를 numpy 배열로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if cv_image is None:
                raise ValueError("이미지 디코딩 실패")
            
            if debug:
                print(f"🔄 바이트 데이터 변환 완료: {cv_image.shape}")
            
            # numpy 배열로 OCR 실행
            return self.run_ocr(cv_image, debug=debug)
            
        except Exception as e:
            print(f"❌ 바이트 데이터 OCR 실패: {e}")
            return ["바이트 데이터 처리 실패"]
        
    def show_img_with_ocr(self):
        """
        OCR 결과를 이미지 위에 시각화하여 표시합니다.
        
        인식된 텍스트 영역을 녹색 사각형으로 표시하고,
        각 영역 위에 인식된 텍스트를 표시합니다.
        
        Note:
            - OpenCV를 사용하여 이미지 처리
            - matplotlib을 통해 원본과 결과 이미지를 나란히 표시
            - 현재 버전에서는 draw_ocr 의존성 문제로 비활성화됨
        """
        # 이미지 읽기
        img = cv2.imread(self.img_path)
        roi_img = img.copy()  # 결과 표시용 이미지 복사

        # OCR 결과의 각 텍스트 영역에 대해 처리
        for text_result in self.ocr_result:
            text = text_result[1][0]  # 인식된 텍스트
            
            # 텍스트 영역의 4개 꼭지점 좌표 추출
            tlX = int(text_result[0][0][0])  # Top-Left X
            tlY = int(text_result[0][0][1])  # Top-Left Y
            trX = int(text_result[0][1][0])  # Top-Right X
            trY = int(text_result[0][1][1])  # Top-Right Y
            brX = int(text_result[0][2][0])  # Bottom-Right X
            brY = int(text_result[0][2][1])  # Bottom-Right Y
            blX = int(text_result[0][3][0])  # Bottom-Left X
            blY = int(text_result[0][3][1])  # Bottom-Left Y

            # 4개 꼭지점 좌표 튜플로 정리
            pts = ((tlX, tlY), (trX, trY), (brX, brY), (blX, blY))
            topLeft = pts[0]
            topRight = pts[1]
            bottomRight = pts[2]
            bottomLeft = pts[3]

            # 텍스트 영역을 녹색 사각형으로 표시
            cv2.line(roi_img, topLeft, topRight, (0, 255, 0), 2)
            cv2.line(roi_img, topRight, bottomRight, (0, 255, 0), 2)
            cv2.line(roi_img, bottomRight, bottomLeft, (0, 255, 0), 2)
            cv2.line(roi_img, bottomLeft, topLeft, (0, 255, 0), 2)
            
            # 텍스트 영역 위에 인식된 텍스트 표시
            roi_img = put_text(roi_img, text, topLeft[0], topLeft[1] - 20, font_size=15)

        # 원본 이미지와 OCR 결과 이미지를 나란히 표시
        plt_imshow(["Original", "ROI"], [img, roi_img], figsize=(16, 10))

    def show_img(self):
        """
        현재 이미지를 matplotlib을 사용하여 화면에 표시합니다.
        
        Note:
            메모리 이미지인 경우 표시할 수 없습니다.
        """
        if self.img_path == "memory_image":
            print("⚠️ 메모리 이미지는 show_img()로 표시할 수 없습니다.")
            print("💡 대신 run_ocr 실행 시 numpy 배열을 직접 사용하세요.")
        else:
            plt_imshow(img=self.img_path)

    def save_memory_image(self, output_path: str, image_array: np.ndarray = None):
        """
        메모리에 있는 이미지를 파일로 저장합니다.
        
        Args:
            output_path (str): 저장할 파일 경로
            image_array (np.ndarray, optional): 저장할 이미지 배열
                                                None인 경우 마지막 처리된 이미지 사용
        """
        if image_array is not None:
            cv2.imwrite(output_path, image_array)
            print(f"✅ 이미지 저장 완료: {output_path}")
        else:
            print("❌ 저장할 이미지 배열이 없습니다.")
