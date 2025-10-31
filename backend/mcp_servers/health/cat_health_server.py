"""
고양이 건강 분석 서버 - 포트 8002
혈액 검사 분석, 건강 상태 평가, 의료 데이터 처리
"""

import logging
import os
import sys
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

# Bootstrap sys.path so that `mcp_servers` package can be imported when running from subfolders
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp_servers.common.runtime import setup_logging, load_mcp_server_settings


setup_logging()
logger = logging.getLogger(__name__)

mcp = FastMCP("CatHealthAnalysisServer")

# 네트워크 설정: 외부 설정/환경변수에서 로드 (기본값: 127.0.0.1:8002)
_host, _port = load_mcp_server_settings("cat_health", default_port=8002)
mcp.settings.host = _host
mcp.settings.port = _port

# 참조 범위 데이터 (간단한 예시)
REFERENCE_RANGES = {
    "adult": {  # 성인 고양이 (1-7세)
        "glucose": {"min": 70, "max": 120, "unit": "mg/dL"},
        "bun": {"min": 14, "max": 36, "unit": "mg/dL"},
        "creatinine": {"min": 0.8, "max": 2.4, "unit": "mg/dL"},
        "alt": {"min": 10, "max": 100, "unit": "U/L"},
        "ast": {"min": 5, "max": 55, "unit": "U/L"},
        "total_protein": {"min": 5.4, "max": 7.8, "unit": "g/dL"},
        "albumin": {"min": 2.5, "max": 3.9, "unit": "g/dL"}
    },
    "senior": {  # 시니어 고양이 (7세 이상)
        "glucose": {"min": 70, "max": 130, "unit": "mg/dL"},
        "bun": {"min": 16, "max": 40, "unit": "mg/dL"},
        "creatinine": {"min": 0.8, "max": 2.8, "unit": "mg/dL"},
        "alt": {"min": 10, "max": 120, "unit": "U/L"},
        "ast": {"min": 5, "max": 60, "unit": "U/L"},
        "total_protein": {"min": 5.2, "max": 8.0, "unit": "g/dL"},
        "albumin": {"min": 2.3, "max": 3.9, "unit": "g/dL"}
    }
}

@mcp.tool()
async def analyze_blood_values(lab_values: Dict[str, float], cat_age: int, cat_weight: float) -> Dict[str, Any]:
    """Analyze cat blood test results and provide comprehensive health insights"""
    logger.info(f"🩺 BLOOD_ANALYSIS 도구 호출: 나이 {cat_age}세, 체중 {cat_weight}kg")

    age_group = "senior" if cat_age >= 7 else "adult"
    ref_ranges = REFERENCE_RANGES[age_group]

    analysis_result: Dict[str, Any] = {
        "overall_health": "normal",
        "abnormal_values": [],
        "recommendations": [],
        "follow_up_needed": False,
        "critical_alerts": []
    }

    for test_name, value in lab_values.items():
        if test_name in ref_ranges:
            ref = ref_ranges[test_name]
            if value < ref["min"]:
                analysis_result["abnormal_values"].append({
                    "test": test_name,
                    "value": value,
                    "status": "low",
                    "reference": f"{ref['min']}-{ref['max']} {ref['unit']}"
                })
                if test_name == "albumin" and value < 2.0:
                    analysis_result["critical_alerts"].append("심각한 저알부민혈증 - 즉시 수의사 상담 필요")
                elif test_name == "glucose" and value < 60:
                    analysis_result["critical_alerts"].append("저혈당 위험 - 응급 처치 필요")
            elif value > ref["max"]:
                analysis_result["abnormal_values"].append({
                    "test": test_name,
                    "value": value,
                    "status": "high",
                    "reference": f"{ref['min']}-{ref['max']} {ref['unit']}"
                })
                if test_name == "creatinine" and value > 3.0:
                    analysis_result["critical_alerts"].append("신장 기능 이상 - 신속한 치료 필요")
                elif test_name == "glucose" and value > 200:
                    analysis_result["critical_alerts"].append("당뇨병 의심 - 정밀 검사 필요")

    if analysis_result["critical_alerts"]:
        analysis_result["overall_health"] = "critical"
        analysis_result["follow_up_needed"] = True
    elif len(analysis_result["abnormal_values"]) > 2:
        analysis_result["overall_health"] = "warning"
        analysis_result["follow_up_needed"] = True
    elif analysis_result["abnormal_values"]:
        analysis_result["overall_health"] = "mild_concern"

    if analysis_result["overall_health"] != "normal":
        analysis_result["recommendations"] = [
            "수의사와 상담하여 정확한 진단 받기",
            "정기적인 건강 검진 실시",
            "적절한 식단 관리",
        ]

    logger.info(f"🩺 BLOOD_ANALYSIS 결과: {analysis_result['overall_health']}")
    return analysis_result

@mcp.tool()
async def normalize_lab_units(raw_values: Dict[str, Any]) -> Dict[str, float]:
    """Normalize different unit systems to standard laboratory values"""
    logger.info(f"⚖️ UNIT_NORMALIZE 도구 호출: {len(raw_values)}개 항목")

    normalized: Dict[str, float] = {}
    conversion_rules = {
        "glucose": {
            "mmol/L": lambda x: x * 18.0,
            "mg/dL": lambda x: x,
            "mg/dl": lambda x: x,
        },
        "bun": {
            "mmol/L": lambda x: x * 2.8,
            "mg/dL": lambda x: x,
            "mg/dl": lambda x: x,
        },
        "creatinine": {
            "μmol/L": lambda x: x / 88.4,
            "umol/L": lambda x: x / 88.4,
            "mg/dL": lambda x: x,
            "mg/dl": lambda x: x,
        },
    }

    for test_name, test_data in raw_values.items():
        if isinstance(test_data, dict) and "value" in test_data and "unit" in test_data:
            value = float(test_data["value"])
            unit = str(test_data["unit"])
            if test_name in conversion_rules and unit in conversion_rules[test_name]:
                normalized[test_name] = conversion_rules[test_name][unit](value)
            else:
                normalized[test_name] = value
        elif isinstance(test_data, (int, float)):
            normalized[test_name] = float(test_data)

    logger.info(f"⚖️ UNIT_NORMALIZE 결과: {len(normalized)}개 정규화됨")
    return normalized

