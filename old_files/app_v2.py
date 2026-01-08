"""
Streamlit UI - Router 기반 QA 챗봇
CALC/LOOKUP/RAG 모드 자동 선택
"""
import streamlit as st
import pandas as pd
from data_loader import DataLoader, Document
from vector_store import VectorStore
from query_processor_v2 import QueryProcessorV2


# 페이지 설정
st.set_page_config(
    page_title="정형데이터 QA 챗봇",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def initialize_system():
    """시스템 초기화 (캐시됨)"""
    with st.spinner("시스템 초기화 중... (최초 1회, 1-2분 소요)"):
        # 1. 데이터 로드
        data_loader = DataLoader()
        data_loader.load_all_data()

        # 2. RAG용 벡터 스토어 구축 (코드북 + 영업일지만)
        rag_documents = []

        # 영업일지
        rag_documents.extend([
            doc for doc in data_loader.documents
            if doc.metadata.get('dataset') == '영업일지'
        ])

        # 코드북
        codebook_df = data_loader.codebook_loader.codebook_df
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

        vector_store = VectorStore()
        vector_store.build_index(rag_documents)

        # 3. 통합 처리기 생성
        processor = QueryProcessorV2(data_loader, vector_store)

        return processor, data_loader, vector_store, len(rag_documents)


def main():
    """메인 앱"""
    st.title("📊 정형데이터 QA + RAG 챗봇")
    st.markdown("""
    **3가지 모드를 자동 선택하여 답변합니다:**
    - **CALC**: 집계/통계 (pandas 직접 계산)
    - **LOOKUP**: 특정 레코드 조회
    - **RAG**: 코드북/영업일지 검색 + LLM 답변
    """)

    st.divider()

    # 시스템 초기화
    try:
        processor, data_loader, vector_store, rag_doc_count = initialize_system()
    except Exception as e:
        st.error(f"시스템 초기화 실패: {e}")
        st.stop()

    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")

        # 데이터셋 필터
        dataset_filter = st.selectbox(
            "검색할 데이터셋",
            ["전체", "거래처", "매출", "영업일지"],
            index=0
        )

        # Top-K (RAG 모드용)
        top_k = st.slider(
            "RAG 검색 문서 수",
            min_value=1,
            max_value=10,
            value=5,
            help="RAG 모드에서 검색할 문서 개수"
        )

        st.divider()

        # 시스템 정보
        st.subheader("📊 시스템 정보")
        st.metric("전체 데이터", f"{len(data_loader.documents):,}개")
        st.metric("RAG 인덱스", f"{rag_doc_count:,}개")
        st.caption("RAG는 코드북 + 영업일지만 인덱싱")

        st.divider()

        # 예시 질문
        st.subheader("💡 예시 질문")

        st.caption("**CALC 모드:**")
        st.text("• 매출 상위 5개 거래처는?")
        st.text("• 거래처별 매출 합계")
        st.text("• 제품별 평균 단가")

        st.caption("**LOOKUP 모드:**")
        st.text("• 한국케미칼상사 정보")
        st.text("• 최근 영업일지 보여줘")

        st.caption("**RAG 모드:**")
        st.text("• 거래처코드란 무엇인가요?")
        st.text("• J-6 항목의 의미는?")

    # 메인 영역
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "질문을 입력하세요",
            placeholder="예: 매출 상위 5개 거래처는?",
            label_visibility="collapsed"
        )

    with col2:
        search_button = st.button("🔍 검색", type="primary", use_container_width=True)

    # 검색 실행
    if search_button and query:
        with st.spinner("처리 중..."):
            try:
                # 질의 처리
                response = processor.process_query(
                    query=query,
                    top_k=top_k,
                    dataset_filter=dataset_filter
                )

                # 라우팅 정보 표시 (상단에 작게)
                routing_info = f"""
                <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;'>
                    <small>
                    🎯 <b>선택된 모드:</b> <span style='color: #0066cc;'><b>{response.mode}</b></span>
                    | <b>신뢰도:</b> {response.routing.confidence:.0%}
                    | <b>이유:</b> {response.routing.reasoning}
                    </small>
                </div>
                """
                st.markdown(routing_info, unsafe_allow_html=True)

                # 답변 표시
                st.markdown("### 📝 답변")
                st.markdown(response.answer)

                # 모드별 추가 정보
                if response.mode == "CALC":
                    from calc_engine import CalcResult
                    if isinstance(response.details, CalcResult):
                        calc_result = response.details

                        # 샘플 행 표시
                        if calc_result.sample_rows:
                            with st.expander("🔍 계산 근거 (샘플 데이터)", expanded=False):
                                for i, row in enumerate(calc_result.sample_rows[:5], 1):
                                    st.caption(f"**[{i}]**")
                                    row_df = pd.DataFrame([row])
                                    st.dataframe(row_df, use_container_width=True)

                        # 필터 조건
                        if calc_result.filter_conditions:
                            st.info(f"적용된 조건: {', '.join(calc_result.filter_conditions)}")

                elif response.mode == "LOOKUP":
                    from lookup_engine import LookupResult
                    if isinstance(response.details, LookupResult):
                        lookup_result = response.details

                        # 검색 조건
                        if lookup_result.search_conditions:
                            st.info(f"검색 조건: {lookup_result.search_conditions}")

                elif response.mode == "RAG":
                    # RAG는 이미 출처가 답변에 포함됨
                    pass

                # 디버깅 정보
                with st.expander("🐛 디버깅 정보", expanded=False):
                    st.json(response.debug_info)

            except Exception as e:
                st.error(f"오류 발생: {e}")
                import traceback
                st.code(traceback.format_exc())

    # 사용 가이드
    elif not query:
        st.info("👆 위에 질문을 입력하고 '검색' 버튼을 클릭하세요.")

        # 모드별 설명
        st.markdown("### 📌 모드별 작동 방식")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **🧮 CALC 모드**
            - pandas로 직접 계산
            - 집계, 통계, TopN
            - 전체 데이터 기준

            *키워드: 합계, 평균, 상위, Top, 거래처별, 월별*
            """)

        with col2:
            st.markdown("""
            **🔎 LOOKUP 모드**
            - 특정 레코드 검색
            - 이름/코드 기반
            - pandas 필터링

            *키워드: 특정, 해당, 이 거래처, 최근*
            """)

        with col3:
            st.markdown("""
            **🤖 RAG 모드**
            - 벡터 검색 + LLM
            - 코드북, 영업일지
            - 정의/설명 답변

            *키워드: 무엇, 의미, 설명, 일지*
            """)

        st.divider()

        # 데이터 통계
        st.markdown("### 📊 데이터 현황")

        col1, col2, col3 = st.columns(3)

        거래처_df = data_loader.get_dataframe("거래처")
        매출_df = data_loader.get_dataframe("매출")
        영업일지_df = data_loader.get_dataframe("영업일지")

        with col1:
            if 거래처_df is not None:
                st.metric("거래처 데이터", f"{len(거래처_df):,}행")

        with col2:
            if 매출_df is not None:
                st.metric("매출 데이터", f"{len(매출_df):,}행")

        with col3:
            if 영업일지_df is not None:
                st.metric("영업일지", f"{len(영업일지_df):,}행")


if __name__ == "__main__":
    main()
