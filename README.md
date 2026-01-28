
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

> 추가적인 환경 설정
```
## **환경 변수**
**`.env`** 파일에 OPENAI_API_KEY 관리하세요
OPENAI_API_KEY=your_key_here
```
# **프로젝트 주제**

네트워크 로그 파일을 업로드하면 머신러닝 모델이 위협을 자동 분류 하고 AI 보안 에이전트가 분류된 공격에 대한 상세 설명 및 기술적 대응 가이드를 제공하는 챗봇 시스템

## **프로그램 구성**

- Model Agent + Guide Agent + UI Agent (3개의 에이전트로 구성)
- Model: 네트워크 로그 공격/정상 데이터 분류
- Guide: 벡터DB를 통해 공격에 대한 가이드 제공
- UI: 챗봇 형태로 Model/Guide Agent 결과 사용자에게 제공

## **프로그램 시연 영상**
https://github.com/user-attachments/assets/47e2fb48-d5e7-4818-9346-d38bef83c59a

---

# **GUIDE AGENT (공격 대응 가이드)**

MITRE ATT&CK, KISA 보고서/가이드 문서를 기반으로 공격 유형 설명, 신고 절차, 최근 사례 요약,

대응 가이드를 제공하는 RAG 챗봇입니다. Streamlit UI로 대화형 질의응답을 제공합니다.

## **주요 기능**

- 공격 유형(예: DDoS, PortScan) 설명 생성
- KISA 신고 절차 생성
- 웹 검색 기반 최근 사례 요약
- KISA 대응 가이드 요약
- Streamlit 챗봇 UI 제공

## 코드 분류 (UI/Infer/Guide/Analyze)


## **디렉터리 구조**

```python
agent_guide_1/
├─ README.txt                # 간단한 안내 문서(기존)
├─ cli_build_db.py            # Chroma 벡터 DB 구축 CLI
├─ streamlit_app.py           # Streamlit 챗봇 UI 및 대화 플로우
├─ rag/
│  ├─ assets/                 # KISA 보고서/가이드 PDF 등 원본 문서
│  ├─ configs/
│  │  ├─ __init__.py           # configs 패키지 초기화
│  │  ├─ constants.py          # 모델/컬렉션/라벨/키워드 상수 정의
│  │  └─ env.py                # .env 로딩 및 API 키 조회
│  ├─ ingest/                 # 문서 전처리/청크 생성 로직
│  ├─ scripts/                # 벡터 DB 구축/유틸 스크립트
│  ├─ utils/                  # 공용 유틸 함수 모음
│  ├─ vectordb/               # Chroma 벡터 스토어 초기화/연동
│  ├─ web_search/
│  │  ├─ __init__.py           # web_search 패키지 초기화
│  │  └─ web_search.py         # OpenAI web_search 기반 최신 사례 수집
│  ├─ generator.py            # LLM 응답 생성기
│  ├─ prompts.py              # 시스템 프롬프트 템플릿
│  ├─ rag_engine.py           # Retriever + Generator 결합 엔진
│  ├─ retriever.py            # Chroma Retriever 구현
│  └─ schema.py               # 데이터 스키마 정의                
├─ created_DB/                # (생성됨) Chroma 저장 경로       
│  ├─ chroma_db
│  │  ├─ db폴더 1
│  │  ├─ db폴더 2
│  │  └─ db폴더 3 
│  ├─ kisa_guide_chunks.jsonl
│  ├─ kisa_report_chunks.jsonl
│  └─ mitre_chunks.jsonl 
```
## 코드 분류 (DB 생성 / RAG / 파이프라인)

### 1) DB 생성 관련 코드

벡터 DB를 구축하고 문서를 전처리/청크화하여 Chroma에 업서트하는 영역입니다.

---

- `cli_build_db.py`: DB 구축 CLI 진입점. 환경 변수 로딩 후 DB 구축 함수 호출.
- `rag/scripts/build_db.py`: DB 구축 전체 파이프라인(수집→청크→임베딩→업서트).
- `rag/ingest/mitre_crawl.py`: MITRE ATT&CK 수집 및 정규화 로직.
- `rag/ingest/kisa_report.py`: KISA 보고서 PDF 파싱 및 정규화.
- `rag/ingest/kisa_guide.py`: KISA 대응 가이드 PDF 파싱 및 정규화.
- `rag/utils/text.py`: 텍스트 분할/전처리 유틸(청크 생성에 사용).
- `rag/utils/normalize.py`: 라벨/텍스트 정규화 유틸.
- `rag/vectordb/chroma_store.py`: Chroma 초기화/컬렉션 생성/업서트.
- `rag/vectordb/embeddings.py`: 임베딩 모델 래퍼/헬퍼.

---

### 2) RAG 관련 코드

---

