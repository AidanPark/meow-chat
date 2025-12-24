import io

import streamlit as st
from PIL import Image

st.set_page_config(page_title="Camera/Gallery Upload Demo", layout="centered")
st.title("사진 업로드 데모 (Streamlit)")

st.markdown(
    """
Streamlit에서 사진을 받는 대표적인 방법은 2가지입니다.

1) **카메라 촬영**: `st.camera_input()` (모바일/지원 브라우저에서 카메라 앱 호출)
2) **갤러리/파일 업로드**: `st.file_uploader()`

아래에서 둘 중 하나로 이미지를 선택해보세요.
"""
)

st.subheader("1) 카메라로 촬영")
cam = st.camera_input("카메라로 촬영하기")

st.subheader("2) 갤러리/파일 업로드")
up = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

img_bytes = None
source = None

if cam is not None:
    img_bytes = cam.getvalue()
    source = "camera"
elif up is not None:
    img_bytes = up.getvalue()
    source = "uploader"

if img_bytes is None:
    st.info("카메라 촬영 또는 파일 업로드를 해주세요.")
    st.stop()

st.success(f"이미지 수신 완료 (source={source}, bytes={len(img_bytes):,})")

image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
st.image(image, caption="입력 이미지", use_container_width=True)

# 여기서 서버로 전송하거나 OCR을 호출하면 됩니다.
# 예: requests.post("http://localhost:8000/api/ocr", files={"image": img_bytes})

st.code(
    """\
# 다음 단계 예시(서버로 전송)
# import requests
# r = requests.post(
#     'http://localhost:8000/api/ocr',
#     files={'image': ('photo.jpg', img_bytes, 'image/jpeg')},
#     data={'session_id': 'demo'}
# )
# st.json(r.json())
""",
    language="python",
)

