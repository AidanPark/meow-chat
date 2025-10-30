# 예시: LangChain으로 MCP 서버들을 조합한 전체 워크플로우
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import streamlit as st
import base64
from io import BytesIO

async def create_cat_health_agent():
    """고양이 건강검진 분석을 위한 MCP 에이전트 생성"""
    
    model = ChatOpenAI(model="gpt-4o")
    
    # 여러 MCP 서버를 하나의 클라이언트로 통합
    client = MultiServerMCPClient({
        "ocr": {
            "command": "python3",
            "args": ["./cat_health_ocr_server.py"],
            "transport": "stdio",
        },
        "analysis": {
            "command": "python3", 
            "args": ["./cat_health_analysis_server.py"],
            "transport": "stdio",
        },
        "vet_knowledge": {
            "url": "http://localhost:8001/sse",  # 수의학 지식베이스 서버
            "transport": "sse",
        }
    })
    
    # 모든 MCP 도구들을 에이전트에 연결
    tools = await client.get_tools()
    agent = create_react_agent(model, tools)
    
    return agent

async def analyze_cat_health_report(uploaded_image, cat_info):
    """전체 분석 워크플로우"""
    
    agent = await create_cat_health_agent()
    
    # 이미지를 base64로 변환
    image_b64 = base64.b64encode(uploaded_image.getvalue()).decode()
    
    # 자연어 명령으로 전체 파이프라인 실행
    prompt = f"""
    고양이 건강검진 결과지를 분석해주세요:
    
    1. 첨부된 이미지에서 OCR로 텍스트를 추출하세요
    2. 추출된 텍스트에서 혈액검사 수치들을 파싱하세요  
    3. 고양이 정보 (나이: {cat_info['age']}세, 체중: {cat_info['weight']}kg)를 고려해서 수치들을 분석하세요
    4. 정상/비정상 판정과 함께 건강 상태를 평가하세요
    5. 필요한 후속 조치나 권장사항을 제시하세요
    
    이미지 데이터: {image_b64[:100]}...
    """
    
    result = await agent.ainvoke({"messages": prompt})
    return result

# Streamlit UI에서 사용
def main():
    st.title("🐱 고양이 건강검진 결과 분석")
    
    uploaded_file = st.file_uploader("건강검진 결과지 업로드", type=['png', 'jpg', 'jpeg'])
    
    with st.sidebar:
        st.header("고양이 정보")
        cat_age = st.number_input("나이 (세)", min_value=0, max_value=25, value=5)
        cat_weight = st.number_input("체중 (kg)", min_value=0.5, max_value=15.0, value=4.5)
    
    if uploaded_file and st.button("분석 시작"):
        with st.spinner("건강검진 결과를 분석 중입니다..."):
            cat_info = {"age": cat_age, "weight": cat_weight}
            result = asyncio.run(analyze_cat_health_report(uploaded_file, cat_info))
            
            st.success("분석 완료!")
            st.write(result)

if __name__ == "__main__":
    main()