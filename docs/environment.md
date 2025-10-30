# Meow Chat 하이브리드 환경 설치 가이드

## 🎯 목차
- [사전 준비](#사전-준비)
- [파일 구성](#파일-구성)  
- [환경 설치](#환경-설치)
- [검증 및 테스트](#검증-및-테스트)
- [문제 해결](#문제-해결)
- [일상 사용법](#일상-사용법)
- [설치 완료 체크리스트](#설치-완료-체크리스트)

---

## 🛠️ 사전 준비

### 필수 소프트웨어
- ✅ **Miniconda/Anaconda** 설치 완료
- ✅ **Git** 설치 완료
- ✅ **VS Code** 설치 완료 (권장)

### 프로젝트 디렉토리 확인
```bash
# 프로젝트 디렉토리로 이동
cd ~/work/meow-chat

# 현재 위치 확인
pwd
# 출력: /home/aidan/work/meow-chat
```

---

## 📝 파일 구성

### 1. environment.yml
이미 생성되어 있는 파일입니다:

```yaml
name: meow-chat
channels:
  - conda-forge
  - defaults

dependencies:
  - python=3.10
  - pip
  
  # 🔬 과학계산 & 이미지처리 (conda 추천)
  - numpy>=1.23,<2.0          # PaddlePaddle 호환성
  - opencv                     # 복잡한 C++ 의존성
  - matplotlib                 # 시각화
  - pandas                     # 데이터 분석
  - pillow                     # 이미지 형식 지원
  - scipy                      # 과학계산
  
  # 🌐 기본 네트워크 & 유틸리티
  - requests                   # HTTP 클라이언트
  - urllib3                    # URL 처리
  - certifi                    # SSL 인증서
  - pyyaml                     # YAML 파서
  
  # 📊 개발 환경 (conda 버전이 안정적)
  - jupyter                    # 노트북 환경
  - notebook                   # Jupyter Lab
  - ipykernel                  # Python 커널
  
  # pip 전용 패키지들
  - pip:
    - -r requirements.txt      # 웹프레임워크 & AI 패키지
```

### 2. requirements.txt 확인
```bash
# 파일 존재 확인
ls -la requirements.txt

# 내용 확인 (첫 10줄)
head -10 requirements.txt
```

### 3. requirements-dev.txt 확인
```bash
# 파일 존재 확인
ls -la requirements-dev.txt

# Jupyter 관련 라인이 주석처리되었는지 확인
grep -n jupyter requirements-dev.txt
```

---

## 🚀 환경 설치

### 단계 1: 기존 환경 정리
```bash
# 현재 활성 환경 확인
conda info --envs

# 기존 meow-chat 환경이 있다면 비활성화
conda deactivate

# 기존 환경 삭제 (있는 경우만)
conda env remove -n meow-chat
```

### 단계 2: YAML 문법 검증
```bash
# YAML 파일 문법 검사
python -c "
import yaml
try:
    with open('environment.yml') as f:
        yaml.safe_load(f)
    print('✅ YAML 문법 정상')
except Exception as e:
    print(f'❌ YAML 오류: {e}')
"
```

### 단계 3: conda 환경 생성
```bash
# 환경 생성 (5-10분 소요)
conda env create -f environment.yml
```

**예상 출력:**
```
Collecting package metadata (repodata.json): done
Solving environment: done

Downloading and Extracting Packages:
...

Preparing transaction: done
Verifying transaction: done
Executing transaction: done

Installing pip dependencies: ...
done

#
# To activate this environment, use
#
#     $ conda activate meow-chat
#
```

### 단계 4: 환경 활성화
```bash
# 환경 활성화
conda activate meow-chat

# 프롬프트 변경 확인
# (meow-chat) aidan@AidanPark:~/work/meow-chat$
```

### 단계 5: 개발용 패키지 설치 (선택적)
```bash
# 개발용 도구 설치
pip install -r requirements-dev.txt

# 설치 완료까지 3-5분 소요
```

---

## ✅ 검증 및 테스트

### 1. 기본 패키지 확인
```bash
# Python 버전 확인
python --version
# 출력: Python 3.10.x

# conda 패키지 확인
conda list | grep -E "(numpy|opencv|matplotlib|pandas)"

# pip 패키지 확인  
pip list | grep -E "(fastapi|paddle|uvicorn)"
```

### 2. 핵심 기능 테스트
```bash
# 기본 import 테스트
python -c "
import numpy as np
import cv2
import matplotlib.pyplot as plt
import pandas as pd
import fastapi
print('✅ 기본 패키지 import 성공')
print(f'NumPy: {np.__version__}')
print(f'OpenCV: {cv2.__version__}')
print(f'FastAPI: {fastapi.__version__}')
"
```

### 3. AI/ML 패키지 테스트
```bash
# PaddlePaddle 테스트
python -c "
import paddle
import paddleocr
print('✅ AI 패키지 import 성공')
print(f'PaddlePaddle: {paddle.__version__}')
print(f'PaddleOCR: {paddleocr.__version__}')
"
```

### 4. OCR 기능 테스트
```bash
# MyPaddleOCR 클래스 테스트
python -c "
try:
    from app.services.ocr.paddle_ocr import MyPaddleOCR
    ocr = MyPaddleOCR(lang='korean', show_log=False)
    print('✅ MyPaddleOCR 생성 성공!')
except Exception as e:
    print(f'❌ OCR 테스트 실패: {e}')
"
```

### 5. Jupyter 노트북 테스트
```bash
# Jupyter 버전 확인
jupyter --version

# 노트북 서버 테스트
jupyter notebook --generate-config
echo "✅ Jupyter 설정 완료"
```

---

## 🔧 문제 해결

### 자주 발생하는 오류들

#### 1. YAML 문법 오류
```bash
# 오류: EnvironmentSpecPluginNotDetected
# 해결: YAML 들여쓰기 확인
cat -A environment.yml | head -5
# 스페이스와 탭 혼용 확인
```

#### 2. 의존성 충돌
```bash
# 오류: Cannot install paddlepaddle and numpy==2.x
# 해결: numpy 버전 확인
conda list numpy
# numpy 1.x 버전인지 확인
```

#### 3. pip 패키지 설치 실패
```bash
# 오류: pip install failed
# 해결: pip 업그레이드
pip install --upgrade pip

# 개별 패키지 테스트
pip install fastapi
```

#### 4. 네트워크 오류
```bash
# 오류: CondaHTTPError
# 해결: 프록시 설정 또는 채널 변경
conda config --add channels conda-forge
conda config --set channel_priority flexible
```

### 완전 초기화 방법
```bash
# 모든 것을 처음부터 다시
conda env remove -n meow-chat
conda clean --all
rm -rf ~/.conda/pkgs/cache
conda env create -f environment.yml
```

---

## 🎮 일상 사용법

### 매일 개발 시작
```bash
# 1. 프로젝트 디렉토리로 이동
cd ~/work/meow-chat

# 2. conda 환경 활성화
conda activate meow-chat

# 3. 최신 코드 동기화 (Git 사용시)
git pull

# 4. 패키지 업데이트 (주기적)
pip install -r requirements.txt --upgrade
```

### Jupyter 노트북 실행
```bash
# 노트북 서버 시작
jupyter notebook

# 특정 노트북 열기
jupyter notebook notebooks/ocr/paddleOCR.ipynb
```

### FastAPI 서버 실행
```bash
# 개발 서버 시작
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 브라우저에서 확인: http://localhost:8000/docs
```

### Streamlit 프론트엔드 실행
```bash
# (선택) MCP 서버 실행: 새 터미널에서
cd ~/work/meow-chat/mcp_servers
bash start_servers.sh

# Streamlit 프론트엔드 실행(레포 루트 기준)
cd ~/work/meow-chat
streamlit run frontend/app.py

# 또는 프론트엔드 폴더에서 실행
cd ~/work/meow-chat/frontend
streamlit run app.py
```

환경 변수 및 설정
- OPENAI_API_KEY: 레포 루트 .env 또는 환경변수로 설정
- MCP 서버 주소: `frontend/config/mcp_servers.yml` 존재 시 이를 사용, 없으면 localhost 기본(8000/8001/8002)

### 코드 품질 검사 (개발용 패키지 설치한 경우)
```bash
# 코드 포맷팅
black app/

# import 정렬
isort app/

# 타입 체크
mypy app/

# 테스트 실행
pytest tests/ -v
```

### 환경 백업 및 공유
```bash
# 현재 환경 내보내기
conda env export > environment-backup-$(date +%Y%m%d).yml

# 팀원과 공유할 환경 파일 생성
conda env export --no-builds > environment-share.yml
```

---

## 📊 설치 완료 체크리스트

- [ ] Python 3.10.x 설치 확인
- [ ] conda 환경 `meow-chat` 생성 완료  
- [ ] numpy < 2.0 버전 확인
- [ ] OpenCV 설치 확인
- [ ] PaddlePaddle 설치 확인
- [ ] PaddleOCR 설치 확인
- [ ] FastAPI 설치 확인
- [ ] MyPaddleOCR 클래스 로드 성공
- [ ] Jupyter 노트북 실행 가능
- [ ] 개발용 도구 설치 완료 (선택)

---

## 🎯 다음 단계

1. **OCR 기능 테스트**: 노트북에서 이미지 OCR 실행
2. **API 서버 구축**: FastAPI 엔드포인트 개발
3. **프론트엔드 연동**: 이미지 업로드 기능 구현
4. **배포 준비**: Docker 컨테이너 구성

---

## 💡 하이브리드 환경의 장점

- **✅ 의존성 안정성**: conda로 기본 과학계산 라이브러리 관리
- **✅ 최신 패키지**: pip으로 최신 웹/AI 프레임워크 설치
- **✅ 빠른 설치**: conda 바이너리 + pip 전용 패키지
- **✅ 팀 협업**: environment.yml로 동일 환경 재현
- **✅ 유연성**: 각 패키지를 최적 방법으로 관리




# 1. 기존 환경 정리
conda deactivate
conda remove -n meow-chat --all -y

# 2. 새 환경 생성
conda create -n meow-chat python=3.10 -y
conda activate meow-chat

# 3. 최신 패키지 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

