"""
Korean OCR using PaddleOCR

이 모듈은 PaddleOCR을 사용하여 한국어 텍스트 인식을 수행하는 클래스를 제공합니다.

Author: yunwoong7 (modified for latest PaddleOCR compatibility)
License: Apache 2.0
"""

import cv2
import numpy as np
from paddleocr import PaddleOCR
import jsonpickle
import numpy as np

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
            # text_det_thresh=0.2,               # 감지 임계값 
            # text_rec_score_thresh=0.7,         # 인식 임계값 
            # text_recognition_batch_size=1,     # 배치 크기 
            # text_det_limit_side_len=1600,      # 이미지 크기 
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
                if 'orientation' in preprocessing_settings['document']['modules']:
                    flow_steps.append("2. 문서 방향 분류")
                if 'unwarping' in preprocessing_settings['document']['modules']:
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
            
            # numpy 배열로 OCR 실행 (재귀 호출)
            return self.run_ocr_from_nparray(cv_image)
            
        except Exception as e:
            print(f"❌ 바이트 데이터 OCR 실패: {e}")
            return None




    def extract_text_with_confidence(self, ocr_result) -> list[dict[str, str | float | None]]:
        """
        OCR 결과에서 텍스트와 신뢰도를 추출하여 리스트로 반환
        
        Args:
            ocr_result: OCR 결과 객체 또는 딕셔너리
            
        Returns:
            list[dict[str, str | float | None]]: [{"text": str, "confidence": float | None}, ...] 형태의 리스트
            데이터 무결성 오류 시 빈 리스트 반환
        """
        # rec_texts 속성 확인
        if hasattr(ocr_result, 'rec_texts'):
            rec_texts = ocr_result.rec_texts
        elif isinstance(ocr_result, dict) and 'rec_texts' in ocr_result:
            rec_texts = ocr_result['rec_texts']
        else:
            print("❌ rec_texts를 찾을 수 없습니다.")
            return []
        
        # rec_scores 속성 확인 (한 번만)
        rec_scores = None
        if hasattr(ocr_result, 'rec_scores'):
            rec_scores = ocr_result.rec_scores
        elif isinstance(ocr_result, dict) and 'rec_scores' in ocr_result:
            rec_scores = ocr_result['rec_scores']
        else:
            print("❌ rec_scores를 찾을 수 없습니다.")
            return []
        
        # rec_texts와 rec_scores 길이가 같다면 zip으로 함께 처리
        if rec_scores and len(rec_texts) == len(rec_scores):
            # 결과 리스트 생성
            result_list = []
            for text, confidence in zip(rec_texts, rec_scores):
                result_list.append({
                    "text": text,
                    "confidence": round(float(confidence), 2)
                })
            return result_list    
        else:
            # 길이가 다르거나 rec_scores가 없으면 [] 반환
            return []

    def convert_to_json(self, result, pretty: bool = True):
        """jsonpickle을 사용한 JSON 변환"""
        try:
            # jsonpickle은 numpy 배열, 복잡한 객체 모두 처리
            json_string = jsonpickle.encode(
                result, 
                unpicklable=False,  # 순수 JSON만 생성
                make_refs=False     # 참조 제거
            )
            
            if pretty:
                import json
                parsed = json.loads(json_string)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            
            return json_string
            
        except Exception as e:
            print(f"❌ jsonpickle 변환 실패: {e}")
            return json.dumps({"error": str(e)})

    def convert_to_structured_json(self, result, pretty: bool = True):
        """
        OCR 결과를 텍스트별로 구조화된 JSON으로 변환
        
        Args:
            result: run_ocr_from_* 메서드의 반환값
            pretty (bool): 들여쓰기 적용 여부
            
        Returns:
            str: 구조화된 JSON 문자열
            
        Example:
            [
                {
                    "rec_text": "안녕하세요",
                    "rec_score": 0.9876,
                    "rec_poly": [[100, 50], [200, 50], [200, 80], [100, 80]],
                    "dt_poly": [[99.5, 49.8], [201.2, 50.1], [200.9, 80.3], [99.7, 79.9]],
                    "dt_score": 0.9543,
                    "ori_poly": [[100, 50], [200, 50], [200, 80], [100, 80]],
                    "ori_scores": 0.9234
                },
                ...
            ]
        """
        try:
            if not result or len(result) == 0:
                return "[]"
            
            page_result = result[0]
            
            # PaddleOCR 3.2.0 결과 구조 처리
            if isinstance(page_result, dict):
                texts = page_result.get('rec_texts', [])
                rec_scores = page_result.get('rec_scores', [])
                rec_polys = page_result.get('rec_polys', [])
                dt_polys = page_result.get('dt_polys', [])
                dt_scores = page_result.get('dt_scores', [])
                ori_polys = page_result.get('ori_polys', [])
                ori_scores = page_result.get('ori_scores', [])
            else:
                # 구버전 호환성: [[좌표, (텍스트, 신뢰도)], ...]
                texts = []
                rec_scores = []
                rec_polys = []
                dt_polys = []
                dt_scores = []
                ori_polys = []
                ori_scores = []
                
                for item in page_result:
                    if len(item) >= 2:
                        dt_polys.append(item[0])
                        rec_polys.append(item[0])  # 구버전에서는 동일
                        if isinstance(item[1], tuple):
                            texts.append(item[1][0])
                            rec_scores.append(item[1][1])
                        else:
                            texts.append(str(item[1]))
                            rec_scores.append(0.0)
                        
                        # 구버전에서는 추가 정보가 없으므로 기본값
                        dt_scores.append(0.0)
                        ori_polys.append(item[0])
                        ori_scores.append(0.0)
            
            # 텍스트별 구조화된 데이터 생성
            structured_data = []
            
            # 모든 배열의 최대 길이 계산
            max_length = max(
                len(texts), len(rec_scores), len(rec_polys),
                len(dt_polys), len(dt_scores), len(ori_polys), len(ori_scores)
            )
            
            for i in range(max_length):
                # 각 필드에서 안전하게 값 추출 (인덱스가 없으면 기본값)
                text_item = {
                    "rec_text": texts[i] if i < len(texts) else "",
                    "rec_score": float(rec_scores[i]) if i < len(rec_scores) else 0.0,
                    "rec_poly": self._convert_poly_to_list(rec_polys[i]) if i < len(rec_polys) else [],
                    "dt_poly": self._convert_poly_to_list(dt_polys[i]) if i < len(dt_polys) else [],
                    "dt_score": float(dt_scores[i]) if i < len(dt_scores) else 0.0,
                    "ori_poly": self._convert_poly_to_list(ori_polys[i]) if i < len(ori_polys) else [],
                    "ori_scores": float(ori_scores[i]) if i < len(ori_scores) else 0.0
                }
                
                structured_data.append(text_item)
            
            # JSON 문자열로 변환
            import json
            if pretty:
                return json.dumps(structured_data, indent=2, ensure_ascii=False)
            else:
                return json.dumps(structured_data, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ 구조화된 JSON 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def _convert_poly_to_list(self, poly):
        """
        다양한 형태의 좌표 데이터를 리스트로 변환
        
        Args:
            poly: numpy 배열, 리스트, 또는 기타 좌표 데이터
            
        Returns:
            list: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] 형태의 리스트
        """
        try:
            if poly is None:
                return []
            
            # numpy 배열인 경우
            if isinstance(poly, np.ndarray):
                # 1차원 배열을 2차원으로 변환 (8개 값 → 4x2)
                if poly.ndim == 1 and len(poly) == 8:
                    poly = poly.reshape(4, 2)
                
                # 2차원 배열을 리스트로 변환
                if poly.ndim == 2:
                    return [[float(x), float(y)] for x, y in poly]
                else:
                    return poly.tolist()
            
            # 이미 리스트인 경우
            elif isinstance(poly, list):
                # 평면 리스트 [x1, y1, x2, y2, ...] → [[x1, y1], [x2, y2], ...]
                if len(poly) == 8 and all(isinstance(x, (int, float)) for x in poly):
                    return [[float(poly[i]), float(poly[i+1])] for i in range(0, 8, 2)]
                # 이미 올바른 형태인 경우
                elif len(poly) > 0 and isinstance(poly[0], (list, tuple)):
                    return [[float(x), float(y)] for x, y in poly]
                else:
                    return poly
            
            # 기타 형태인 경우 문자열로 변환 후 파싱 시도
            else:
                return str(poly)
                
        except Exception as e:
            print(f"⚠️ 좌표 변환 실패: {e}")
            return []


    def _x_extract_reference_words_simple(self, result, left_region_ratio=0.10, confidence_threshold=0.3, min_word_length=2):
        """
        간단한 왼쪽 영역 필터링을 통한 기준단어 추출
        
        rec_polys의 left 값이 문서 너비의 10% 이내에 있는 텍스트들만 필터링합니다.
        """
        if not result or len(result) == 0:
            print("❌ OCR 결과가 없습니다.")
            return []
        
        try:
            page_result = result[0]
            
            # PaddleOCR 3.2.0 결과 구조 처리 - rec_polys 사용
            if isinstance(page_result, dict):
                texts = page_result.get('rec_texts', [])
                scores = page_result.get('rec_scores', [])
                polys = page_result.get('rec_polys', [])
                print("🔍 사용 좌표: rec_polys (정규화된 위치)")
            else:
                # 구버전 호환성
                texts = []
                scores = []
                polys = []
                for item in page_result:
                    if len(item) >= 2:
                        polys.append(item[0])
                        if isinstance(item[1], tuple):
                            texts.append(item[1][0])
                            scores.append(item[1][1])
                        else:
                            texts.append(str(item[1]))
                            scores.append(0.0)
            
            if not texts or not polys:
                print("❌ 인식된 텍스트나 좌표 정보가 없습니다.")
                return []
            
            # 문서 너비 계산
            all_x_coords = []
            for poly in polys:
                all_x_coords.extend([point[0] for point in poly])
            
            min_x = min(all_x_coords)
            max_x = max(all_x_coords)
            document_width = max_x - min_x
            left_boundary = min_x + document_width * left_region_ratio
            
            print(f"📏 문서 너비: {document_width:.1f}, 왼쪽 경계: {left_boundary:.1f}")
            
            # 왼쪽 영역 필터링
            left_items = []
            for i in range(min(len(texts), len(polys), len(scores))):
                text = texts[i].strip()
                poly = polys[i]
                confidence = scores[i] if i < len(scores) else 0.0
                
                # 신뢰도 및 길이 필터링
                if confidence < confidence_threshold or len(text) < min_word_length:
                    continue
                
                # left 값 계산
                left = min([point[0] for point in poly])
                top = min([point[1] for point in poly])
                bottom = max([point[1] for point in poly])
                center_y = (top + bottom) / 2
                
                # 왼쪽 영역 필터링
                if left <= left_boundary:
                    left_items.append({
                        'text': text,
                        'confidence': confidence,
                        'left': left,
                        'center_y': center_y
                    })
            
            # Y 좌표 기준 정렬
            left_items.sort(key=lambda x: x['center_y'])
            
            return left_items
            
        except Exception as e:
            print(f"❌ 간단 추출 실패: {e}")
            return []

    def _setup_korean_font(self):
        """한글 폰트 설정 (NanumGothic 사용)"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            import os
            
            # NanumGothic 폰트 직접 등록
            nanum_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
            
            if os.path.exists(nanum_path):
                # 폰트 등록
                fm.fontManager.addfont(nanum_path)
                font_prop = fm.FontProperties(fname=nanum_path)
                
                # matplotlib 설정
                plt.rcParams['font.family'] = font_prop.get_name()
                plt.rcParams['axes.unicode_minus'] = False
                
                print(f"✅ 한글 폰트 설정 완료: {font_prop.get_name()}")
                
            else:
                # 대체 폰트 사용
                plt.rcParams['font.family'] = 'DejaVu Sans'
                plt.rcParams['axes.unicode_minus'] = False
                print("⚠️ NanumGothic을 찾을 수 없어 DejaVu Sans 사용")
                
        except Exception as e:
            print(f"❌ 폰트 설정 오류: {e}")
            import matplotlib.pyplot as plt
            plt.rcParams['font.family'] = 'DejaVu Sans'
            plt.rcParams['axes.unicode_minus'] = False
    
    def debug_ocr_result(self, result, image_path: str = None):
        """
        PaddleOCR 3.2.0 시각화 
        
        Args:
            result: PaddleOCR.predict() 반환값
            image_path (str, optional): 시각화할 이미지 파일 경로. None이면 텍스트 분석만 수행
        """
        try:
            print(f"🎨 PaddleOCR 3.2.0 시각화 시작...")
            
            if not result or len(result) == 0:
                print("❌ 표시할 OCR 결과가 없습니다.")
                return
            
            page_result = result[0]
            if not isinstance(page_result, dict):
                print("❌ OCR 결과 형식이 올바르지 않습니다.")
                return
            
            # OCR 결과 추출
            texts = page_result.get('rec_texts', [])
            polys = page_result.get('dt_polys', page_result.get('rec_polys', []))
            scores = page_result.get('rec_scores', [])
            
            if not texts or not polys:
                print("❌ 텍스트나 좌표 정보가 없습니다.")
                return

            # OCR 결과 텍스트 분석 (항상 실행)
            print("🔍 OCR 결과 분석:")
            
            if isinstance(result, list) and len(result) > 0:
                page_result = result[0]
                if isinstance(page_result, dict):
                    texts = page_result.get('rec_texts', [])
                    scores = page_result.get('rec_scores', [])
                    polys = page_result.get('rec_polys', [])
                    
                    print(f"   📝 텍스트: {len(texts)}개")
                    print(f"   📊 신뢰도: {len(scores)}개")
                    print(f"   📍 좌표: {len(polys)}개")
                    print(f"   🔑 전체 키: {list(page_result.keys())}")
                    
                    if texts:
                        print(f"   📄 인식된 텍스트들:")
                        for i, text in enumerate(texts, 1):
                            confidence = f" (신뢰도: {scores[i-1]:.4f})" if i-1 < len(scores) else ""
                            print(f"      {i}. '{text}'{confidence}")
                    
                    # 신뢰도 통계
                    if scores:
                        avg_confidence = sum(scores) / len(scores)
                        print(f"   📊 평균 신뢰도: {avg_confidence:.4f}")
                        print(f"   📊 신뢰도 범위: {min(scores):.4f} ~ {max(scores):.4f}")
                        
                else:
                    print(f"   ⚠️ 예상과 다른 구조: {type(page_result)}")
            else:
                print(f"   ⚠️ 예상과 다른 최상위 구조: {type(result)}")

            # image_path가 제공된 경우에만 이미지 시각화 실행
            if image_path is None:
                print("💡 이미지 경로가 제공되지 않아 텍스트 분석만 수행했습니다.")
                print("   시각화를 원한다면 image_path를 지정하세요.")
                return

            # 새로운 PaddleX 기반 시각화 구현
            from PIL import Image, ImageDraw, ImageFont
            import matplotlib.pyplot as plt
            import numpy as np
            import os
            
            # 원본 이미지 로드
            pil_image = Image.open(image_path).convert('RGB')
            draw = ImageDraw.Draw(pil_image)
            
            print(f"📊 시각화 정보:")
            print(f"   - 이미지 크기: {pil_image.size}")
            print(f"   - 텍스트 수: {len(texts)}")
            print(f"   - 좌표 수: {len(polys)}")
            
            # 폰트 설정
            try:
                font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 24)
                    label_font = ImageFont.truetype(font_path, 16)
                else:
                    font = ImageFont.load_default()
                    label_font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
                label_font = ImageFont.load_default()
            
            # 색상 팔레트
            colors = [
                (255, 0, 0),     # 빨강
                (0, 255, 0),     # 초록
                (0, 0, 255),     # 파랑
                (255, 165, 0),   # 주황
                (128, 0, 128),   # 보라
                (255, 20, 147),  # 분홍
                (0, 191, 255),   # 하늘색
                (255, 215, 0),   # 금색
            ]
            
            # 바운딩 박스와 텍스트 그리기
            for i, (text, poly) in enumerate(zip(texts, polys)):
                try:
                    # 좌표 정규화
                    if isinstance(poly, (list, np.ndarray)):
                        poly_array = np.array(poly, dtype=np.float32)
                        
                        if poly_array.ndim == 1 and len(poly_array) == 8:
                            poly_array = poly_array.reshape(4, 2)
                        
                        if poly_array.ndim == 2 and poly_array.shape[0] >= 4:
                            # 다각형 좌표
                            polygon_points = [(int(p[0]), int(p[1])) for p in poly_array]
                            
                            # 색상 선택 (순환)
                            color = colors[i % len(colors)]
                            
                            # 다각형 테두리 그리기
                            draw.polygon(polygon_points, outline=color, width=3)
                            
                            # 번호 레이블 위치 (왼쪽 상단)
                            label_x = int(poly_array[0][0])
                            label_y = max(0, int(poly_array[0][1]) - 25)
                            
                            # 번호 배경 (가독성을 위해)
                            label_text = str(i + 1)
                            try:
                                bbox = draw.textbbox((label_x, label_y), label_text, font=label_font)
                                draw.rectangle(bbox, fill=color)
                            except:
                                # textbbox가 없는 구버전 PIL 대응
                                draw.rectangle((label_x-2, label_y-2, label_x+20, label_y+18), fill=color)
                            
                            # 번호 텍스트
                            draw.text((label_x, label_y), label_text, fill=(255, 255, 255), font=label_font)
                            
                            # 신뢰도 표시 (선택적)
                            if i < len(scores):
                                confidence_text = "{:.3f}".format(scores[i])
                                conf_y = label_y + 20
                                draw.text((label_x, conf_y), confidence_text, fill=color, font=label_font)
                            
                            # 로그 출력
                            score_text = "{:.3f}".format(scores[i]) if i < len(scores) else 'N/A'
                            print("   ✅ {}. '{}' - 신뢰도: {}".format(i+1, text, score_text))
                            
                except Exception as e:
                    print("   ❌ 바운딩 박스 그리기 실패 ({}): {}".format(i+1, str(e)))
                    continue
            
            # matplotlib으로 표시
            self._setup_korean_font()
            
            plt.figure(figsize=(20, 14))
            plt.imshow(pil_image)
            # 타이틀 제거 (요청사항 3)
            plt.axis('off')
            
            # 좌측 하단: 인식된 텍스트 목록 (신뢰도 막대 제거, 한글 깨짐 방지)
            text_info_lines = []
            for i, (text, score) in enumerate(zip(texts, scores)):
                # 신뢰도 막대 그래프 제거 (요청사항 1)
                line = "{}. {} ({:.3f})".format(i+1, text, score)
                text_info_lines.append(line)
            
            text_info = "\n".join(text_info_lines)
            
            # 한글 깨짐 방지를 위해 fontfamily 제거 (요청사항 1)
            plt.figtext(0.02, 0.02, "인식된 텍스트:\n{}".format(text_info), 
                    fontsize=11, verticalalignment='bottom',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.95))
            
            # 좌측 상단: 통계 정보 (요청사항 2)
            if scores:
                avg_confidence = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
                stats_text = "총 {}개 텍스트\n평균 신뢰도: {:.3f}\n범위: {:.3f} ~ {:.3f}".format(
                    len(texts), avg_confidence, min_score, max_score
                )
            else:
                stats_text = "총 {}개 텍스트\n신뢰도 정보 없음".format(len(texts))
            
            # 위치를 좌측 상단으로 변경 (0.02, 0.98)
            plt.figtext(0.02, 0.98, stats_text, 
                    fontsize=12, horizontalalignment='left', verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.9))
            
            plt.tight_layout()
            plt.show()
            
            print("✅ PaddleOCR 3.2.0 시각화 완료!")
            if scores:
                avg_confidence = sum(scores) / len(scores)
                print("📊 통계: 평균 신뢰도 {:.4f}, 범위 {:.3f}~{:.3f}".format(
                    avg_confidence, min(scores), max(scores)
                ))
            
        except Exception as e:
            print("❌ PaddleOCR 3.2.0 시각화 실패: {}".format(str(e)))
            import traceback
            traceback.print_exc()

   





