"""
질의 처리 및 답변 생성
"""
import re
import pandas as pd
from typing import List, Tuple, Dict
import google.generativeai as genai

from config import GOOGLE_API_KEY, STAT_KEYWORDS
from data_loader import Document, DataLoader
from vector_store import VectorStore


# Google Gemini API 설정
genai.configure(api_key=GOOGLE_API_KEY)


class QueryProcessor:
    """질의를 처리하고 답변을 생성하는 클래스"""

    def __init__(self, vector_store: VectorStore, data_loader: DataLoader):
        self.vector_store = vector_store
        self.data_loader = data_loader
        self.llm = genai.GenerativeModel('gemini-2.5-flash')

    def process_query(
            self,
            query: str,
            top_k: int = 5,
            dataset_filter: str = "전체"
    ) -> Dict:
        """
        질의를 처리하고 답변을 생성합니다.

        Args:
            query: 사용자 질의
            top_k: 검색할 문서 수
            dataset_filter: 데이터셋 필터

        Returns:
            {
                'answer': 답변 텍스트,
                'sources': [(doc, score), ...],
                'statistics': DataFrame or None,
                'is_statistical': bool
            }
        """
        print(f"\n🔍 질의 처리 중: {query}")

        # 1. 통계성 질의 여부 확인
        is_statistical = self._is_statistical_query(query)
        print(f"  통계성 질의: {is_statistical}")

        # 2. RAG 검색
        sources = self.vector_store.search(query, top_k=top_k, dataset_filter=dataset_filter)
        print(f"  검색 결과: {len(sources)} 개 문서")

        # 3. 통계 계산 (필요시)
        statistics_df = None
        statistics_text = ""

        if is_statistical:
            statistics_df, statistics_text = self._calculate_statistics(query, sources, dataset_filter)

        # 4. 답변 생성
        answer = self._generate_answer(query, sources, statistics_text)

        return {
            'answer': answer,
            'sources': sources,
            'statistics': statistics_df,
            'is_statistical': is_statistical
        }

    def _is_statistical_query(self, query: str) -> bool:
        """
        통계성 질의인지 확인합니다.

        Args:
            query: 질의 텍스트

        Returns:
            통계성 질의 여부
        """
        return any(keyword in query for keyword in STAT_KEYWORDS)

    def _calculate_statistics(
            self,
            query: str,
            sources: List[Tuple[Document, float]],
            dataset_filter: str
    ) -> Tuple[pd.DataFrame, str]:
        """
        통계를 계산합니다.

        Args:
            query: 질의 텍스트
            sources: 검색 결과
            dataset_filter: 데이터셋 필터

        Returns:
            (DataFrame, 통계 설명 텍스트)
        """
        print("  📊 통계 계산 중...")

        # 관련 데이터셋 결정
        if dataset_filter != "전체":
            datasets = [dataset_filter]
        else:
            # sources에서 언급된 데이터셋 추출
            datasets = list(set(doc.metadata.get('dataset') for doc, _ in sources))

        statistics_parts = []

        for dataset_name in datasets:
            df = self.data_loader.get_dataframe(dataset_name)
            if df is None:
                continue

            # 간단한 통계 계산
            stats_text = self._compute_simple_stats(query, df, dataset_name)
            if stats_text:
                statistics_parts.append(stats_text)

        statistics_text = "\n\n".join(statistics_parts) if statistics_parts else ""

        return None, statistics_text

    def _compute_simple_stats(self, query: str, df: pd.DataFrame, dataset_name: str) -> str:
        """
        간단한 통계를 계산합니다.

        Args:
            query: 질의
            df: DataFrame
            dataset_name: 데이터셋 이름

        Returns:
            통계 텍스트
        """
        stats_lines = []
        stats_lines.append(f"### {dataset_name} 통계")

        # 기본 통계
        stats_lines.append(f"- 총 행 수: {len(df):,}")

        # 거래처코드(B-2) 기준 통계
        if 'B-2' in df.columns:
            unique_clients = df['B-2'].nunique()
            stats_lines.append(f"- 고유 거래처 수: {unique_clients:,}")

        # 거래처명(B-1) 기준 Top 5
        if 'B-1' in df.columns and '합계' in query or 'Top' in query or '상위' in query:
            top_clients = df['B-1'].value_counts().head(5)
            stats_lines.append(f"\n거래처별 건수 Top 5:")
            for i, (client, count) in enumerate(top_clients.items(), 1):
                stats_lines.append(f"  {i}. {client}: {count:,}건")

        # 숫자 컬럼에 대한 집계
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            # J-6, J-7, J-8 같은 매출 관련 컬럼 찾기
            revenue_cols = [col for col in numeric_cols if col in ['J-6', 'J-7', 'J-8']]

            if revenue_cols and ('매출' in query or '합계' in query or '총' in query):
                stats_lines.append(f"\n주요 숫자 컬럼 합계:")
                for col in revenue_cols[:3]:  # 최대 3개만
                    total = df[col].sum()
                    if not pd.isna(total) and total > 0:
                        stats_lines.append(f"  - {col}: {total:,.0f}")

        return "\n".join(stats_lines)

    def _generate_answer(
            self,
            query: str,
            sources: List[Tuple[Document, float]],
            statistics_text: str
    ) -> str:
        """
        LLM을 사용하여 답변을 생성합니다.

        Args:
            query: 사용자 질의
            sources: 검색 결과
            statistics_text: 통계 텍스트

        Returns:
            답변 텍스트
        """
        print("  🤖 답변 생성 중...")

        # 컨텍스트 구성
        context_parts = []

        if statistics_text:
            context_parts.append("=== 통계 정보 ===")
            context_parts.append(statistics_text)
            context_parts.append("")

        context_parts.append("=== 검색된 관련 문서 ===")
        for i, (doc, score) in enumerate(sources, 1):
            context_parts.append(f"\n[문서 {i}] (유사도: {score:.4f})")
            context_parts.append(f"출처: {doc.metadata['source']}")
            # 텍스트의 처음 500자만 사용
            text_preview = doc.text[:500]
            context_parts.append(text_preview)

        context = "\n".join(context_parts)

        # 프롬프트 구성
        prompt = f"""당신은 한국어 비즈니스 데이터 분석 전문가입니다.

아래 문서들을 바탕으로 사용자의 질문에 답변해주세요.

사용자 질문: {query}

관련 문서 및 통계:
{context}

답변 작성 지침:
1. 제공된 문서의 정보만을 기반으로 답변하세요.
2. 한국어로 답변하세요.
3. 구체적인 수치나 사실을 언급할 때는 출처(문서 번호)를 표시하세요.
4. 통계 정보가 있다면 표 형태로 정리하여 제시하세요.
5. 정보가 부족하여 답변할 수 없다면 솔직히 말씀해주세요.
6. 근거가 명확하지 않은 추측은 하지 마세요.

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
        """
        출처를 포맷팅합니다.

        Args:
            sources: 검색 결과

        Returns:
            포맷팅된 출처 텍스트
        """
        if not sources:
            return "출처 정보가 없습니다."

        source_parts = []
        source_parts.append("## 📚 근거 및 출처")
        source_parts.append("")

        for i, (doc, score) in enumerate(sources, 1):
            source_parts.append(f"### [{i}] {doc.metadata['source']} (유사도: {score:.4f})")

            # 핵심 메타데이터 표시
            metadata = doc.metadata
            if '거래처명' in metadata:
                source_parts.append(f"- 거래처: {metadata['거래처명']}")
            if '거래처코드' in metadata:
                source_parts.append(f"- 거래처코드: {metadata['거래처코드']}")
            if '날짜' in metadata:
                dates = metadata['날짜']
                if isinstance(dates, list) and dates:
                    source_parts.append(f"- 날짜: {dates[0]}")

            # 문서 텍스트 미리보기
            preview = doc.text[:300].replace('\n', ' ')
            source_parts.append(f"\n```\n{preview}...\n```\n")

        return "\n".join(source_parts)


if __name__ == "__main__":
    # 테스트
    from data_loader import DataLoader
    from vector_store import VectorStore

    print("=== 질의 처리기 테스트 ===")

    # 데이터 및 벡터 스토어 로드
    data_loader = DataLoader()
    documents = data_loader.load_all_data()

    vector_store = VectorStore()
    vector_store.build_index(documents)

    # 질의 처리기 생성
    processor = QueryProcessor(vector_store, data_loader)

    # 테스트 질의
    test_query = "한국케미칼상사에 대해 알려주세요"

    result = processor.process_query(test_query, top_k=3)

    print(f"\n질문: {test_query}")
    print(f"\n답변:\n{result['answer']}")
    print(f"\n{processor.format_sources(result['sources'])}")
