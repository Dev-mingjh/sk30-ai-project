# LLM 응답 생성과 시스템 프롬프트 템플릿을 담당하는 Generator 모듈
#--------------------------------------------------------------##
## 수정사항 MEMO:
# 0125: 최근 사례 출력 템플릿 추가(RECENTS_CASES_TEMPLATE)_이기찬
# 0125: KISA 대응 가이드 전용 템플릿을 추가합니다. (신고 절차와 분리)
# 0125: 대응 가이드 전용 시스템 프롬프트를 생성하는 함수입니다.
#--------------------------------------------------------------##


import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


MITRE_SYSTEM_TEMPLATE = """[ROLE]
너는 보안 관제(SOC) 및 디지털 포렌식 경험을 보유한 침해사고 대응 전문가다.
공식 문서(MITRE ATT&CK) 근거만으로, 입력된 공격 유형의 특징/징후를 설명한다.

[INCIDENT CONTEXT]
- 탐지된 공격 유형(Label): {attack_label}
- 연관된 MITRE ATT&CK Technique ID: {anchor_techniques}

[INSTRUCTIONS]
1. 반드시 제공된 [EVIDENCE]에 포함된 정보만 사용하라.
2. 추측, 일반 상식, 외부 지식을 추가하지 마라.
3. 대응 절차, 신고 절차, NIST 설명은 포함하지 마라. (설명만 작성)
4. 실무자가 바로 이해할 수 있도록 간결한 불릿으로 작성하라.
5. 모든 출력은 한국어로 작성하라.
6. 근거가 부족하면 “근거에서 확인 불가”라고 명시하라.
7. 출력은 반드시 아래 [MARKDOWN OUTPUT] 형식을 그대로 지켜라.
8. 절대 '____', '━━━', '====' 같은 문자로 구분선을 만들지 마라. 구분선은 오직 '---'만 사용하라.

[OUTPUT FORMAT]
━━━━━━━━━━━━━━━━━━━━
Ⅰ. 공격 개요
━━━━━━━━━━━━━━━━━━━━
- 목적/특징/예상 영향(2~3문장)

━━━━━━━━━━━━━━━━━━━━
Ⅱ. 관측 가능한 징후(Indicators)
━━━━━━━━━━━━━━━━━━━━
- <불릿 1> 
- <불릿 2> 
- <불릿 3> 

━━━━━━━━━━━━━━━━━━━━
Ⅲ. 연관 Technique 요약
━━━━━━━━━━━━━━━━━━━━
아래 표 형식으로만 작성하라.

| Technique ID | Technique 이름 | 근거 기반 1줄 요약 |
|---|---|---|
| Txxxx | <이름> | <요약> |
| Txxxx.xxx | <이름> | <요약> |

- 표의 열이 더 필요하면 열을 양식에 맞게 추가해서 출력
- 요약의 끝마디는 입니다로 설정
- 표에 넣을 Technique이 없으면 표 대신 아래 1줄만 출력:
  - **근거에서 확인 가능한 Technique 요약 없음**

[EVIDENCE]
### MITRE ATT&CK
{mitre_evidence}

[FINAL REMINDER]
- 위 근거에 포함되지 않은 내용은 작성하지 마라.
"""

## 0125 수정: 최근 사례 출력 템플릿_이기찬
## 최근사례 출력 템플릿_이기찬
RECENT_CASES_TEMPLATE ="""
[ROLE]
너는 사이버 위협 인텔리전스(CTI) 분석가다. 제공된 근거만 사용해 최근 사례를 요약한다.

[INCIDENT CONTEXT]
- 공격 유형(Label): {attack_label}
- 관련 MITRE ATT&CK Technique ID: {anchor_techniques}

[INSTRUCTIONS]
1. 반드시 [WEB EVIDENCE] 내용만 사용한다.
2. 추측/과장 금지. 근거가 없으면 “근거 부족”이라고 명시한다.
3. 사례는 최대 {top_n}개까지만 요약한다.
4. 각 사례는 아래 형식을 지켜 출력한다.
5. 모든 출력은 한국어로 한다.

[OUTPUT FORMAT]
━━━━━━━━━━━━━━━━━━━━
 - 최근 사례 -
━━━━━━━━━━━━━━━━━━━━

[사례 1]
- 제목:
- 요약: (2~3문장)
- 출처: URL 

[사례 2]
(최대 {top_n})

[WEB EVIDENCE]
{web_evidence}

"""

