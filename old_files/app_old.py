"""
Streamlit 기반 RAG 챗봇 UI
"""
import streamlit as st
from pathlib import Path

from config import DEFAULT_TOP_K, MAX_TOP_K, DATASETS
from data_loader import DataLoader
from vector_store import VectorStore
from query_processor import QueryProcessor


# 페이지 설정
st.set_page_config(
    page_title="📊 데이터 기반 RAG 챗봇",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def initialize_system():
    """시스템을 초기화합니다 (캐싱)."""
    with st.spinner("🔄 시스템 초기화 중..."):
        # 데이터 로드
        data_loader = DataLoader()
        documents = data_loader.load_all_data()

        # 벡터 스토어 구축
        vector_store = VectorStore()
        vector_store.build_index(documents)

        # 질의 처리기 생성
        query_processor = QueryProcessor(vector_store, data_loader)

    return query_processor, data_loader, vector_store


def main():
    # 제목
    st.title("📊 데이터 기반 RAG 챗봇")
    st.markdown("거래처, 매출, 영업일지 데이터를 자연어로 질문하세요!")

    # 시스템 초기화
    try:
        query_processor, data_loader, vector_store = initialize_system()
    except Exception as e:
        st.error(f"❌ 시스템 초기화 실패: {e}")
        st.stop()

    # 사이드바 - 필터 및 설정
    with st.sidebar:
        st.header("⚙️ 설정")

        # 데이터셋 필터
        st.subheader("📁 데이터셋 선택")
        dataset_options = ["전체"] + list(DATASETS.keys())
        dataset_filter = st.selectbox(
            "검색할 데이터셋",
            options=dataset_options,
            index=0
        )

        # Top-K 설정
        st.subheader("🔍 검색 설정")
        top_k = st.slider(
            "검색할 문서 수 (Top-K)",
            min_value=1,
            max_value=MAX_TOP_K,
            value=DEFAULT_TOP_K,
            step=1
        )

        # 통계
        st.subheader("📈 데이터 통계")
        total_docs = len(vector_store.documents)
        st.metric("총 문서 수", f"{total_docs:,}")

        dataset_counts = {}
        for doc in vector_store.documents:
            dataset = doc.metadata.get('dataset', 'Unknown')
            dataset_counts[dataset] = dataset_counts.get(dataset, 0) + 1

        for dataset, count in dataset_counts.items():
            st.metric(f"{dataset}", f"{count:,}")

        # 캐시 재생성 버튼
        st.subheader("🔧 관리")
        if st.button("🔄 벡터 인덱스 재생성"):
            with st.spinner("재생성 중..."):
                vector_store.clear_cache()
                st.cache_resource.clear()
                st.success("✅ 완료! 페이지를 새로고침하세요.")
                st.rerun()

    # 메인 영역
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 질문하기")

        # 예시 질문
        with st.expander("💡 예시 질문 보기"):
            example_questions = [
                "한국케미칼상사에 대해 알려주세요",
                "이놀의 거래처 정보를 알려주세요",
                "최근 영업일지를 보여주세요",
                "매출 상위 거래처는?",
                "거래처별 매출 합계를 알려주세요",
                "PS양면 제품을 구매한 거래처는?",
                "거래처 중 냉장고 관련 거래처는?",
                "최근 방문한 거래처는?",
                "주요 거래처 목록을 보여주세요",
                "매출액이 높은 제품은?"
            ]
            for i, q in enumerate(example_questions, 1):
                st.markdown(f"{i}. {q}")

        # 질문 입력
        query = st.text_input(
            "질문을 입력하세요",
            placeholder="예: 한국케미칼상사에 대해 알려주세요",
            key="query_input"
        )

        # 검색 버튼
        if st.button("🔍 검색", type="primary") or query:
            if query.strip():
                with st.spinner("🤔 답변 생성 중..."):
                    # 질의 처리
                    result = query_processor.process_query(
                        query=query,
                        top_k=top_k,
                        dataset_filter=dataset_filter
                    )

                    # 답변 표시
                    st.markdown("### 📝 답변")
                    st.markdown(result['answer'])

                    # 통계 표시 (있을 경우)
                    if result['statistics'] is not None:
                        st.markdown("### 📊 통계")
                        st.dataframe(result['statistics'])

                    # 출처 표시
                    st.markdown("---")
                    sources_text = query_processor.format_sources(result['sources'])
                    st.markdown(sources_text)

            else:
                st.warning("⚠️ 질문을 입력해주세요.")

    with col2:
        st.subheader("📚 근거 문서")

        # 세션 상태에 근거 문서 저장
        if 'sources' not in st.session_state:
            st.session_state.sources = []

        # 검색 결과가 있으면 업데이트
        if query and query.strip():
            try:
                result = query_processor.process_query(
                    query=query,
                    top_k=top_k,
                    dataset_filter=dataset_filter
                )
                st.session_state.sources = result['sources']
            except:
                pass

        # 근거 문서 카드 표시
        if st.session_state.sources:
            for i, (doc, score) in enumerate(st.session_state.sources, 1):
                with st.expander(f"📄 문서 {i} - {doc.metadata['source']} (유사도: {score:.4f})"):
                    # 메타데이터
                    st.markdown("**메타데이터:**")
                    metadata = doc.metadata
                    if '거래처명' in metadata:
                        st.write(f"- 거래처: {metadata['거래처명']}")
                    if '거래처코드' in metadata:
                        st.write(f"- 거래처코드: {metadata['거래처코드']}")
                    if '날짜' in metadata:
                        dates = metadata['날짜']
                        if isinstance(dates, list) and dates:
                            st.write(f"- 날짜: {dates[0]}")

                    # 문서 텍스트
                    st.markdown("**내용:**")
                    st.text_area(
                        "문서 내용",
                        value=doc.text,
                        height=200,
                        key=f"doc_text_{i}",
                        label_visibility="collapsed"
                    )
        else:
            st.info("검색 결과가 여기에 표시됩니다.")

    # 푸터
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 12px;'>
        📊 데이터 기반 RAG 챗봇 | Powered by Sentence Transformers + FAISS + Google Gemini
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
