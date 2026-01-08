"""
RAG 모드: 코드북 + 영업일지 검색 엔진
"""
import google.generativeai as genai
from typing import List, Tuple, Dict
from dataclasses import dataclass

from config import GOOGLE_API_KEY
from data_loader import Document
from vector_store import VectorStore


# Google Gemini API 설정
genai.configure(api_key=GOOGLE_API_KEY)


@dataclass
class RAGResult:
    """RAG 결과"""
    answer: str
    sources: List[Tuple[Document, float]]
    context_used: str


class RAGEngine:
    """RAG 검색 및 답변 생성 엔진 (코드북 + 영업일지 전용)"""

    def __init__(self, vector_store: VectorStore):
        """
        Args:
            vector_store: VectorStore 인스턴스 (RAG용으로 빌드된 것)
        """
        self.vector_store = vector_store
        self.llm = genai.GenerativeModel('gemini-2.5-flash')

    def search_and_generate(
        self, query: str, top_k: int = 5
    ) -> RAGResult:
        """
        RAG 검색 및 답변 생성

        Args:
            query: 사용자 질문
            top_k: 검색할 문서 수

        Returns:
            RAGResult
        """
        print(f"\n🤖 RAG 모드: 벡터 검색 + LLM 생성")
        print(f"  질문: {query}")
        print(f"  Top-K: {top_k}")

        # 1. 벡터 검색 (코드북 + 영업일지에서만)
        sources = self.vector_store.search(query, top_k=top_k)
        print(f"  검색 결과: {len(sources)} 개 문서")

        # 2. 컨텍스트 구성
        context = self._build_context(sources)

        # 3. LLM 답변 생성
        answer = self._generate_answer(query, context, sources)

        return RAGResult(
            answer=answer,
            sources=sources,
            context_used=context
        )

    def _build_context(self, sources: List[Tuple[Document, float]]) -> str:
        """검색 결과에서 컨텍스트 구성"""
        context_parts = []

        context_parts.append("=== 검색된 관련 문서 ===\n")

        for i, (doc, score) in enumerate(sources, 1):
            context_parts.append(f"[문서 {i}] (유사도: {score:.4f})")
            context_parts.append(f"출처: {doc.metadata.get('source', 'N/A')}")

            # 텍스트 미리보기 (최대 300자)
            text_preview = doc.text[:300]
            context_parts.append(text_preview)
            context_parts.append("")

        return "\n".join(context_parts)

    def _generate_answer(
        self, query: str, context: str, sources: List[Tuple[Document, float]]
    ) -> str:
        """LLM을 사용하여 답변 생성"""
        print("  🤖 LLM 답변 생성 중...")

        # 프롬프트 구성
        prompt = f"""당신은 한국어 비즈니스 데이터 분석 전문가입니다.

아래 문서들을 바탕으로 사용자의 질문에 답변해주세요.

사용자 질문: {query}

관련 문서:
{context}

답변 작성 지침:
1. 제공된 문서의 정보만을 기반으로 답변하세요.
2. 한국어로 답변하세요.
3. 코드북 정보라면 항목의 정의와 설명을 명확히 제시하세요.
4. 영업일지 정보라면 날짜, 거래처, 활동 내용을 구체적으로 설명하세요.
5. 구체적인 내용을 언급할 때는 출처(문서 번호)를 표시하세요.
6. 정보가 부족하여 답변할 수 없다면 솔직히 말씀해주세요.
7. 근거가 명확하지 않은 추측은 하지 마세요.

답변:"""

        try:
            # Gemini API 호출
            response = self.llm.generate_content(prompt)
            answer = response.text

            return answer

        except Exception as e:
            print(f"✗ 답변 생성 실패: {e}")
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {e}"

    def format_sources(self, sources: List[Tuple[Document, float]]) -> str:
        """출처 정보 포맷팅"""
        if not sources:
            return "출처 정보가 없습니다."

        source_parts = []
        source_parts.append("## 📚 근거 및 출처")
        source_parts.append("")

        for i, (doc, score) in enumerate(sources, 1):
            source_parts.append(f"### [{i}] {doc.metadata.get('source', 'N/A')} (유사도: {score:.4f})")

            # 문서 텍스트 미리보기
            preview = doc.text[:200].replace('\n', ' ')
            source_parts.append(f"```\n{preview}...\n```\n")

        return "\n".join(source_parts)


if __name__ == "__main__":
    # 테스트
    from data_loader import DataLoader

    print("=" * 60)
    print("RAG 엔진 테스트")
    print("=" * 60)

    # 코드북 + 영업일지만 로드하여 벡터 스토어 구축
    data_loader = DataLoader()
    data_loader.load_all_data()

    # RAG용 문서만 필터링
    rag_documents = [
        doc for doc in data_loader.documents
        if doc.metadata.get('dataset') in ['영업일지']
    ]

    # 코드북 문서 추가
    codebook_df = data_loader.codebook_loader.codebook_df
    for idx, row in codebook_df.iterrows():
        text_parts = []
        text_parts.append(f"파일 구분: {row.get('파일 구분', '')}")
        text_parts.append(f"번호: {row.get('번호', '')}")
        text_parts.append(f"항목: {row.get('항목', '')}")
        text_parts.append(f"항목설명: {row.get('항목설명', '')}")

        text = "\n".join(text_parts)
        metadata = {
            "dataset": "코드북",
            "row_id": int(idx),
            "source": f"코드북 (행 {idx + 1})"
        }

        from data_loader import Document
        rag_documents.append(Document(text=text, metadata=metadata))

    print(f"\n총 RAG 문서 수: {len(rag_documents)}")

    # 벡터 스토어 구축
    vector_store = VectorStore()
    vector_store.build_index(rag_documents, force_rebuild=True)

    # RAG 엔진 생성
    rag_engine = RAGEngine(vector_store)

    # 테스트 질문
    test_queries = [
        "거래처코드란 무엇인가요?",
        "영업일지에서 최근 방문 기록을 보여줘",
        "J-6 항목은 어떤 의미인가요?",
    ]

    for query in test_queries:
        print(f"\n\n질문: {query}")
        print("-" * 60)
        result = rag_engine.search_and_generate(query, top_k=3)
        print(result.answer)
        print(f"\n{rag_engine.format_sources(result.sources)}")
