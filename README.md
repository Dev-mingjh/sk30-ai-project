
# 환경 세팅 방법
> 작업환경: vscode venv 가상환경 사용
```bash
git clone -b main https://github.com/Dev-mingjh/sk30-ai-project.git
cd sk30-ai-project
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

# GUIDE Agent (공격 대응 가이드)

> 공식 보안 프레임워크 기반 RAG 구조의 보안 사고 대응 가이드 생성 Agent

## 1. Agent 개요

### 1.1 개발 배경 및 문제 정의

최근 보안 사고 대응 과정에서 LLM을 활용한 자동화된 대응 가이드 생성 시도가 증가하고 있으나,  
LLM 단독 사용은 **근거 없는 응답**과 **공식 가이드와의 불일치**라는 한계를 가진다.

본 프로젝트는 이러한 문제를 해결하기 위해,  
공식 보안 프레임워크 및 기관 가이드 문서를 기반으로 한  
**RAG(Retrieval-Augmented Generation) 구조의 GUIDE Agent**를 설계하였다.

GUIDE Agent는 VectorDB 기반 검색을 통해 신뢰 가능한 문서 근거를 우선 확보한 후,  
이를 바탕으로 LLM이 대응 가이드를 종합·생성하는 방식으로 동작한다.

이를 통해 다음 정보를 **일관되고 근거 중심적으로 제공**하는 것을 목표로 한다.

---

### 1.2 GUIDE Agent 목적

GUIDE Agent의 주요 목적은 다음과 같다.

- 공식 문서 기반의 **신뢰 가능한 보안 대응 가이드 제공**
- 공격 유형에 대한 **구조화된 설명 및 대응 절차 자동화**
- 보안 상담 Agent와 **연동 가능한 대응 가이드 생성 모듈 제공**
- 향후 공격 분류 모델 및 **다중 에이전트 시스템 확장성 확보**

이를 위해 다음 지식원을 활용한다.

- **MITRE ATT&CK Framework**
- **KISA 침해사고 대응 및 신고 절차 문서**

---

## 2. 코드 분류 및 역할

### 2.1 DB 생성 파이프라인

- `cli_build_db.py` : DB 구축 CLI 진입점  
- `scripts/build_db.py` : 전체 DB 구축 파이프라인  
- `ingest/mitre_crawl.py` : MITRE 크롤링  
- `ingest/kisa_report.py` : KISA 신고 절차 PDF 파싱  
- `ingest/kisa_guide.py` : KISA 대응 가이드 PDF 파싱  
- `utils/text.py` : 텍스트 분할 유틸  
- `utils/normalize.py` : 정규화 유틸  
- `vectordb/chroma_store.py` : Chroma 관리  
- `vectordb/embeddings.py` : 임베딩 헬퍼  

---

### 2.2 RAG 핵심 로직

- `rag_api.py` : RAG 진입점
- `retriever.py` : VectorDB 검색
- `generator.py` : LLM 응답 생성
- `rag_engine.py` : Retriever + Generator 결합
- `prompts.py` : 프롬프트 템플릿
- `web_search.py` : 최신 사례 검색


## 3. 출처

- MITRE ATT&CK Framework  
  https://attack.mitre.org/

- KISA 침해사고 대응 안내서 (개정본)

- KISA 훈련 분야별 대응 가이드  
  (공공데이터포털, 2025-06-30)


<!--
>  각자 브랜치 작업하는 방법
```bash

=======================================================
# 환경 세팅
# git 가져오고 해당 폴더 이동
git clone -b [브랜치명] [저장소 URL]
cd 'git폴더'

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/scripts/activate

# 의존성 파일 설치( pip install 한 패키지 requriements.txt에 추가해주세요)
# 추가하는법 ( python -c "import os; cur = set(open('requirements.txt').readlines()) if os.path.exists('requirements.txt') else set(); new = [l + '\n' for l in __import__('subprocess').check_output(['pip', 'freeze']).decode().splitlines() if l + '\n' not in cur]; open('requirements.txt', 'a').writelines(new)") 
python -m pip install --upgrade pip
pip install -r requirements.txt

#  pip install 한 패키지 requriements.txt에 추가해주세요)
python -c "import os; cur = set(open('requirements.txt').readlines()) if os.path.exists('requirements.txt') else set(); new = [l + '\n' for l in __import__('subprocess').check_output(['pip', 'freeze']).decode().splitlines() if l + '\n' not in cur]; open('requirements.txt', 'a').writelines(new)"

========================================================
# 작업세팅
# 새로운 브랜치 생성 및 이동
git checkout -b '브랜치 이름'

# 파일 새로 작성 후 변경된 모든 파일 스테이징
git add .

# 커밋 메시지 작성
git commit -m '커밋 내용'

# 원격 저장소(origin)의 해당 브랜치로 푸시
git push origin '브랜치 이름'

# 각자 feature 브랜치 업데이트된 내용 동기화
git checkout 'feature/(ui, ai, guide) or main'
git pull origin 'feature/(ui, ai, guide) or main'

# 현재 작업중인 branch 유지하면서 상위 브랜치 내용만 업데이트 하고싶은경우
git pull origin 'feature/(ui, ai, guide) or main'
```

> 각자 브랜치에서 작업 후에 feature/(ui, guide, ai)브랜치에 pull request 하고 파트별로 1명이 검토 후에 merge 하고
> main에는 최종으로 작업
-->