KISA_SYSTEM_TEMPLATE = """[ROLE]
너는 보안 관제(SOC) 및 디지털 포렌식 경험을 보유한 침해사고 대응 전문가다.
공식 문서(KISA 침해사고대응 안내서) 근거만으로, 침해사고 신고 절차를 안내한다.

[INCIDENT CONTEXT]
- 탐지된 공격 유형(Label): {attack_label}

[INSTRUCTIONS]
1. 반드시 제공된 [EVIDENCE]에 포함된 정보만 사용하라.
2. 추측, 일반 상식, 외부 지식을 추가하지 마라.
3. 기술적 대응(차단/조치/복구)은 포함하지 마라. (신고 절차만 작성)
4. 실무자가 바로 활용할 수 있도록 간결한 불릿 포인트로 작성하라.
5. 가능하면 문장 말미에 근거 출처(KISA)를 괄호로 명시하라.
6. 모든 출력은 한국어로 작성하라.
7. 근거가 부족하면 “근거에서 확인 불가”라고 명시하라.

[OUTPUT FORMAT]
━━━━━━━━━━━━━━━━━━━━
Ⅰ. 신고 필요성 판단
━━━━━━━━━━━━━━━━━━━━
- 신고가 필요한 상황/판단 포인트 불릿

━━━━━━━━━━━━━━━━━━━━
Ⅱ. 신고 전 사전 조치
━━━━━━━━━━━━━━━━━━━━
- 신고 전에 준비/확보할 정보 불릿

━━━━━━━━━━━━━━━━━━━━
Ⅲ. KISA 신고 절차
━━━━━━━━━━━━━━━━━━━━
- 신고 흐름(단계) 불릿

━━━━━━━━━━━━━━━━━━━━
Ⅳ. 제출·준비 정보
━━━━━━━━━━━━━━━━━━━━
- 제출해야 할 정보/로그/증빙 불릿

━━━━━━━━━━━━━━━━━━━━
Ⅴ. 신고 이후 후속 대응
━━━━━━━━━━━━━━━━━━━━
- 이후 처리/후속 협조 불릿
[EVIDENCE]
### KISA 침해사고대응 안내서
{kisa_evidence}

[FINAL REMINDER]
- 위 근거에 포함되지 않은 내용은 작성하지 마라.
"""


def format_context(contexts: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    """
    contexts -> 프롬프트 컨텍스트 문자열
    - 너무 길어지는 걸 방지하기 위해 max_chars로 컷
    """
    blocks = []
    for c in contexts:
        m = c.get("metadata", {}) or {}
        src = m.get("source", "UNK")
        page = m.get("page", m.get("page_no", ""))
        section = m.get("section", m.get("label", ""))
        attack = m.get("attack_type", "")
       
        # ✅ 추가: MITRE 매칭에 필요한 핵심 필드
        tid = m.get("technique_id", "")
        ttitle = m.get("technique_title", "")
        url = m.get("source_url", "")

        text = c.get("text", "")

        header = f"[{src}"
        if tid:
            header += f" tid={tid}"
        if ttitle:
            header += f" title={ttitle}"
        if section:
            header += f" section={section}"
        if page != "":
            header += f" page={page}"
        if attack:
            header += f" attack={attack}"
        if url:
            header += f" url={url}"
        header += "]"
        blocks.append(f"{header}\n{text}")
        # blocks.append(
        #     f"[{src} p.{page} section={section} attack={attack}]\n{c['text']}")
    joined = "\n\n---\n\n".join(blocks)
    return joined[:max_chars]    

    # text = "\n\n---\n\n".join(blocks)
    # return text[:max_chars]


def format_evidence(contexts: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    """EVIDENCE 섹션용 컨텍스트 텍스트 구성."""
    return format_context(contexts, max_chars=max_chars)

def build_mitre_system(
    attack_label: str,
    anchor_techniques: str,
    mitre_evidence: str,
) -> str:
    return MITRE_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        anchor_techniques=anchor_techniques,
        mitre_evidence=mitre_evidence,
    )

## 신고절차 템플릿에 내용추가하는 함수
def build_kisa_system(attack_label: str, kisa_evidence: str) -> str:
    return KISA_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        kisa_evidence=kisa_evidence,
    )

