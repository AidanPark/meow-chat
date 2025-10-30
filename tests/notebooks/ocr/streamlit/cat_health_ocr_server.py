# 예시: cat_health_ocr_server.py
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import base64
from PIL import Image
import io

mcp = FastMCP("CatHealthOCR")

@mcp.tool()
async def extract_health_report_text(image_base64: str) -> Dict[str, Any]:
    """Extract text from cat health report image using OCR"""
    # PaddleOCR 또는 기존 OCR 로직 사용
    extracted_text = await run_paddleocr(image_base64)
    return {
        "raw_text": extracted_text,
        "confidence": 0.95,
        "processing_time": "2.3s"
    }

@mcp.tool()
async def extract_lab_values(ocr_text: str) -> Dict[str, Any]:
    """Extract laboratory values from OCR text"""
    # 기존 lab_table_extractor.py 로직 활용
    lab_data = await parse_lab_table(ocr_text)
    return {
        "blood_values": lab_data,
        "extracted_parameters": ["WBC", "RBC", "PLT", "ALT", "AST"],
        "status": "success"
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")