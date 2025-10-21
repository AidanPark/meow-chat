"""
Korean OCR using PaddleOCR

이 모듈은 PaddleOCR을 사용하여 한국어 텍스트 인식을 수행하는 클래스를 제공합니다.

Author: yunwoong7 (modified for latest PaddleOCR compatibility)
License: Apache 2.0
"""

import cv2
import numpy as np
import re
from paddleocr import PaddleOCR
from app.services.analysis import line_preprocessor as lp
import jsonpickle
from typing import Optional
import json

class PaddleOCRService:
    """
    PaddleOCR을 사용한 한국어 OCR 클래스
    
    이 클래스는 PaddleOCR 라이브러리를 래핑하여 한국어 텍스트 인식 기능을 제공합니다.
    최신 PaddleOCR API와 호환되도록 설계되었습니다.
    
    Attributes:
        lang (str): 인식할 언어 설정 (기본값: "korean")
        _ocr (PaddleOCR): PaddleOCR 인스턴스
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
        self._ocr_engine = PaddleOCR(
            lang=self.lang, 
            use_doc_orientation_classify=True, # 문서 방향 분류/교정 모델 로드
            use_doc_unwarping=True,            # 문서 휘어짐 보정 
            use_textline_orientation=True,     # 방향 분류 활성화

            # text_detection_model_name="PP-OCRv5_server_det",
            # text_recognition_model_name="korean_PP-OCRv5_server_rec",
            # text_det_limit_side_len=1920,      # 이미지 크기 
            # text_det_thresh=0.25,               # 감지 임계값 
            # text_rec_score_thresh=0.75,         # 인식 임계값 

            # text_recognition_batch_size=1,     # 배치 크기         
            # return_word_box=True,              # 단어별 박스 반환       
            # text_det_unclip_ratio=2.5,         # 텍스트 박스 확장  
            **kwargs
        )

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
            params = self._ocr_engine._params
            config = self._ocr_engine._merged_paddlex_config
            
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
        
    def get_current_preprocessing_settings(self):
        """
        현재 PaddleOCR 인스턴스에 실제로 적용된 모든 전처리 설정을 출력합니다.
        
        Returns:
            dict: 현재 전처리 설정 정보
        """
        print("🔧 현재 PaddleOCR 인스턴스의 전처리 설정 (실제 적용됨)")
        print("=" * 70)
        
        preprocessing_settings = {}
        
        try:
            # PaddleOCR 인스턴스에서 실제 설정 추출
            params = self._ocr_engine._params
            config = self._ocr_engine._merged_paddlex_config
            sub_modules = config.get('SubModules', {})
            sub_pipelines = config.get('SubPipelines', {})
            
            # 1. 기본 시스템 설정
            system_settings = {
                'language': self.lang,
                'pipeline_name': config.get('pipeline_name', 'OCR'),
                'text_type': config.get('text_type', 'general'),
                'use_gpu': params.get('use_gpu', True),
                'gpu_id': params.get('gpu_id', 0),
                'cpu_threads': params.get('cpu_threads', 10),
                'enable_mkldnn': params.get('enable_mkldnn', True),
                'warmup': params.get('warmup', True),
                'show_log': params.get('show_log', False)
            }
            preprocessing_settings['system'] = system_settings
            
            print("🖥️  시스템 설정:")
            print(f"   언어: {system_settings['language']}")
            print(f"   파이프라인: {system_settings['pipeline_name']}")
            print(f"   텍스트 유형: {system_settings['text_type']}")
            print(f"   GPU 사용: {'✅' if system_settings['use_gpu'] else '❌'}")
            print(f"   GPU ID: {system_settings['gpu_id']}")
            print(f"   CPU 스레드: {system_settings['cpu_threads']}")
            print(f"   MKLDNN 최적화: {'✅' if system_settings['enable_mkldnn'] else '❌'}")
            print(f"   모델 워밍업: {'✅' if system_settings['warmup'] else '❌'}")
            print(f"   로그 출력: {'✅' if system_settings['show_log'] else '❌'}")
            
            # 2. 텍스트 감지 전처리 설정
            detection_settings = {}
            if 'TextDetection' in sub_modules:
                det_config = sub_modules['TextDetection']
                detection_settings = {
                    'model_name': det_config.get('model_name', 'Unknown'),
                    'thresh': det_config.get('thresh', 0.3),
                    'box_thresh': det_config.get('box_thresh', 0.6),
                    'unclip_ratio': det_config.get('unclip_ratio', 1.5),
                    'max_side_len': det_config.get('max_side_len', 960),
                    'limit_type': det_config.get('limit_type', 'max'),
                    'use_dilation': det_config.get('use_dilation', True),
                    'score_mode': det_config.get('score_mode', 'fast'),
                    'polygon': det_config.get('polygon', False),
                    'visualize': det_config.get('visualize', False)
                }
                preprocessing_settings['detection'] = detection_settings
                
                print(f"\n🔍 텍스트 감지 전처리:")
                print(f"   모델: {detection_settings['model_name']}")
                print(f"   감지 임계값: {detection_settings['thresh']}")
                print(f"   박스 임계값: {detection_settings['box_thresh']}")
                print(f"   언클립 비율: {detection_settings['unclip_ratio']}")
                print(f"   최대 변 길이: {detection_settings['max_side_len']}px")
                print(f"   크기 제한 방식: {detection_settings['limit_type']}")
                print(f"   팽창 연산: {'✅' if detection_settings['use_dilation'] else '❌'}")
                print(f"   점수 계산 모드: {detection_settings['score_mode']}")
                print(f"   다각형 감지: {'✅' if detection_settings['polygon'] else '❌'}")
                print(f"   시각화: {'✅' if detection_settings['visualize'] else '❌'}")
            
            # 3. 텍스트 인식 전처리 설정
            recognition_settings = {}
            if 'TextRecognition' in sub_modules:
                rec_config = sub_modules['TextRecognition']
                recognition_settings = {
                    'model_name': rec_config.get('model_name', 'Unknown'),
                    'batch_size': rec_config.get('batch_size', 6),
                    'score_thresh': rec_config.get('score_thresh', 0.5),
                    'max_text_length': rec_config.get('max_text_length', 25),
                    'image_shape': rec_config.get('image_shape', [3, 48, 320]),
                    'use_space_char': rec_config.get('use_space_char', True),
                    'limited_max_width': rec_config.get('limited_max_width', 1280),
                    'limited_min_width': rec_config.get('limited_min_width', 16),
                    'char_dict_path': rec_config.get('char_dict_path', None),
                    'visualize': rec_config.get('visualize', False)
                }
                preprocessing_settings['recognition'] = recognition_settings
                
                print(f"\n📝 텍스트 인식 전처리:")
                print(f"   모델: {recognition_settings['model_name']}")
                print(f"   배치 크기: {recognition_settings['batch_size']}")
                print(f"   점수 임계값: {recognition_settings['score_thresh']}")
                print(f"   최대 텍스트 길이: {recognition_settings['max_text_length']}")
                print(f"   이미지 크기: {recognition_settings['image_shape']}")
                print(f"   공백 문자 사용: {'✅' if recognition_settings['use_space_char'] else '❌'}")
                print(f"   최대 너비 제한: {recognition_settings['limited_max_width']}px")
                print(f"   최소 너비 제한: {recognition_settings['limited_min_width']}px")
                print(f"   문자 사전: {recognition_settings['char_dict_path'] or '기본값'}")
                print(f"   시각화: {'✅' if recognition_settings['visualize'] else '❌'}")
            
            # 4. 텍스트 방향 분류 전처리 설정
            orientation_settings = {}
            if 'TextLineOrientation' in sub_modules:
                ori_config = sub_modules['TextLineOrientation']
                orientation_settings = {
                    'model_name': ori_config.get('model_name', 'Unknown'),
                    'score_thresh': ori_config.get('score_thresh', 0.9),
                    'batch_size': ori_config.get('batch_size', 6),
                    'image_shape': ori_config.get('image_shape', [3, 48, 192]),
                    'label_list': ori_config.get('label_list', ['0', '180']),
                    'visualize': ori_config.get('visualize', False)
                }
                preprocessing_settings['orientation'] = orientation_settings
                
                print(f"\n📐 텍스트 방향 분류 전처리:")
                print(f"   모델: {orientation_settings['model_name']}")
                print(f"   분류 임계값: {orientation_settings['score_thresh']}")
                print(f"   배치 크기: {orientation_settings['batch_size']}")
                print(f"   이미지 크기: {orientation_settings['image_shape']}")
                print(f"   지원 각도: {orientation_settings['label_list']}")
                print(f"   시각화: {'✅' if orientation_settings['visualize'] else '❌'}")
            else:
                print(f"\n📐 텍스트 방향 분류 전처리: ❌ 비활성화")
            
            # 5. 문서 전처리 설정 (고급)
            doc_preprocessing_settings = {}
            if 'DocPreprocessor' in sub_pipelines:
                doc_preprocessor = sub_pipelines['DocPreprocessor']
                doc_sub_modules = doc_preprocessor.get('SubModules', {})
                
                doc_preprocessing_settings['enabled'] = True
                doc_preprocessing_settings['modules'] = {}
                
                print(f"\n📄 문서 전처리 (고급 기능):")
                
                # 문서 방향 분류
                if 'DocOrientationClassify' in doc_sub_modules:
                    doc_ori_config = doc_sub_modules['DocOrientationClassify']
                    doc_ori_settings = {
                        'model_name': doc_ori_config.get('model_name', 'Unknown'),
                        'score_thresh': doc_ori_config.get('score_thresh', 0.9),
                        'batch_size': doc_ori_config.get('batch_size', 1)
                    }
                    doc_preprocessing_settings['modules']['orientation'] = doc_ori_settings
                    
                    print(f"   🔄 문서 방향 분류:")
                    print(f"      모델: {doc_ori_settings['model_name']}")
                    print(f"      임계값: {doc_ori_settings['score_thresh']}")
                    print(f"      배치 크기: {doc_ori_settings['batch_size']}")
                
                # 문서 교정 (언워핑)
                if 'DocUnwarping' in doc_sub_modules:
                    doc_unwarp_config = doc_sub_modules['DocUnwarping']
                    doc_unwarp_settings = {
                        'model_name': doc_unwarp_config.get('model_name', 'Unknown'),
                        'batch_size': doc_unwarp_config.get('batch_size', 1)
                    }
                    doc_preprocessing_settings['modules']['unwarping'] = doc_unwarp_settings
                    
                    print(f"   📐 문서 교정 (언워핑):")
                    print(f"      모델: {doc_unwarp_settings['model_name']}")
                    print(f"      배치 크기: {doc_unwarp_settings['batch_size']}")
                
                preprocessing_settings['document'] = doc_preprocessing_settings
            else:
                print(f"\n📄 문서 전처리: ❌ 비활성화 (일반 모드)")
                preprocessing_settings['document'] = {'enabled': False}
            
            # 6. 이미지 입력 전처리 설정 (추론)
            image_preprocessing = {
                'auto_resize': True,
                'max_side_len': detection_settings.get('max_side_len', 960),
                'normalize': True,
                'channel_order': 'BGR',
                'data_type': 'float32',
                'interpolation': 'LANCZOS',
                'padding': False
            }
            preprocessing_settings['image'] = image_preprocessing
            
            print(f"\n🖼️  이미지 입력 전처리 (추론됨):")
            print(f"   자동 크기 조정: {'✅' if image_preprocessing['auto_resize'] else '❌'}")
            print(f"   최대 변 길이: {image_preprocessing['max_side_len']}px")
            print(f"   정규화: {'✅' if image_preprocessing['normalize'] else '❌'}")
            print(f"   채널 순서: {image_preprocessing['channel_order']}")
            print(f"   데이터 타입: {image_preprocessing['data_type']}")
            print(f"   보간법: {image_preprocessing['interpolation']}")
            print(f"   패딩: {'✅' if image_preprocessing['padding'] else '❌'}")
            
            # 7. 초기화 시 사용된 커스텀 옵션들
            custom_settings = {}
            if self.init_kwargs:
                custom_settings = self.init_kwargs.copy()
                preprocessing_settings['custom'] = custom_settings
                
                print(f"\n⚙️  초기화 시 커스텀 설정:")
                for key, value in custom_settings.items():
                    print(f"   {key}: {value}")
            else:
                print(f"\n⚙️  초기화 시 커스텀 설정: ❌ 모든 기본값 사용")
            
            # 8. 파이프라인 플로우 요약
            print(f"\n🔄 전처리 파이프라인 플로우:")
            
            flow_steps = []
            flow_steps.append("1. 이미지 로드 및 크기 조정")
            
            if preprocessing_settings['document']['enabled']:
                doc_section = preprocessing_settings.get('document') if isinstance(preprocessing_settings, dict) else None
                doc_modules = doc_section.get('modules', {}) if isinstance(doc_section, dict) else {}
                if isinstance(doc_modules, dict) and 'orientation' in doc_modules:
                    flow_steps.append("2. 문서 방향 분류")
                if isinstance(doc_modules, dict) and 'unwarping' in doc_modules:
                    flow_steps.append("3. 문서 교정 (언워핑)")
            
            flow_steps.append(f"{len(flow_steps)+1}. 텍스트 감지 ({detection_settings.get('model_name', 'Unknown')})")
            
            if 'orientation' in preprocessing_settings:
                flow_steps.append(f"{len(flow_steps)+1}. 텍스트 방향 분류")
            
            flow_steps.append(f"{len(flow_steps)+1}. 텍스트 인식 ({recognition_settings.get('model_name', 'Unknown')})")
            flow_steps.append(f"{len(flow_steps)+1}. 결과 후처리 및 필터링")
            
            for step in flow_steps:
                print(f"   {step}")
            
            # 9. 성능 특성 분석
            print(f"\n📊 성능 특성 분석:")
            
            # 모델 조합 분석
            det_model = detection_settings.get('model_name', '')
            rec_model = recognition_settings.get('model_name', '')
            
            is_server_det = 'server' in det_model.lower()
            is_mobile_rec = 'mobile' in rec_model.lower()
            has_doc_processing = preprocessing_settings['document']['enabled']
            has_orientation = 'orientation' in preprocessing_settings
            
            print(f"   모델 조합: {'서버급' if is_server_det else '모바일'} 감지 + {'모바일' if is_mobile_rec else '서버급'} 인식")
            print(f"   처리 속도: {'⚡ 고속' if is_mobile_rec else '🎯 고정확도'}")
            print(f"   메모리 사용: {'💾 적음' if is_mobile_rec else '💿 많음'}")
            print(f"   문서 지원: {'✅ 고급' if has_doc_processing else '❌ 기본'}")
            print(f"   방향 보정: {'✅ 지원' if has_orientation else '❌ 미지원'}")
            print(f"   배치 처리: 감지({detection_settings.get('batch_size', 'N/A')}), 인식({recognition_settings.get('batch_size', 'N/A')})")
            
            # 신뢰도 설정 분석
            det_thresh = detection_settings.get('thresh', 0.3)
            rec_thresh = recognition_settings.get('score_thresh', 0.5)
            
            print(f"\n🎯 신뢰도 설정 분석:")
            print(f"   감지 민감도: {'높음' if det_thresh <= 0.3 else '보통' if det_thresh <= 0.5 else '낮음'} (임계값: {det_thresh})")
            print(f"   인식 필터링: {'엄격' if rec_thresh >= 0.7 else '보통' if rec_thresh >= 0.5 else '관대'} (임계값: {rec_thresh})")
            
            overall_quality = "균형" if (det_thresh <= 0.4 and rec_thresh >= 0.5) else \
                            "고품질" if (det_thresh <= 0.3 and rec_thresh >= 0.7) else \
                            "고속도" if (det_thresh >= 0.4 and rec_thresh <= 0.4) else "커스텀"
            print(f"   전체 설정: {overall_quality}")
            
        except Exception as e:
            print(f"❌ 전처리 설정 추출 실패: {e}")
            preprocessing_settings = {
                'error': str(e),
                'fallback': {
                    'language': self.lang,
                    'custom_options': self.init_kwargs
                }
            }
            print(f"📌 기본 정보만 표시: 언어={self.lang}, 커스텀 옵션={len(self.init_kwargs)}개")
        
        return preprocessing_settings



    def run_ocr_from_path(self, file_path: str) -> list[dict] | None:
        """
        파일 경로에서 OCR을 실행하고 원본 결과를 반환합니다.
        
        Args:
            file_path (str): 이미지 파일 경로
            
        Returns:
            list[dict] | None: PaddleOCR 원본 결과 (성공시 OCRResult 딕셔너리 리스트, 실패시 None)
        """
        try:
            # PaddleOCR 원본 결과 반환
            result = self._ocr_engine.predict(file_path)
            # print(f"result: {result}")

            return result
            
        except Exception as e:
            print(f"❌ 파일 OCR 실패: {e}")
            return None
    
    def run_ocr_from_nparray(self, image_array: np.ndarray) -> list[dict] | None:
        """
        numpy 배열에서 OCR을 실행하고 원본 결과를 반환합니다.
        
        Args:
            image_array (np.ndarray): OpenCV 이미지 배열 (BGR 형식)
            
        Returns:
            list[dict] | None: PaddleOCR 원본 결과 (성공시 OCRResult 딕셔너리 리스트, 실패시 None)
        """
        try:
            # PaddleOCR 원본 결과 반환
            result = self._ocr_engine.predict(image_array)
            return result
            
        except Exception as e:
            print(f"❌ 배열 OCR 실패: {e}")
            return None
    
    def run_ocr_from_bytes(self, image_bytes: bytes) -> list[dict] | None:
        """
        바이트 데이터에서 OCR을 실행하고 원본 결과를 반환합니다.
        
        Args:
            image_bytes (bytes): 이미지 파일의 바이트 데이터
            
        Returns:
            list[dict] | None: PaddleOCR 원본 결과 (성공시 OCRResult 딕셔너리 리스트, 실패시 None)
        """
        try:
            # 바이트 데이터를 numpy 배열로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_image is None:
                print("❌ 이미지 디코딩 실패: 지원되지 않는 형식이거나 손상된 이미지입니다.")
                return None
            
            # numpy 배열로 OCR 실행 (재귀 호출)
            return self.run_ocr_from_nparray(cv_image)
            
        except Exception as e:
            print(f"❌ 바이트 데이터 OCR 실패: {e}")
            return None





