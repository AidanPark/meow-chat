import os
import asyncio
import streamlit as st

# LangChain MCP imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

load_dotenv("/home/aidan/work/meow-chat/.env")

# MCP 클라이언트 설정
@st.cache_resource
def create_mcp_agent():
    """LangChain MCP 에이전트 생성 (캐시됨)"""
    model = ChatOpenAI(model="gpt-4.1-mini")
    
    client = MultiServerMCPClient({
        "utilities": {
            "url": "http://localhost:8000/sse",
            "transport": "sse",
        }
    })
    
    return model, client

async def chat_with_mcp_agent(messages):
    """MCP 에이전트와 대화"""
    try:
        model, client = create_mcp_agent()
        
        # MCP 도구들을 가져와서 에이전트 생성
        tools = await client.get_tools()
        agent = create_react_agent(model, tools)
        
        # 마지막 메시지를 질문으로 사용
        latest_message = messages[-1][1] if messages else "안녕하세요!"
        
        print(f"🔍 사용자 질문: {latest_message}")
        print(f"🛠️ 사용 가능한 도구들: {[tool.name for tool in tools]}")
        
        # 에이전트 실행 (전체 응답 객체 반환)
        response = await agent.ainvoke({"messages": [{"role": "user", "content": latest_message}]})
        
        # 응답에서 사용된 도구 정보 추출
        used_tools = []
        tool_details = []
        
        if "messages" in response:
            for msg in response["messages"]:
                # 도구 호출 정보 확인
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        used_tools.append(tool_name)
                        tool_details.append({
                            "name": tool_name,
                            "args": tool_args
                        })
                        print(f"🔧 사용된 도구: {tool_name} - 인자: {tool_args}")
        
        # 최종 응답 텍스트
        final_content = response.get("messages", [])[-1].content if response.get("messages") else "죄송합니다. 응답을 생성할 수 없습니다."
        
        return {
            "content": final_content,
            "used_tools": used_tools,
            "tool_details": tool_details
        }
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return {
            "content": f"오류가 발생했습니다: {str(e)}",
            "used_tools": [],
            "tool_details": []
        }


def main():
    st.title("Multi-turn Chatbot with Unified MCP Server")
    st.caption("🧮 수학, 🌤️ 날씨, 🔧 유틸리티 기능을 제공하는 AI 어시스턴트")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # 사용 가능한 기능 안내
    with st.sidebar:
        st.header("사용 가능한 기능")
        st.markdown("""
        ### 🧮 수학 계산
        - "3 + 5는 얼마야?"
        - "12 곱하기 8은?"
        - "100을 4로 나누면?"
        
        ### 🌤️ 날씨 정보  
        - "뉴욕 날씨 어때?"
        - "서울 3일 예보는?"
        
        ### � 단위 변환
        - "25도를 화씨로 변환해줘"
        
        ### �💬 일반 대화
        - 기타 질문들
        """)

        st.info("**개선된 점**: 이제 하나의 통합 서버(포트 8000)에서 모든 기능을 제공합니다!")

        # 도구 사용 이력 표시
        if "tool_history" not in st.session_state:
            st.session_state["tool_history"] = []
        
        if st.session_state["tool_history"]:
            st.header("🔧 최근 사용된 도구들")
            for i, tool_info in enumerate(st.session_state["tool_history"][-5:]):  # 최근 5개만 표시
                with st.expander(f"도구 #{len(st.session_state['tool_history']) - len(st.session_state['tool_history'][-5:]) + i + 1}: {tool_info['name']}"):
                    st.json(tool_info['args'])

    # 대화 기록 표시
    for role, content in st.session_state["messages"]:
        with st.chat_message(role):
            if isinstance(content, dict):
                # 도구 사용 정보가 포함된 응답
                st.markdown(content["content"])
                if content.get("used_tools"):
                    st.info(f"🛠️ **사용된 도구**: {', '.join(content['used_tools'])}")
            else:
                st.markdown(content)

    # 사용자 입력
    if user_input := st.chat_input("질문을 입력해주세요..."):
        # 사용자 메시지 추가
        st.session_state["messages"].append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        # 어시스턴트 응답
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            tool_info_placeholder = st.empty()
            
            with st.spinner("AI가 답변을 생성 중입니다..."):
                try:
                    # MCP 에이전트로 응답 생성
                    response = asyncio.run(chat_with_mcp_agent(st.session_state["messages"]))
                    
                    # 응답 표시
                    if isinstance(response, dict):
                        message_placeholder.markdown(response["content"])
                        
                        # 사용된 도구 정보 표시
                        if response.get("used_tools"):
                            tool_info_placeholder.info(f"🛠️ **사용된 도구**: {', '.join(response['used_tools'])}")
                            
                            # 도구 사용 이력에 추가
                            for tool_detail in response.get("tool_details", []):
                                st.session_state["tool_history"].append(tool_detail)
                        
                        # 응답을 세션에 저장
                        st.session_state["messages"].append(("assistant", response))
                    else:
                        # 이전 버전 호환성
                        message_placeholder.markdown(response)
                        st.session_state["messages"].append(("assistant", response))
                    
                except Exception as e:
                    error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
                    message_placeholder.markdown(error_msg)
                    st.session_state["messages"].append(("assistant", error_msg))


if __name__ == "__main__":
    main()