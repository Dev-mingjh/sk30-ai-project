# Retriever와 Generator를 묶어 RAG 파이프라인을 제공하는 엔진 모듈
from typing import Any, Dict, List, Optional

from .retriever import ChromaRetriever
from .generator import AnswerGenerator


class RAGEngine:
    """
    옵션 A 구현: retrieve() / generate()를 분리 제공 + answer()로 조합
    """

    def __init__(self, retriever: ChromaRetriever, generator: AnswerGenerator):
        self.retriever = retriever
        self.generator = generator

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        fallback: bool = True,
    ) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(query=query, top_k=top_k, where=where, fallback=fallback)

    def generate(
        self,
        question: str,
        contexts: List[Dict[str, Any]],
        system: Optional[str] = None,
    ) -> str:
        return self.generator.generate(question=question, contexts=contexts, system=system)

    def answer(
        self,
        question: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        fallback: bool = True,
    ) -> dict:
        ctxs = self.retrieve(question, top_k=top_k, where=where, fallback=fallback)
        answer = self.generate(question, ctxs) if ctxs else "문서 근거를 찾지 못했다."
        return {"answer": answer, "contexts": ctxs}