검색(Retrieval)과 생성(Generation)을 담당하는 핵심 구성요소입니다.

---

- `rag/retriever.py`: Chroma 기반 문서 검색기.
- `rag/generator.py`: LLM 응답 생성기.
- `rag/rag_engine.py`: Retriever + Generator 결합 엔진.
- `rag/prompts.py`: 시스템 프롬프트 템플릿 모음.
- `rag/schema.py`: 문서/청크 관련 스키마 정의.
- `rag/web_search/web_search.py`: 웹 검색 기반 최신 사례 증거 수집.

---

## 3) 파이프라인/앱 코드

---

사용자 요청을 받아 흐름을 제어하고, RAG를 호출하는 실행 레이어입니다.

---

- `streamlit_app.py`: Streamlit UI, 대화 상태 관리, 질문 분기 로직.

---

### 코드 설명

- DB 생성 실행 : cli_build_db.py
    - 호출하는 모듈 역할
        - **env.py**
            - load_env()가 .env 위치를 찾아 로드하고, OPEN_API_KEY가 있으면 OPENAI_API_KEY로 매핑합니다.
            - 파일: env.py
        - **constants.py**
            - 기본 모델, 컬렉션 이름, 출력 폴더명 등 상수 정의.
            - cli_build_db.py는 기본 경로와 컬렉션 이름을 이 상수로 채웁니다.
            - 파일: constants.py
        - **build_db.py**
            - **build_vector_db()**가 실제 DB 생성 파이프라인의 엔트리입니다. 흐름은 다음과 같습니다.
                1. **문서 수집/청크 생성**
                    - build_mitre_chunks() (MITRE ATT&CK)
                    - build_kisa_chunks() (KISA report PDF)
                    - build_kisa_guide_chunks() (KISA guide PDF)
                2. **JSONL 저장/로드**
                    - save_jsonl()로 .jsonl 생성
                    - load_jsonl()로 다시 읽어 처리
                3. **스키마 정규화 + 중복 제거**
                    - normalize_mitre(), normalize_kisa(), normalize_kisa_guide()
                    - dedup_docs_by_id()로 문서 ID 중복 제거
                    - assert_unique_ids()로 중복 체크 로그 출력
                4. **Chroma 초기화 + 업서트**
                    - init_chroma()로 컬렉션 생성/연결
                    - upsert_to_chroma()로 벡터 업서트
            - 파일: build_db.py
        - **rag/ingest/***
            - PDF/웹 문서를 가져와 **청크**로 만드는 모듈들.
            - build_mitre_chunks()는 MITRE 데이터 수집/청크화
            - build_kisa_chunks()는 KISA 보고서 PDF 파싱
            - build_kisa_guide_chunks()는 KISA 가이드 PDF 파싱
            - 파일:
                - **mitre_crawl.py**
                - **kisa_report.py**
                - **kisa_guide.py**
        - **schema.py**
            - normalize_* 함수들이 RAG 입력 포맷(텍스트, 메타데이터, ID)을 통일합니다.
            - 파일: schema.py
        - **chroma_store.py**
            - init_chroma()에서 Chroma DB 연결/컬렉션 준비
            - upsert_to_chroma()에서 문서 벡터 업서트 처리
            - 파일: chroma_store.py

---

- **rag_api 개요**
    - 목적: 여러 모듈(retriever/generator/rag_engine/web_search/configs)을 한 곳에서 조립해 “간단한 RAG API 레이어”로 제공
    - 특징: streamlit_app 쪽에서 여러 모듈을 직접 import 하던 걸 감춰서, RagBundle + answer_* 함수만으로 질의 가능
    
    **사용하는 모듈과 역할**
    
- retriever.py
    - ChromaRetriever 사용
    - Chroma 컬렉션에서 관련 컨텍스트 검색 담당
- generator.py
    - AnswerGenerator로 LLM 응답 생성
    - build_*_system 함수들로 시스템 프롬프트 템플릿 구성
    - format_evidence로 검색 결과를 증거 텍스트로 포맷
- rag_engine.py
    - RAGEngine: retriever + generator를 묶은 실행 유닛
    - retrieve / generate 파이프라인 단순화
- web_search.py
    - collect_web_evidence: 최신 사례(웹) 근거 수집
- env.py
    - load_env: 환경 변수 로딩
- constants.py
    - 기본 모델/컬렉션 이름/라벨 맵/가족 맵 등 공통 상수 사용

**핵심 데이터 구조**

- RagBundle (dataclass)
    - rag_mitre, rag_kisa_report, rag_kisa_guide: 각각 MITRE/KISA Report/KISA Guide 전용 RAGEngine
    - embed_model, gen_model: 임베딩/생성 모델 이름
    - chroma_dir, collection_*: Chroma 경로/컬렉션 이름

**주요 함수 상세**

- create_rag_bundle(...) -> RagBundle
    - 역할: 환경 변수 + 기본 상수로 ChromaRetriever 3개와 AnswerGenerator를 생성하고, RAGEngine 3개를 묶어 반환
    - 동작:
        - load_env() 호출로 환경 변수 적용
        - DEFAULT_OUT_DIR/DEFAULT_CHROMA_SUBDIR로 기본 Chroma 경로 구성
        - 컬렉션 이름은 env(COLLECTION_*) 우선, 없으면 상수 사용
        - OPENAI_EMBED_MODEL, OPENAI_GEN_MODEL 환경 변수 우선 적용
- extract_attack_type(text: str) -> Optional[str]
    - 역할: 입력 문장에서 ATTACK_LABELS에 포함된 공격 유형을 단순 매칭
    - 동작: 소문자 비교로 라벨 포함 여부 확인
- map_attack_family(label: str) -> str
    - 역할: 공격 라벨을 상위 패밀리명으로 변환
    - 동작: ATTACK_FAMILY_MAP에 있으면 매핑, 없으면 원본 반환
- answer_mitre_explain(bundle, attack_label, question=None, top_k=None) -> dict
    - 목적: MITRE 기반 공격 설명 생성
    - 동작:
        - LABEL_TO_ATTACK에서 anchor_techniques를 추출
        - 각 technique에 대해 섹션 필터(Description/Detection/Mitigations/Procedure Examples)로 검색
        - 결과 없으면 기본 질의로 fallback 검색
        - build_mitre_system + format_evidence로 프롬프트 구성 후 생성
- answer_kisa_report(bundle, attack_label, question=None, top_k=None) -> dict
    - 목적: KISA 보고서 기반 대응 요약
    - 동작:
        - DDoS이면 라벨 기반 섹션 필터, 그 외는 incident_response_guide 섹션만 검색
        - build_kisa_system으로 프롬프트 구성 후 생성
- answer_kisa_guide(bundle, attack_label, question=None, top_k=6) -> dict
    - 목적: KISA 가이드 행동 요약
    - 동작:
        - 공격 라벨을 패밀리로 변환 후 질의
        - kisa_guide_response 섹션만 검색
        - build_kisa_guide_system으로 프롬프트 구성 후 생성
- answer_recent_cases(bundle, attack_label, question=None, top_n=2) -> dict
    - 목적: 최신 사례 요약 (웹)
    - 동작:
        - collect_web_evidence로 웹 증거 수집
        - build_recent_cases_system으로 프롬프트 구성
        - RAG 검색 없이 generator만 사용

**입출력 형태 (공통)**

- 반환 dict: {"answer": str, "contexts": list, "question": str}
- contexts는 retriever 결과 원문 및 메타 포함

---

# **UI AGENT 설명**

사용자와 시스템 사이의 접점인 Web UI를 관리하며, 전체적인 서비스 워크플로우를 설계하고 제어한다. 단순히 인터페이스를 제공하는 것에 그치지 않고, 사용자 입력의 의도를 파악하여 적절한 내부 
모듈(분석 모델, Guide Agent 등)로 연결하고 결과를 시각화하여 전달하는 중추적인 역할을 담당한다

## **주요 기능**

- 통합 인터페이스 제공: 사용자와의 대화 및 데이터 업로드를 관리하는 단일 접점(Single Point of Contact) 역할을 수행
- 지능형 워크플로우 제어: 사용자의 의도에 따라 로그 분석 모델(Infer)과 대응 가이드 에이전트(Guide)를 유기적으로 연결
- 분석 데이터의 직관적 시각화: 복잡한 네트워크 로그 분석 결과를 비전문가도 이해하기 쉬운 리포트와 그래프 형태로 가공하여 전달
- 대화 맥락 유지를 통한 연속적 상담: 세션 상태 관리를 통해 파일 분석부터 상세 대응 가이드 요청까지 끊김 없는 사용자 경험을 보장

## UI Agent Flow Diagram
<img width="700" height="600" alt="Image" src="https://github.com/user-attachments/assets/a29bc5a2-6518-4f61-8cd0-c128df31e4f7" />

## 코드 분류 및 UI 로직 구성

###  `ui.py`  
**메인 보안 상담 에이전트 및 화면 구성 (Streamlit UI)**

보안 상담 Agent의 UI와 사용자 인터랙션 전반을 담당하는 핵심 모듈이다.  
채팅 기반 상담, 로그 파일 업로드, 모델 예측 결과 시각화, RAG 호출까지의 전체 흐름을 관리한다.

#### 주요 함수 및 역할

- **`init_settings`**
  - 웹 페이지 레이아웃을 `wide` 모드로 설정
  - 세션 상태 초기화 (`messages`, `df`, `last_processed_file` 등)
  - 침입 탐지 모델 로드 수행

- **`apply_custom_css`**
  - 헤더 디자인
  - 파일 업로더 영역 압축
  - 전체 UI 스타일 개선을 위한 CSS 적용

- **`set_chat_upload`**
  - 채팅 기반 UI의 핵심 로직
  - 사용자 메시지 입력과 로그 파일 업로드를 동시에 처리
  - 파일 업로드 시 다음 파이프라인 실행  
    → 모델 예측  
    → 결과 시각화  
    → 요약 메시지 출력

- **`display_chat_messages`**
  - 세션에 저장된 채팅 메시지를 순차적으로 렌더링
  - 공격 분포 그래프 및 CSV 다운로드 버튼 표시

- **`handle_input`**
  - OpenAI Function Calling을 활용하여 사용자 입력 의도 분석
  - 입력 유형에 따라 다음 기능으로 분기 처리
    - 로그 분석 (`analyze`)
    - RAG 기반 설명 / 가이드 / 신고 절차 / 사례 조회

- **`execute_chatbot`**
  - UI 애플리케이션의 메인 실행 함수
  - 실행 흐름:
    1. 초기화
    2. CSS 적용
    3. 헤더 구성
    4. 채팅/파일 업로드 UI
    5. 사이드바
    6. 푸터

- **`load_bundle`**
  - VectorDB 및 임베딩 모델을 포함한 RAG 번들 초기화
  - 캐싱 처리로 반복 호출 시 성능 저하 방지

- **`TOOLS / FUNCTION_MAP`**
  - OpenAI Function Calling에 사용되는 도구 정의
  - 실제 RAG API 함수와의 매핑 관리
    - MITRE ATT&CK 설명
    - KISA 대응 가이드
    - KISA 신고 절차
    - 최근 공격 사례

- **`typewriter_markdown`**
  - AI 응답을 일정 단위로 분할 출력
  - 실제 사람이 타이핑하는 것처럼 보이게 하는 UX 핵심 기능

- **`visualize_attack_counts`**
  - 공격 유형 분포를 `matplotlib` 기반 그래프로 생성
  - PNG → base64 변환 후 채팅 UI에 삽입

---

###  `infer.py`  
**네트워크 로그 분석 모델 연동**

CICIDS 기반 침입 탐지 모델을 로드하고, 사용자 로그 데이터를 전처리·예측하는 역할을 담당한다.

#### 주요 함수 및 역할

- **`_load_model`**
  - RandomForest 기반 침입 탐지 모델  
    (`cicids2017_rf_model_v2.pkl`) 로드
  - 싱글톤 패턴 적용으로 UI 실행 중 중복 로딩 방지

- **`get_required_columns`**
  - Pipeline 및 `ColumnTransformer` 정보를 기반으로
  - 모델 학습 시 사용된 입력 특징(feature) 목록 추출

- **`prepare_X`**
  - 사용자 로그 DataFrame 전처리
  - 불필요한 컬럼 제거
  - 모델 입력 구조에 맞게 컬럼 정렬
  - 누락 컬럼은 0으로 채움
  - `Protocol` 타입 변환 수행

- **`add_pred_column`**
  - 전처리된 입력 데이터를 기반으로 공격 유형 예측
  - 각 로그 행에 다음 컬럼 추가
    - `attack_type`
    - 클래스별 예측 확률 (`prob_*`)

---

### `guide.py`  
**RAG 기반 보안 상담 로직**

VectorDB 검색과 LLM 생성을 결합하여 공격 유형별 보안 가이드를 생성한다.

#### 주요 함수

- **`run_explain`**
  - MITRE ATT&CK 기반 공격 유형 설명 생성

- **`run_report`**
  - KISA 침해사고 신고 및 행정 대응 절차 생성

- **`run_recent_cases`**
  - 웹 검색 기반 최근 공격 사례 요약

- **`run_guide`**
  - KISA 대응 가이드 기반 기술·운영 대응 절차 생성

---

###  `analyze.py`  
**업로드 로그 통계 분석 모듈**

사용자가 업로드한 로그 데이터를 정량적으로 분석하여 공격 특성을 도출한다.

#### 주요 함수 및 역할

- **`analyze_user_file_stats`**
  - 세션에 저장된 사용자 로그 데이터를 기반으로 분석 수행
  - 특정 공격 유형과 정상 트래픽을 비교 분석

#### 분석 지표

- Flow Duration
- Flow Bytes/s
- Flow Packets/s
- Avg Packet Size

각 지표에 대해 평균값 및 최대값을 계산하여 공격 특성을 정량화한다.

- **`ANALYZE_TOOLS`**
  - OpenAI Function Calling에서  
    “내 파일 분석” 요청을 처리하기 위한 전용 분석 도구 정의

---



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

