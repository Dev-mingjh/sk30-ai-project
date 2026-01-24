# LLM 응답 생성과 시스템 프롬프트 템플릿을 담당하는 Generator 모듈
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

[OUTPUT FORMAT]
━━━━━━━━━━━━━━━━━━━━
Ⅰ. 공격 개요
━━━━━━━━━━━━━━━━━━━━
- 목적/특징/예상 영향(2~3문장)

━━━━━━━━━━━━━━━━━━━━
Ⅱ. 관측 가능한 징후(Indicators)
━━━━━━━━━━━━━━━━━━━━
- 로그/트래픽/행동 단서 위주 불릿

━━━━━━━━━━━━━━━━━━━━
Ⅱ. 연관 Technique 요약
━━━━━━━━━━━━━━━━━━━━
- Technique ID: 요약(1줄) (MITRE)

[EVIDENCE]
### MITRE ATT&CK
{mitre_evidence}

[FINAL REMINDER]
- 위 근거에 포함되지 않은 내용은 작성하지 마라.
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

        blocks.append(
            f"[{src} p.{page} section={section} attack={attack}]\n{c['text']}"
        )

    text = "\n\n---\n\n".join(blocks)
    return text[:max_chars]


def format_evidence(contexts: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    """EVIDENCE 섹션용 컨텍스트 텍스트 구성."""
    return format_context(contexts, max_chars=max_chars)


def build_mitre_system(attack_label: str, anchor_techniques: str, mitre_evidence: str) -> str:
    return MITRE_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        anchor_techniques=anchor_techniques,
        mitre_evidence=mitre_evidence,
    )


def build_kisa_system(attack_label: str, kisa_evidence: str) -> str:
    return KISA_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        kisa_evidence=kisa_evidence,
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