@mcp.tool()
async def get_reference_ranges(test_type: str, cat_age: int) -> Dict[str, Any]:
    """Get normal reference ranges for specific cat lab values based on age"""
    logger.info(f"📊 REFERENCE 도구 호출: {test_type}, 나이 {cat_age}세")

    age_group = "senior" if cat_age >= 7 else "adult"

    if test_type == "all":
        result: Dict[str, Any] = REFERENCE_RANGES[age_group]
    elif test_type in REFERENCE_RANGES[age_group]:
        result = {test_type: REFERENCE_RANGES[age_group][test_type]}
    else:
        result = {"error": f"Unknown test type: {test_type}"}

    logger.info(f"📊 REFERENCE 결과: {test_type} 범위 반환")
    return result

@mcp.tool()
async def assess_kidney_function(creatinine: float, bun: float, cat_age: int) -> Dict[str, Any]:
    """Specific assessment for kidney function based on creatinine and BUN levels"""
    logger.info(f"🫘 KIDNEY 도구 호출: 크레아티닌 {creatinine}, BUN {bun}, 나이 {cat_age}세")

    assessment: Dict[str, Any] = {
        "stage": "normal",
        "description": "",
        "recommendations": [],
        "monitoring_frequency": "annual",
    }

    if creatinine <= 1.6:
        assessment.update(stage="normal", description="신장 기능 정상", monitoring_frequency="annual")
    elif creatinine <= 2.8:
        assessment.update(
            stage="ckd_stage_2",
            description="경미한 신장 기능 저하",
            monitoring_frequency="every_6_months",
            recommendations=["저단백 식단 고려", "충분한 수분 섭취"],
        )
    elif creatinine <= 5.0:
        assessment.update(
            stage="ckd_stage_3",
            description="중등도 신장 기능 저하",
            monitoring_frequency="every_3_months",
            recommendations=["신장 전용 사료", "인 제한 식단", "정기적인 혈액 검사"],
        )
    else:
        assessment.update(
            stage="ckd_stage_4",
            description="심각한 신장 기능 저하",
            monitoring_frequency="monthly",
            recommendations=["응급 치료 필요", "수액 요법", "전문의 상담"],
        )

    ratio = bun / creatinine if creatinine > 0 else 0
    if ratio > 30:
        assessment["additional_notes"] = "탈수 또는 위장관 출혈 가능성 검토 필요"

    logger.info(f"🫘 KIDNEY 결과: {assessment['stage']}")
    return assessment

@mcp.tool()
async def generate_health_report(cat_info: Dict[str, Any], lab_results: Dict[str, float]) -> str:
    """Generate a comprehensive health report for the cat"""
    logger.info(f"📋 REPORT 도구 호출: {cat_info.get('name', '고양이')}의 건강 리포트")

    name = cat_info.get('name', '고양이')
    age = int(cat_info.get('age', 0))
    weight = float(cat_info.get('weight', 0))
    breed = cat_info.get('breed', '믹스')

    analysis = await analyze_blood_values(lab_results, age, weight)

    lines = [
        f"=== {name} 건강 검진 리포트 ===",
        "",
        "🐱 기본 정보:",
        f"- 나이: {age}세",
        f"- 체중: {weight}kg",
        f"- 품종: {breed}",
        "",
        "🩺 검사 결과 요약:",
        f"- 전체 건강 상태: {analysis['overall_health']}",
        f"- 이상 수치 개수: {len(analysis['abnormal_values'])}개",
        f"- 추가 검사 필요 여부: {'예' if analysis['follow_up_needed'] else '아니오'}",
        "",
        "📊 상세 분석:",
    ]

    if analysis['abnormal_values']:
        lines.append("\n⚠️ 이상 수치:")
        for abnormal in analysis['abnormal_values']:
            lines.append(f"- {abnormal['test']}: {abnormal['value']} ({abnormal['status']}) - 정상범위: {abnormal['reference']}")

    if analysis['critical_alerts']:
        lines.append("\n🚨 중요 알림:")
        for alert in analysis['critical_alerts']:
            lines.append(f"- {alert}")

    if analysis['recommendations']:
        lines.append("\n💡 권장사항:")
        for rec in analysis['recommendations']:
            lines.append(f"- {rec}")

    logger.info(f"📋 REPORT 결과: {name} 리포트 생성 완료")
    return "\n".join(lines)

if __name__ == "__main__":
    logger.info("🚀 고양이 건강 분석 MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: analyze_blood_values, normalize_lab_units, get_reference_ranges, assess_kidney_function, generate_health_report")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8002} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "CatHealthAnalysisServer"})

    sse_app = mcp.sse_app()
    routes = [
        Route("/health", endpoint=health),
        *sse_app.routes,
    ]

    app = Starlette(
        routes=routes,
        middleware=sse_app.user_middleware,
    )

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8002)
