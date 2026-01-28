# LLM 응답 생성 담당 Generator 모듈
from openai import OpenAI

from rag.configs.env import get_openai_api_key
from rag.configs.constants import DEFAULT_LLM_MODEL 

from rag.prompts import MITRE_SYSTEM_TEMPLATE, KISA_SYSTEM_TEMPLATE, RECENT_CASES_TEMPLATE, KISA_GUIDE_SYSTEM_TEMPLATE

# contexts -> 프롬프트 컨텍스트 문자열
# - 너무 길어지는 걸 방지하기 위해 max_chars로 컷
def format_context(contexts: list[dict[str, object]], max_chars: int = 12000) -> str:
    blocks: list[str] = []
    for c in contexts:
        m_obj = c.get("metadata") if isinstance(c, dict) else None
        m = m_obj if isinstance(m_obj, dict) else {}

        src = m.get("source", "UNK")
        page = m.get("page", m.get("page_no", ""))
        section = m.get("section", m.get("label", ""))
        attack = m.get("attack_type", "")

        # MITRE 매칭에 필요한 핵심 필드
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

    joined = "\n\n---\n\n".join(blocks)
    return joined[:max_chars]


# evidence 섹션용 컨텍스트 텍스트 구성
def format_evidence(contexts: list[dict[str, object]], max_chars: int = 12000) -> str:
    return format_context(contexts, max_chars=max_chars)


def build_mitre_system(attack_label: str, anchor_techniques: str, mitre_evidence: str) -> str:
    return MITRE_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        anchor_techniques=anchor_techniques,
        mitre_evidence=mitre_evidence,
    )


def build_kisa_report_system(attack_label: str, kisa_evidence: str) -> str:
    return KISA_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        kisa_evidence=kisa_evidence,
    )

def build_kisa_guide_system(attack_label: str, guide_evidence: str) -> str:
    return KISA_GUIDE_SYSTEM_TEMPLATE.format(
        attack_label=attack_label,
        guide_evidence=guide_evidence,
    )

def build_recent_cases_system(
    attack_label: str,
    anchor_techniques: str,
    web_evidence: str,
    top_n: int = 3,
) -> str:
    return RECENT_CASES_TEMPLATE.format(
        attack_label=attack_label,
        anchor_techniques=anchor_techniques,
        top_n=top_n,
        web_evidence=web_evidence or "- 근거 부족",
    )

# contexts + question -> 답변 생성
class AnswerGenerator:
    def __init__(self, gen_model: str = DEFAULT_LLM_MODEL):
        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError("OPENAI_API_KEY(또는 OPEN_API_KEY)가 .env에 설정되어 있지 않습니다.")

        self.openai = OpenAI(api_key=api_key)
        self.gen_model = gen_model

    def generate(
        self,
        question: str,
        contexts: list[dict[str, object]],
        system: str | None = None,
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

        response = self.openai.responses.create(
            model=self.gen_model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.output_text
