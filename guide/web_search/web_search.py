# web/web_search.py
from __future__ import annotations

from typing import List

from openai import OpenAI

from configs.env import get_openai_api_key
from configs.constants import TRUSTED_SOURCES


def build_web_search_query(label: str, techniques: List[str]) -> str:
    tech_part = " ".join(techniques[:3]) if techniques else ""
    return f"{label} {tech_part} attack campaign analysis"

def collect_web_evidence(label: str, techniques: List[str], top_n: int = 3) -> str:
    """
    label/techniques -> 검색 쿼리 생성 -> OpenAI web_search tool -> 문자열 반환
    - 반환 포맷은 노트북에서 정의한 bullet 형식으로 출력되도록 유도
    - web-search는 '선택 기능'이므로, 실패 시 빈 문자열 반환(파이프라인 유지)
    """
    api_key = get_openai_api_key()
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)

    query = build_web_search_query(label, techniques)

    trusted_hint = ", ".join(TRUSTED_SOURCES)

    prompt = f"""
아래 검색 키워드로 웹 검색을 수행한 뒤, 최신 참고 사례 {top_n}개를 뽑아 요약해줘.

검색 키워드:
{query}

요구사항:
- 가능하면 신뢰 가능한 보안 기관/벤더/공식 문서를 우선으로 선택해줘.
- (가능하면) 아래 도메인/출처를 우선 고려해줘: {trusted_hint}
- 각 사례는 아래 포맷을 반드시 지켜줘 (top {top_n}개):
  - 제목: ...
    요약: ... (2~3문장)
    출처: URL (가능하면 게시/업데이트 연도/날짜)

출력은 반드시 bullet 형식으로만.
""".strip()

    try:
        response = client.responses.create(
            model="gpt-5",  # 웹서치용 모델은 단순 고정(설정 분산 방지)
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        text = (getattr(response, "output_text", "") or "").strip()
        return text if text else ""
    except Exception:
        # 선택 기능: 오류가 나도 전체 파이프라인은 유지
        return ""
