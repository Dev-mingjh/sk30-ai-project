import argparse
import json
from typing import List

from llm.guide import generate_final_report


def _parse_anchors(s: str) -> List[str]:
    s = s.strip()
    if not s:
        return []
    if s.startswith("["):
        return list(json.loads(s))
    return [x.strip() for x in s.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="HighFive 대응가이드 생성 CLI")
    parser.add_argument("--label", required=True, help="모델이 분류한 공격 라벨 (예: Web Attack - Brute Force)")
    parser.add_argument("--anchors", default="", help='MITRE Technique IDs. 예: "T1110,T1059" 또는 \'["T1110"]\'')
    parser.add_argument("--query", required=True, help="상황 설명/로그 요약 (user_query)")
    parser.add_argument("--k-mitre", type=int, default=None, help="MITRE 검색 top-k (기본값은 constants.DEFAULT_TOP_K)")
    parser.add_argument("--k-kisa", type=int, default=None, help="KISA 검색 top-k (기본값은 constants.DEFAULT_TOP_K)")
    parser.add_argument("--no-web", action="store_true", help="웹서치 자동 보강 끄기")
    parser.add_argument("--web-top-n", type=int, default=3, help="웹 증거 몇 개 붙일지 (기본 3)")
    parser.add_argument("--model", default=None, help="LLM 모델명 (미지정 시 constants.DEFAULT_LLM_MODEL)")
    args = parser.parse_args()

    anchors = _parse_anchors(args.anchors)

    kwargs = {}
    if args.k_mitre is not None:
        kwargs["k_mitre"] = args.k_mitre
    if args.k_kisa is not None:
        kwargs["k_kisa"] = args.k_kisa
    if args.model is not None:
        kwargs["model"] = args.model

    result = generate_final_report(
        label=args.label,
        anchors=anchors,
        user_query=args.query,
        auto_web=(not args.no_web),
        web_top_n=args.web_top_n,
        **kwargs,
    )

    # result가 dict 형태로 리턴된다는 가정(현재 코드 주석상 Dict[str,Any] 형태)
    final_text = result.get("final_text") if isinstance(result, dict) else str(result)
    print(final_text)


if __name__ == "__main__":
    main()
