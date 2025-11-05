# 예시: cat_health_analysis_server.py
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List

mcp = FastMCP("CatHealthAnalysis")

@mcp.tool()
async def analyze_blood_values(lab_values: Dict[str, float], cat_age: int, cat_weight: float) -> Dict[str, Any]:
    """고양이 혈액 검사 결과를 분석하고 건강 인사이트를 제공합니다."""
    # ...blood_analyzer.py 관련 주석 삭제...
    analysis = await perform_blood_analysis(lab_values, cat_age, cat_weight)
    return {
        "overall_health": analysis["status"],  # "normal", "warning", "critical"
        "abnormal_values": analysis["flags"],
        "recommendations": analysis["advice"],
        "follow_up_needed": analysis["follow_up"]
    }

@mcp.tool()
async def normalize_units(raw_values: Dict[str, Any]) -> Dict[str, float]:
    """다양한 단위 체계를 표준 값으로 정규화합니다."""
    # 기존 unit_normalizer.py 로직 활용
    normalized = await standardize_units(raw_values)
    return normalized

@mcp.tool()
async def get_reference_ranges(test_type: str, cat_age: int) -> Dict[str, Any]:
    """고양이 검사 항목의 정상 기준 범위를 반환합니다."""
    # 기존 reference/ 데이터 활용
    ranges = await load_reference_data(test_type, cat_age)
    return ranges

if __name__ == "__main__":
    mcp.run(transport="stdio")