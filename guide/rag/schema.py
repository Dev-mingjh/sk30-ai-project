# JSONL -> Chroma 업서트 스키마 변환 모듈
from .configs.constants import LABEL_TO_KISA_CATEGORY
from .utils.normalize import normalize_label

# MITRE JSONL 항목들을 Chroma 업서트용 docs 리스트로 변환
def normalize_mitre(items: list[dict[str, object]]) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []

    for x in items:
        # labels 필드 호환 처리
        # - labels(list) / label(str) 혼재 가능
        labels = x.get("labels")
        if labels is None:
            labels = x.get("label")

        # labels를 CSV 문자열로 통일
        if isinstance(labels, list):
            labels_csv = ",".join(labels)
        elif labels:
            labels_csv = str(labels)
        else:
            labels_csv = ""

        # Chroma upsert용 문서 구성
        docs.append(
            {
                "id": x["chunk_id"],          # Chroma 문서 ID
                "text": x.get("text", ""),    # 임베딩 대상 본문
                "meta": {
                    "source": "MITRE_ATT&CK",
                    "technique_id": x.get("technique_id", ""),
                    "technique_title": x.get("technique_title", ""),
                    "section": x.get("section", ""),
                    "labels_csv": labels_csv,
                    "mitigation_id": x.get("mitigation_id", ""),
                    "mitigation_name": x.get("mitigation_name", ""),
                    "source_url": x.get("source_url", ""),
                },
            }
        )

    return docs

# KISA 신고절차 JSONL 항목들을 Chroma 업서트용 docs 리스트로 변환
def normalize_kisa(items: list[dict[str, object]]) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []

    for x in items:
        # 원본 라벨
        raw_label = x.get("label", "")

        # 라벨 정규화 (별칭/대소문자/표기 통일)
        norm_label = normalize_label(raw_label) if raw_label else raw_label

        # KISA 상위 카테고리 매핑
        kisa_category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")

        # page_no 안전 처리 (숫자 아니면 -1)
        raw_page = x.get("page_no", -1)
        page_no = int(raw_page) if str(raw_page).isdigit() else -1

        docs.append(
            {
                "id": x["chunk_id"],          # Chroma 문서 ID
                "text": x.get("text", ""),    # 임베딩 대상 본문
                "meta": {
                    "source": "KISA",
                    "label": norm_label,
                    "kisa_category": kisa_category,
                    "section": x.get("section", ""),
                    "page_no": page_no,
                    "source_doc": x.get("source_doc", ""),
                },
            }
        )

    return docs

# KISA 대응가이드 JSONL 항목을 Chroma 업서트용 docs 리스트로 변환
def normalize_kisa_guide(items: list[dict[str, object]]) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []

    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label

        raw_page = x.get("page_no", -1)
        page_no = int(raw_page) if str(raw_page).isdigit() else -1

        docs.append(
            {
                "id": x["chunk_id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "KISA_GUIDE",
                    "label": norm_label,
                    "section": x.get("section", "kisa_guide_response"),
                    "page_no": page_no,
                    "source_doc": x.get("source_doc", ""),
                },
            }
        )

    return docs