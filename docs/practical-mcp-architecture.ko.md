"""
실용적인 MCP 서버 구조 - 고양이 건강 분석 프로젝트용
포트 3-4개만 사용하여 모든 기능 제공
"""

# 1. 건강 분석 서버 (포트 8001)
# health_analysis_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CatHealthAnalysis")

@mcp.tool()
async def extract_text_from_image(image_base64: str):
    """OCR로 건강검진 결과지에서 텍스트 추출"""
    pass

@mcp.tool()
async def parse_lab_values(ocr_text: str):
    """혈액검사 수치 파싱"""
    pass

@mcp.tool()
async def analyze_blood_results(lab_values: dict, cat_info: dict):
    """혈액검사 결과 분석"""
    pass

@mcp.tool()
async def normalize_units(raw_values: dict):
    """단위 표준화"""
    pass

@mcp.tool()
async def generate_health_report(analysis_results: dict):
    """건강 리포트 생성"""
    pass

# 2. 지식베이스 서버 (포트 8002)  
# knowledge_server.py
@mcp.tool()
async def search_veterinary_guidelines(query: str):
    """수의학 가이드라인 검색"""
    pass

@mcp.tool()
async def get_reference_ranges(test_type: str, cat_age: int):
    """정상 수치 범위 조회"""
    pass

@mcp.tool()
async def find_similar_cases(symptoms: list):
    """유사 사례 검색"""
    pass

# 3. 유틸리티 서버 (포트 8003)
# utilities_server.py  
@mcp.tool()
def add(a: int, b: int):
    """수학 계산"""
    pass

@mcp.tool()
async def get_weather(location: str):
    """날씨 정보"""
    pass

@mcp.tool()
async def store_conversation(messages: list):
    """대화 기록 저장"""
    pass
