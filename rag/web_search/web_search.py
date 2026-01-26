from typing import List
from openai import OpenAI

# urlparse :  URL을 구성요소로 나눠주는 표준 라이브러리 함수
# 파이썬 urllib.parse 모듈에 있고, URL에서 도메인만 추출할 때 자주 사용
from urllib.parse import urlparse\

from rag.configs.env import get_openai_api_key
from rag.configs.constants import TRUSTED_SOURCES


def build_web_search_query(label: str, techniques: List[str]) -> str:
    # techniques 리스트에서 최대 3개만 뽑아 검색어에 포함
    tech_part = " ".join(techniques[:3]) if techniques else ""

    # TRUSTED_SOURCES에 있는 URL에서 "도메인"만 추출
    # 예: "https://www.boannews.com/" -> "www.boannews.com"
    trusted_domains = []
    for src in TRUSTED_SOURCES:
        parsed = urlparse(src)
        domain = parsed.netloc or parsed.path
        domain = domain.strip("/")
        if domain:
            trusted_domains.append(domain)

    # 도메인 목록을 "site:도메인 OR site:도메인" 형태로 구성
    # 검색엔진이 이 도메인 안에서만 결과를 찾도록 제한 가능
    site_filters = " OR ".join([f"site:{d}" for d in trusted_domains]) if trusted_domains else ""

    # site: 필터가 있으면 검색어 뒤에 붙인다.
    if site_filters:
        return f"{label} {tech_part} attack campaign analysis ({site_filters})"

    # TRUSTED_SOURCES가 비어 있으면 기존 검색어만 사용한다.
    return f"{label} {tech_part} attack campaign analysis"

# label/techniques -> 검색 쿼리 생성 -> OpenAI web_search tool -> 문자열 반환
def collect_web_evidence(label: str, techniques: List[str], top_n: int = 3) -> str:
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
- {trusted_hint}에서만 검색 해줘
- 각 사례는 아래 포맷을 반드시 지켜줘 (top {top_n}개):
  - 제목: ...
    요약: ... (2~3문장)
    출처: URL (가능하면 게시/업데이트 연도/날짜)

출력은 반드시 bullet 형식으로만.
""".strip()

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",  # 웹서치용 모델은 단순 고정(설정 분산 방지)
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        text = (getattr(response, "output_text", "") or "").strip()
        return text if text else ""
    except Exception:
        # 선택 기능: 오류가 나도 전체 파이프라인은 유지
        return ""