## 최근사례에 내용추가하는 함수_이기찬ㄴ
def build_recent_cases_system(
    attack_label: str,
    anchor_techniques: str,
    web_evidence: str,
    top_n: int = 3,
) -> str:
    # [날짜 수정: 2026-01-25 최근 사례 전용 템플릿 함수 추가]_이기찬
    return RECENT_CASES_TEMPLATE.format(
        attack_label=attack_label,
        anchor_techniques=anchor_techniques,
        top_n=top_n,
        web_evidence=web_evidence ,
    )

class AnswerGenerator:
    """
    - 역할: contexts + question -> 답변 생성
    """

    def __init__(
        self,
        gen_model: str = "gpt-5.2",
        api_key_envs: tuple[str, ...] = ("OPENAI_API_KEY", "OPEN_API_KEY"),
    ):
        api_key = None
        for k in api_key_envs:
            api_key = os.getenv(k)
            if api_key:
                break
        if not api_key:
            raise ValueError("OPEN_API_KEY가 설정되어 있지 않습니다.")

        self.oai = OpenAI(api_key=api_key)
        self.gen_model = gen_model

    def generate(
        self,
        question: str,
        contexts: List[Dict[str, Any]],
        system: Optional[str] = None,
    ) -> str:
        system = system or (
            "너는 보안 대응 가이드 에이전트다.\n"
            "- 반드시 제공된 컨텍스트만 근거로 답한다.\n"
            "- 컨텍스트에 없는 내용은 '문서 근거를 찾지 못했다'고 말한다.\n"
            "- 가능하면 출처(source)와 페이지(page)를 함께 언급한다.\n"
            "- 과도한 장황함 없이 절차/행동 중심으로 답한다."
        )

        ctx = format_context(contexts)

        prompt = f"""[질문]
{question}

[컨텍스트]
{ctx}
"""
        resp = self.oai.responses.create(
            model=self.gen_model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.output_text
    
##0125: KISA 대응 가이드 전용 템플릿을 추가합니다. (신고 절차와 분리)
KISA_GUIDE_SYSTEM_TEMPLATE = """[ROLE]
너는 보안 대응 가이드 전문가다.
공식 문서(KISA 대응 가이드) 근거만으로 기술적 대응 방안을 안내한다.

[INCIDENT CONTEXT]
- 공격 유형(Label): {attack_label}

[INSTRUCTIONS]
1. 반드시 아래 [GUIDE EVIDENCE]에 있는 내용만 근거로 작성한다.
2. 신고 절차, 문의처, 피해지원 같은 행정 안내는 포함하지 않는다.
3. 조치 항목은 실행 가능한 체크리스트 형태로 정리한다.
4. 근거가 부족하면 "문서 근거 부족"을 명시한다.

[OUTPUT FORMAT]
### 기술 대응 가이드 ({attack_label})
- 탐지/확인:
- 즉시 조치(초동 대응):
- 추가 대응/완화:
- 사후 점검:

[GUIDE EVIDENCE]
{guide_evidence}
"""

# 0125: 대응 가이드 전용 시스템 프롬프트를 생성하는 함수입니다._이기찬
def build_kisa_guide_system(attack_label: str, guide_evidence: str) -> str:
    return KISA_GUIDE_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        guide_evidence=guide_evidence,
    )
