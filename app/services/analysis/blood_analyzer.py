"""
Blood Analyzer Code Extraction Utilities

이 모듈은 혈액 분석기 관련 데이터에서 코드를 추출하는 유틸리티 함수들을 제공합니다.
"""

from typing import Set, List
from reference_data_analyzers import ANALYZERS
from reference_data_subparameters import SUBPARAMETERS


def extract_analyzer_codes() -> Set[str]:
    """
    ANALYZERS에서 모든 test code를 추출합니다.
    
    Returns:
        Set[str]: 분석기에서 추출된 모든 unique test code들
    """
    codes = set()
    for manufacturer, models in ANALYZERS.items():
        for model_name, model_data in models.items():
            tests = model_data.get("tests", [])
            for test in tests:
                if "code" in test:
                    codes.add(test["code"])
    return codes


def extract_subparameter_codes() -> Set[str]:
    """
    SUBPARAMETERS에서 모든 code를 추출합니다.
    
    Returns:
        Set[str]: 서브파라미터에서 추출된 모든 unique code들
    """
    codes = set()
    for category, items in SUBPARAMETERS.items():
        if isinstance(items, list):
            for item in items:
                if "code" in item:
                    codes.add(item["code"])
    return codes


def extract_all_unique_codes() -> List[str]:
    """
    ANALYZERS와 SUBPARAMETERS의 모든 코드를 합쳐서 unique한 코드들을 반환합니다.
    
    Returns:
        List[str]: 알파벳 순으로 정렬된 모든 unique code들
    """
    analyzer_codes = extract_analyzer_codes()
    subparameter_codes = extract_subparameter_codes()
    return sorted(analyzer_codes | subparameter_codes)


def get_analyzer_codes_by_manufacturer(manufacturer: str) -> Set[str]:
    """
    특정 제조사의 분석기에서 코드들을 추출합니다.
    
    Args:
        manufacturer (str): 제조사 이름 (예: "Abaxis", "IDEXX")
        
    Returns:
        Set[str]: 해당 제조사 분석기의 모든 unique test code들
    """
    codes = set()
    if manufacturer in ANALYZERS:
        for model_name, model_data in ANALYZERS[manufacturer].items():
            tests = model_data.get("tests", [])
            for test in tests:
                if "code" in test:
                    codes.add(test["code"])
    return codes


def get_analyzer_codes_by_model(manufacturer: str, model: str) -> Set[str]:
    """
    특정 제조사의 특정 모델에서 코드들을 추출합니다.
    
    Args:
        manufacturer (str): 제조사 이름
        model (str): 모델 이름
        
    Returns:
        Set[str]: 해당 모델의 모든 test code들
    """
    codes = set()
    if manufacturer in ANALYZERS and model in ANALYZERS[manufacturer]:
        tests = ANALYZERS[manufacturer][model].get("tests", [])
        for test in tests:
            if "code" in test:
                codes.add(test["code"])
    return codes


def get_subparameter_codes_by_category(category: str) -> Set[str]:
    """
    특정 카테고리의 서브파라미터에서 코드들을 추출합니다.
    
    Args:
        category (str): 카테고리 이름 (예: "CBC", "BLOOD_GAS")
        
    Returns:
        Set[str]: 해당 카테고리의 모든 code들
    """
    codes = set()
    if category in SUBPARAMETERS:
        items = SUBPARAMETERS[category]
        if isinstance(items, list):
            for item in items:
                if "code" in item:
                    codes.add(item["code"])
    return codes


def get_code_statistics() -> dict:
    """
    코드 추출 통계 정보를 반환합니다.
    
    Returns:
        dict: 통계 정보를 담은 딕셔너리
    """
    analyzer_codes = extract_analyzer_codes()
    subparameter_codes = extract_subparameter_codes()
    all_codes = analyzer_codes | subparameter_codes
    common_codes = analyzer_codes & subparameter_codes
    
    return {
        "analyzer_codes_count": len(analyzer_codes),
        "subparameter_codes_count": len(subparameter_codes),
        "total_unique_codes_count": len(all_codes),
        "common_codes_count": len(common_codes),
        "analyzer_only_count": len(analyzer_codes - subparameter_codes),
        "subparameter_only_count": len(subparameter_codes - analyzer_codes),
        "common_codes": sorted(common_codes)
    }


def search_code_in_data(search_code: str) -> dict:
    """
    특정 코드가 어디에서 사용되는지 검색합니다.
    
    Args:
        search_code (str): 검색할 코드
        
    Returns:
        dict: 검색 결과를 담은 딕셔너리
    """
    result = {
        "code": search_code,
        "found_in_analyzers": [],
        "found_in_subparameters": []
    }
    
    # ANALYZERS에서 검색
    for manufacturer, models in ANALYZERS.items():
        for model_name, model_data in models.items():
            tests = model_data.get("tests", [])
            for test in tests:
                if test.get("code") == search_code:
                    result["found_in_analyzers"].append({
                        "manufacturer": manufacturer,
                        "model": model_name,
                        "test_info": test
                    })
    
    # SUBPARAMETERS에서 검색
    for category, items in SUBPARAMETERS.items():
        if isinstance(items, list):
            for item in items:
                if item.get("code") == search_code:
                    result["found_in_subparameters"].append({
                        "category": category,
                        "item_info": item
                    })
    
    return result