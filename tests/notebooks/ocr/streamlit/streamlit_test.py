import os
import asyncio
import streamlit as st
import base64
from io import BytesIO
from PIL import Image

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
    model = ChatOpenAI(model="gpt-4o-mini")
    
    client = MultiServerMCPClient({
        "math": {
            "command": "python3",
            "args": ["./math_server.py"],
            "transport": "stdio",
        },
        "weather": {
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
        
        # 에이전트 실행
        response = await agent.ainvoke({"messages": [{"role": "user", "content": latest_message}]})
        
        return response.get("messages", [])[-1].content if response.get("messages") else "죄송합니다. 응답을 생성할 수 없습니다."
        
    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}"
    input_items: list[TResponseInputItem] = []

    for role, content in messages:
        if role == "user":
            input_items.append({"role": "user", "content": content})
        else:
            input_items.append({"role": "assistant", "content": content})
    
    result = Runner.run_streamed(agent, input=input_items)
    return result

def main():
    st.title("Meow Chat - MCP")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # 이전 메시지 표시
    for role, content in st.session_state["messages"]:
        with st.chat_message(role):
            st.markdown(content)

    if user_input := st.chat_input("대화를 입력해주세요."):
        st.session_state["messages"].append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            async def stream_response():
                nonlocal full_response
                result = await chat_with_bot(st.session_state["messages"])
                
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        full_response += event.data.delta
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
            
            asyncio.run(stream_response())

        st.session_state["messages"].append(("assistant", full_response))

if __name__ == "__main__":
    main()