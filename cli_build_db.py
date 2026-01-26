import argparse
from pathlib import Path

from rag.configs.env import load_env
from rag.scripts.build_db import build_vector_db
from rag.configs.constants import (
    DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR,
    COLLECTION_MITRE,
    COLLECTION_KISA,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Chroma DB for RAG (MITRE/KISA) using unified collections."
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
        "--kisa-pdf",
        default=str(Path(__file__).resolve().parent / "rag" / "assets" / "kisa 신고절차.pdf"),
        help="Path to KISA PDF (default: rag/assets/kisa 신고절차.pdf).",
    )

    parser.add_argument(
        "--mitre-collection",
        default=COLLECTION_MITRE,
        help=f"MITRE collection name (default: {COLLECTION_MITRE}).",
    )
    parser.add_argument(
        "--kisa-collection",
        default=COLLECTION_KISA,
        help=f"KISA collection name (default: {COLLECTION_KISA}).",
    )

    args = parser.parse_args()

    load_env()

    if args.mitre_collection in ("mitre", "mitre_chunk", "mitre_docs"):
        args.mitre_collection = COLLECTION_MITRE
    if args.kisa_collection in ("kisa", "kisa_chunk", "kisa_docs"):
        args.kisa_collection = COLLECTION_KISA

    # build_vector_db 내부에서 Chroma 초기화 + 업서트까지 수행
    build_vector_db(
        pdf_path=args.kisa_pdf,
        out_dir=args.out_dir,
        chroma_path=args.chroma_dir,
        mitre_collection=args.mitre_collection,
        kisa_collection=args.kisa_collection,
    )

    print(f"Chroma DB created at: {args.chroma_dir}")

    # 정확한 문서 개수 출력을 위해 Chroma 컬렉션을 다시 열기
    try:
        from rag.vectordb.chroma_store import init_chroma

        _, col_mitre, col_kisa = init_chroma(
            args.chroma_dir,
            mitre_collection=args.mitre_collection,
            kisa_collection=args.kisa_collection,
        )
        print(f"MITRE docs: {col_mitre.count()} -> {args.mitre_collection}")
        print(f"KISA docs: {col_kisa.count()} -> {args.kisa_collection}")
    except Exception:
        print(f"MITRE collection: {args.mitre_collection}")
        print(f"KISA collection: {args.kisa_collection}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())