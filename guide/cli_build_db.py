import argparse
from pathlib import Path

from rag.configs.env import load_env
from rag.scripts.build_db import build_vector_db
from rag.configs.constants import (
    DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR,
    COLLECTION_MITRE,
    COLLECTION_KISA_REPORT,
    COLLECTION_KISA_GUIDE,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Chroma DB for RAG (MITRE / KISA report / KISA guide) using unified collections."
    )

    parser.add_argument(
        "--chroma-dir",
        default=str(Path(DEFAULT_OUT_DIR) / DEFAULT_CHROMA_SUBDIR),
        help="Chroma persistent directory (default: constants DEFAULT_OUT_DIR/DEFAULT_CHROMA_SUBDIR).",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path(DEFAULT_OUT_DIR)),
        help="Directory to store intermediate JSONL files (default: constants DEFAULT_OUT_DIR).",
    )
    parser.add_argument(
        "--kisa-report-pdf",
        default=str(Path(__file__).resolve().parent / "rag" / "assets" / "kisa_report.pdf"),
        help="Path to KISA report PDF (default: rag/assets/kisa_report.pdf).",
    )
    parser.add_argument(
        "--kisa-guide-pdf",
        default=str(Path(__file__).resolve().parent / "rag" / "assets" / "kisa_guide.pdf"),
        help="Path to KISA guide PDF (default: rag/assets/kisa_guide.pdf).",
    )
    parser.add_argument(
        "--mitre-collection",
        dest="mitre_collection",
        default=COLLECTION_MITRE,
        help=f"MITRE collection name (default: {COLLECTION_MITRE}).",
    )
    parser.add_argument(
        "--kisa-report-collection",
        dest="kisa_report_collection",
        default=COLLECTION_KISA_REPORT,
        help=f"KISA report collection name (default: {COLLECTION_KISA_REPORT}).",
    )
    parser.add_argument(
        "--kisa-guide-collection",
        dest="kisa_guide_collection",
        default=COLLECTION_KISA_GUIDE,
        help=f"KISA guide collection name (default: {COLLECTION_KISA_GUIDE}).",
    )

    args = parser.parse_args()

    load_env()

    # build_vector_db 내부에서 Chroma 초기화 + 업서트까지 수행
    build_vector_db(
        pdf_path=args.kisa_report_pdf,
        pdf_path2=args.kisa_guide_pdf,
        out_dir=args.out_dir,
        chroma_path=args.chroma_dir,
        mitre_collection=args.mitre_collection,
        kisa_report_collection=args.kisa_report_collection,
        kisa_guide_collection=args.kisa_guide_collection,
    )

    print(f"Chroma DB created at: {args.chroma_dir}")

    # 정확한 문서 개수 출력을 위해 Chroma 컬렉션을 다시 열기
    try:
        from rag.vectordb.chroma_store import init_chroma

        _, col_mitre, col_kisa_report, col_kisa_guide = init_chroma(
            args.chroma_dir,
            mitre_collection=args.mitre_collection,
            kisa_report_collection=args.kisa_report_collection,
            kisa_guide_collection=args.kisa_guide_collection,
        )
        print(f"MITRE docs: {col_mitre.count()} -> {args.mitre_collection}")
        print(f"KISA REPORT docs: {col_kisa_report.count()} -> {args.kisa_report_collection}")
        print(f"KISA GUIDE docs: {col_kisa_guide.count()} -> {args.kisa_guide_collection}")

    except Exception as e:
        print("[WARN] reopen count failed:", e)
        print(f"MITRE collection: {args.mitre_collection}")
        print(f"KISA REPORT collection: {args.kisa_report_collection}")
        print(f"KISA GUIDE collection: {args.kisa_guide_collection}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
