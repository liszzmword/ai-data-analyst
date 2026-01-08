"""
통합 질의 처리기 (Router 기반)
CALC / LOOKUP / RAG 모드를 자동 선택하여 처리
"""
from typing import Dict, Any
from dataclasses import dataclass

from router import QueryRouter, RoutingResult
from calc_engine import CalcEngine, CalcResult
from lookup_engine import LookupEngine, LookupResult
from rag_engine import RAGEngine, RAGResult
from data_loader import DataLoader
from vector_store import VectorStore


@dataclass
class QueryResponse:
    """통합 응답 결과"""
    mode: str  # CALC, LOOKUP, RAG
    routing: RoutingResult
    answer: str
    details: Any  # CalcResult | LookupResult | RAGResult
    debug_info: Dict


class QueryProcessorV2:
    """라우터 기반 통합 질의 처리기"""

    def __init__(
        self,
        data_loader: DataLoader,
        vector_store: VectorStore
    ):
        """
        Args:
            data_loader: DataLoader 인스턴스
            vector_store: VectorStore 인스턴스 (RAG용)
        """
        self.data_loader = data_loader
        self.vector_store = vector_store

        # 라우터 초기화
        self.router = QueryRouter()

        # 각 엔진 초기화
        self.calc_engine = CalcEngine(data_loader)
        self.lookup_engine = LookupEngine(data_loader)
        self.rag_engine = RAGEngine(vector_store)

        print("✓ 통합 질의 처리기 초기화 완료 (Router 기반)")

    def process_query(
        self,
        query: str,
        top_k: int = 5,
        dataset_filter: str = "전체"
    ) -> QueryResponse:
        """
        질문을 라우팅하여 적절한 엔진으로 처리합니다.

        Args:
            query: 사용자 질문
            top_k: RAG 검색 시 문서 수
            dataset_filter: 데이터셋 필터

        Returns:
            QueryResponse
        """
        print("\n" + "=" * 60)
        print(f"🔍 질의 처리: {query}")
        print("=" * 60)

        # 1. 라우팅
        routing = self.router.route(query)
        print(f"\n📍 라우팅 결과:")
        print(f"  → 모드: {routing.mode} (신뢰도: {routing.confidence:.2f})")
        print(f"  → 이유: {routing.reasoning}")

        debug_info = {
            "query": query,
            "mode": routing.mode,
            "confidence": routing.confidence,
            "reasoning": routing.reasoning,
            "dataset_filter": dataset_filter,
            "top_k": top_k
        }

        # 2. 모드별 처리
        if routing.mode == "CALC":
            result = self.calc_engine.calculate(query, dataset_filter)
            answer = result.answer

            # 결과 테이블 추가
            if result.result_df is not None and len(result.result_df) > 0:
                answer += "\n\n---\n\n"
                answer += "### 📊 계산 결과 상세\n\n"
                answer += result.result_df.head(10).to_markdown(index=False)

            details = result

        elif routing.mode == "LOOKUP":
            result = self.lookup_engine.lookup(query, dataset_filter)
            answer = result.answer
            details = result

        elif routing.mode == "RAG":
            result = self.rag_engine.search_and_generate(query, top_k)
            answer = result.answer

            # 출처 추가
            answer += "\n\n---\n\n"
            answer += self.rag_engine.format_sources(result.sources)

            details = result

        else:
            answer = f"알 수 없는 모드: {routing.mode}"
            details = None

        return QueryResponse(
            mode=routing.mode,
            routing=routing,
            answer=answer,
            details=details,
            debug_info=debug_info
        )

    def format_response(self, response: QueryResponse) -> str:
        """응답을 사용자 친화적 형식으로 포맷팅"""
        parts = []

        # 디버깅 정보 (작게 표시)
        parts.append(f"<small>🎯 모드: **{response.mode}** | 신뢰도: {response.routing.confidence:.0%} | {response.routing.reasoning}</small>\n")
        parts.append("---\n")

        # 답변
        parts.append(response.answer)

        # CALC 모드 추가 정보
        if response.mode == "CALC" and isinstance(response.details, CalcResult):
            calc_result = response.details
            if calc_result.sample_rows:
                parts.append("\n\n### 🔍 샘플 데이터 (계산 근거)")
                for i, row in enumerate(calc_result.sample_rows[:5], 1):
                    parts.append(f"\n**[{i}]**")
                    for key, value in list(row.items())[:5]:  # 최대 5개 필드
                        parts.append(f"- {key}: {value}")

        # LOOKUP 모드 추가 정보
        elif response.mode == "LOOKUP" and isinstance(response.details, LookupResult):
            # 이미 answer에 포함됨
            pass

        # RAG 모드는 이미 출처 포함됨

        return "\n".join(parts)


if __name__ == "__main__":
    # 테스트
    print("=" * 60)
    print("통합 질의 처리기 테스트 (Router 기반)")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n[1/3] 데이터 로딩...")
    data_loader = DataLoader()
    data_loader.load_all_data()

    # 2. RAG용 벡터 스토어 구축 (코드북 + 영업일지만)
    print("\n[2/3] RAG 벡터 스토어 구축...")
    rag_documents = []

    # 영업일지
    rag_documents.extend([
        doc for doc in data_loader.documents
        if doc.metadata.get('dataset') == '영업일지'
    ])

    # 코드북
    codebook_df = data_loader.codebook_loader.codebook_df
    from data_loader import Document
    import pandas as pd

    for idx, row in codebook_df.iterrows():
        text_parts = [
            f"파일 구분: {row.get('파일 구분', '')}",
            f"번호: {row.get('번호', '')}",
            f"항목: {row.get('항목', '')}",
            f"항목설명: {row.get('항목설명', '')}"
        ]
        if pd.notna(row.get('예시 및 선택지')):
            text_parts.append(f"예시: {row['예시 및 선택지']}")

        rag_documents.append(Document(
            text="\n".join(text_parts),
            metadata={
                "dataset": "코드북",
                "row_id": int(idx),
                "source": f"코드북 (행 {idx + 1})"
            }
        ))

    print(f"  RAG 문서 수: {len(rag_documents)}")

    vector_store = VectorStore()
    vector_store.build_index(rag_documents)

    # 3. 통합 처리기 생성
    print("\n[3/3] 통합 질의 처리기 초기화...")
    processor = QueryProcessorV2(data_loader, vector_store)

    # 테스트 질문들
    test_queries = [
        "매출 상위 5개 거래처는?",  # CALC
        "거래처별 매출 합계를 알려주세요",  # CALC
        "한국케미칼상사의 정보를 알려주세요",  # LOOKUP
        "최근 영업일지를 보여주세요",  # LOOKUP or RAG
        "거래처코드란 무엇인가요?",  # RAG
        "J-6 항목은 어떤 의미인가요?",  # RAG
    ]

    print("\n" + "=" * 60)
    print("테스트 질문 실행")
    print("=" * 60)

    for query in test_queries:
        try:
            response = processor.process_query(query, top_k=3)
            formatted = processor.format_response(response)

            print(f"\n\n질문: {query}")
            print("-" * 60)
            print(formatted)

        except Exception as e:
            print(f"\n✗ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("✓ 모든 테스트 완료!")
    print("=" * 60)
