# 📓 Jupyter Notebooks (PyCharm)

실험, 프로토타이핑, 코드 테스트를 위한 Jupyter 노트북 모음입니다.

---

## 📑 목차

1. [빠른 시작](#-빠른-시작)
2. [디렉토리 구조](#-디렉토리-구조)
3. [인터프리터 선택](#-인터프리터-선택)
4. [사용 예시](#-사용-예시)
5. [PyCharm 단축키](#-pycharm-단축키)
6. [문제 해결](#-문제-해결) ⭐ Safe mode 포함
7. [보안 주의사항](#-보안-주의사항)

---

## 🚀 빠른 시작

### 1️⃣ 커널 등록 (최초 1회만)
```bash
cd /home/aidan/projects/meow-chat
poetry run python -m ipykernel install --user --name=meow-chat --display-name="Python 3.10 (meow-chat)"
```

### 2️⃣ PyCharm에서 노트북 실행 (권장)
1. PyCharm에서 `.ipynb` 파일 열기 (예: `notebooks/ocr/test_google_vision.ipynb`)
2. 파일 상단 **"Start Jupyter Server"** 클릭
3. 커널 드롭다운에서 **"Python 3.10 (meow-chat)"** 선택
4. 셀 실행: `Shift+Enter`

### 3️⃣ 터미널에서 실행 (대안)
```bash
# 방법 1: 스크립트 사용
./scripts/start_jupyter.sh

# 방법 2: 직접 실행
cd notebooks/
poetry run jupyter notebook
```

### 4️⃣ 환경 확인 (첫 번째 셀)
```python
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent
sys.path.insert(0, str(PROJECT_ROOT))

print(f"✅ Python: {sys.executable}")
print(f"✅ Version: {sys.version}")
print(f"✅ 프로젝트 루트: {PROJECT_ROOT}")
```

---

## 📂 디렉토리 구조

```
notebooks/
├── README.md              # 이 파일
├── ocr/                   # OCR 테스트 및 실험
│   ├── test_google_vision.ipynb
│   └── result/            # OCR 결과 저장 (Git 제외)
├── llm/                   # LLM 프롬프트 테스트
│   └── test_prompts.ipynb
└── experiments/           # 기타 실험 및 프로토타이핑
    └── quick_test.ipynb
```

### 준비된 노트북

| 노트북 | 설명 |
|--------|------|
| `ocr/test_google_vision.ipynb` | Google Vision OCR 테스트, 바운딩 박스 정보, 처리 시간 측정 |
| `experiments/quick_test.ipynb` | 간단한 코드 스니펫 테스트, 프로젝트 모듈 임포트 |

---

## 🐍 인터프리터 선택

### 선택해야 할 커널
- **표시 이름**: `Python 3.10 (meow-chat)`
- **커널 이름**: `meow-chat`

### PyCharm에서 설정

#### 방법 A: Poetry 환경 자동 감지 (권장)
1. **File → Settings** (Ctrl+Alt+S)
2. **Project: meow-chat → Python Interpreter**
3. 톱니바퀴 ⚙️ → **Add Interpreter → Add Local Interpreter**
4. **Poetry Environment** 탭 선택
5. **OK** 클릭

#### 방법 B: 노트북에서 직접 선택
1. `.ipynb` 파일 열기
2. 상단 **"Start Jupyter Server"** 클릭
3. 커널 드롭다운에서 **"Python 3.10 (meow-chat)"** 선택

### 커널이 보이지 않는 경우
```bash
# 1. 커널 재등록
poetry run python -m ipykernel install --user --name=meow-chat --display-name="Python 3.10 (meow-chat)"

# 2. 등록 확인
poetry run jupyter kernelspec list

# 3. PyCharm 재시작
```

### Poetry 환경 경로 확인
```bash
poetry env info
# 또는
poetry run python -c "import sys; print(sys.executable)"
```

---

## 📝 사용 예시

### 자동 리로드 활성화 (첫 셀)
```python
%load_ext autoreload
%autoreload 2
```

### OCR 테스트
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))

from src.services.ocr.google_vision import GoogleVisionOCR
from src.utils.images import load_image

ocr = GoogleVisionOCR()
image = load_image("../tests/fixtures/images/sample_checkup.jpg")
result = ocr.extract_text(image)

print(f"텍스트 길이: {len(result.text)} 글자")
print(result.text[:500])
```

### LLM 테스트
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))

from src.services.llm.openai_llm import OpenAILLM

llm = OpenAILLM()
response = llm.generate("고양이 건강검진에서 중요한 항목은?")
print(response)
```

---

## ⌨️ PyCharm 단축키

| 작업 | 단축키 |
|------|--------|
| 셀 실행 | `Shift + Enter` |
| 셀 실행 후 아래에 새 셀 추가 | `Alt + Shift + Enter` |
| 위에 셀 추가 | `A` (명령 모드) |
| 아래에 셀 추가 | `B` (명령 모드) |
| 셀 삭제 | `D D` (두 번) |
| 셀 타입 변경 (마크다운/코드) | `M` / `Y` |
| 커널 인터럽트 | `I I` (두 번) |
| 커널 재시작 | 상단 버튼 또는 `0 0` |
| Settings 열기 | `Ctrl + Alt + S` |

---

## 🔧 문제 해결

### ❌ "Safe mode, limited functionality" 메시지 (PyCharm 프로젝트)

**원인**: PyCharm이 프로젝트를 신뢰하지 않는 상태 (보안 기능)

**해결 방법 1: Trust project 버튼 클릭 (가장 간단!) ⭐**
1. 화면 상단 또는 우측의 **"Trust project"** 버튼 클릭
2. 또는 메시지 영역의 **"Trust project"** 링크 클릭

**해결 방법 2: PyCharm 설정에서 신뢰하기**
1. **File → Settings** (Ctrl+Alt+S)
2. **Build, Execution, Deployment → Trusted Projects**
3. 프로젝트 경로 추가: `/home/aidan/projects/meow-chat`
4. **OK** 클릭

**해결 방법 3: workspace.xml 파일 생성 (자동 해결)**
프로젝트에 `.idea/workspace.xml` 파일이 생성되어 있으면 자동으로 신뢰됩니다.
```bash
# 이미 처리됨 - PyCharm 재시작 필요 없음
```

**💡 참고**:
- 이 메시지는 PyCharm의 보안 기능입니다
- 본인의 프로젝트는 안전하게 신뢰할 수 있습니다
- Trust 후에는 모든 Python 파일에서 전체 기능 사용 가능

### ❌ "Safe mode, limited functionality" 메시지 (Jupyter 노트북)

**원인**: 노트북이 신뢰할 수 없는(untrusted) 상태로 표시됨

**해결 방법 1: PyCharm에서 신뢰하기**
1. 노트북 파일 상단의 **"Trust"** 또는 **"신뢰"** 버튼 클릭
2. 또는 우측 상단의 경고 아이콘 클릭 → **"Trust Notebook"** 선택

**해결 방법 2: 명령줄에서 신뢰하기**
```bash
# 특정 노트북 파일 신뢰
jupyter trust notebooks/ocr/test_google_vision.ipynb

# notebooks/ 폴더의 모든 노트북 신뢰
jupyter trust notebooks/**/*.ipynb
```

**해결 방법 3: 모든 로컬 노트북 자동 신뢰 (권장)**
```bash
# Jupyter 설정 파일 생성/편집
jupyter notebook --generate-config

# ~/.jupyter/jupyter_notebook_config.py 파일에 추가:
# c.NotebookApp.trust_xheaders = True
# c.ContentsManager.trust_notebooks = True
```

**또는 간단하게:**
```bash
# 현재 프로젝트의 모든 노트북 한 번에 신뢰
find notebooks/ -name "*.ipynb" -exec jupyter trust {} \;
```

**💡 참고**: 
- 이 메시지는 보안을 위한 것이며, 본인이 작성한 노트북은 안전하게 신뢰할 수 있습니다
- Git에서 클론한 노트북은 항상 untrusted 상태로 시작합니다

### ❌ "Jupyter Server not found" 오류

**방법 1: PyCharm 내장 서버 사용**
1. 노트북 파일 상단 **"Configure Jupyter Server"** 클릭
2. **"Managed Server"** 선택
3. **"Start"** 버튼 클릭

**방법 2: 기존 서버 연결**
1. 터미널에서: `poetry run jupyter notebook`
2. 출력된 URL과 토큰 복사 (예: `http://localhost:8888/?token=abc123...`)
3. PyCharm에서 **"Configure Jupyter Server"** → **"Use existing"**
4. URL 입력

### ❌ 모듈을 찾을 수 없는 경우 (ModuleNotFoundError)

**해결 방법 1**: 노트북 첫 셀에 추가
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path.cwd().parent
sys.path.insert(0, str(PROJECT_ROOT))
```

**해결 방법 2**: PyCharm 프로젝트 설정
1. **File → Settings → Project: meow-chat → Project Structure**
2. 프로젝트 루트 폴더 선택
3. **"Sources"** 버튼 클릭 (파란색)
4. **OK** → PyCharm 재시작

### ❌ Poetry 환경을 찾을 수 없는 경우
```bash
# 1. 환경 경로 확인
poetry env info

# 2. PyCharm에서 수동 추가
# File → Settings → Python Interpreter
# Add Interpreter → Existing → 경로 입력
```

### ❌ Jupyter 실행이 느리거나 응답 없음
```bash
# Jupyter 캐시 삭제
rm -rf ~/.jupyter/runtime/*

# 커널 재시작: PyCharm에서 "Restart Kernel" 버튼 클릭
```

### ❌ "Kernel Dead" 오류
```bash
# 1. 의존성 재설치
poetry install

# 2. ipykernel 재설치
poetry add --group dev ipykernel

# 3. 커널 재등록
poetry run python -m ipykernel install --user --name=meow-chat --display-name="Python 3.10 (meow-chat)"

# 4. PyCharm 재시작
```

---

## 🔒 보안 주의사항

### Git 커밋 제외 대상
- ✅ `.ipynb_checkpoints/` (노트북 체크포인트)
- ✅ `ocr/result/` (OCR 결과)
- ✅ `*.jpg`, `*.png`, `*.pdf` (이미지/문서 파일)

### 민감 정보 관리
- ⚠️ API 키를 노트북에 직접 작성하지 마세요
- ✅ 환경변수 사용: `os.getenv("OPENAI_API_KEY")`
- ✅ `.env` 파일 활용

---

## 💡 팁

### 성능 측정
```python
%%time
# 시간을 측정할 코드
result = ocr.extract_text(image)
```

### 큰 이미지 처리
```python
# 이미지 리사이즈로 API 호출 시간 단축
from PIL import Image
image = image.resize((800, 800))
```

### API 결과 캐싱
```python
import pickle
from pathlib import Path

cache_file = Path("result/ocr_cache.pkl")
if cache_file.exists():
    result = pickle.load(open(cache_file, "rb"))
else:
    result = ocr.extract_text(image)
    pickle.dump(result, open(cache_file, "wb"))
```

---

## 📚 추가 문서

- **테스트 가이드**: `docs/TEST_GUIDE.md`
- **API 키 설정**: `docs/API_KEYS_SETUP.md`
- **빠른 시작**: `docs/QUICKSTART.md`
- **PyCharm 공식 문서**: [Jupyter Notebook Support](https://www.jetbrains.com/help/pycharm/jupyter-notebook-support.html)

---

## 🔑 핵심 정리

| 항목 | 값 |
|------|-----|
| IDE | PyCharm Professional |
| 가상환경 | Poetry (pyenv 기반) |
| Python 버전 | 3.10.14 |
| 커널 이름 | `Python 3.10 (meow-chat)` |
| 활성화 스크립트 | `scripts/activate_env.sh` |

---

**마지막 업데이트**: 2025-01-26

