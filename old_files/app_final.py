"""
최종 Streamlit UI - 데이터 기반 의사결정 지원 챗봇
모든 답변에 Gemini 분석 + 의견 포함
"""
import streamlit as st
from data_loader import DataLoader
from unified_processor import UnifiedProcessor


# 페이지 설정
st.set_page_config(
    page_title="의사결정 지원 챗봇",
    page_icon="💼",
    layout="wide"
)


@st.cache_resource
def initialize_system():
    """시스템 초기화"""
    with st.spinner("시스템 초기화 중... (데이터 로딩)"):
        data_loader = DataLoader()
        data_loader.load_all_data()
        processor = UnifiedProcessor(data_loader)
        return processor, data_loader


def main():
    """메인 앱"""
    st.title("💼 비즈니스 의사결정 지원 챗봇")
    st.markdown("""
    **데이터를 분석하고 구체적인 의견을 제시합니다**
    - 📊 거래처/매출/영업일지 데이터 자동 검색
    - 🤖 AI 분석 + 인사이트 도출
    - 💡 의사결정에 도움되는 제안 제공
    """)

    st.divider()

    # 시스템 초기화
    try:
        processor, data_loader = initialize_system()
    except Exception as e:
        st.error(f"시스템 초기화 실패: {e}")
        st.stop()

    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")

        dataset_filter = st.selectbox(
            "데이터 범위",
            ["전체", "거래처", "매출", "영업일지"],
            index=0
        )

        st.divider()

        # 시스템 정보
        st.subheader("📊 데이터 현황")

        거래처_df = data_loader.get_dataframe("거래처")
        매출_df = data_loader.get_dataframe("매출")
        영업일지_df = data_loader.get_dataframe("영업일지")

        if 거래처_df is not None:
            st.metric("거래처", f"{len(거래처_df):,}개")
        if 매출_df is not None:
            st.metric("매출 데이터", f"{len(매출_df):,}건")
        if 영업일지_df is not None:
            st.metric("영업일지", f"{len(영업일지_df):,}건")

        st.divider()

        # 예시 질문
        st.subheader("💡 예시 질문")

        example_queries = [
            "매출 상위 5개 거래처는? 전략은?",
            "한국케미칼상사 거래 현황 분석해줘",
            "최근 영업활동의 특징은?",
            "거래처별 매출 추이를 보고 조언해줘",
            "이번 달 주요 성과는?",
        ]

        for example in example_queries:
            if st.button(example, key=f"ex_{example}", use_container_width=True):
                st.session_state.query_input = example
                st.rerun()

    # 메인 영역
    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "질문을 입력하세요",
            value=st.session_state.get('query_input', ''),
            placeholder="예: 매출 상위 거래처를 분석하고 전략을 제안해주세요",
            label_visibility="collapsed",
            key="main_query_input"
        )

    with col2:
        analyze_button = st.button("🔍 분석", type="primary", use_container_width=True)

    # 질문 처리
    if analyze_button and query:
        # 입력 초기화
        if 'query_input' in st.session_state:
            del st.session_state.query_input

        with st.spinner("데이터 수집 및 분석 중..."):
            try:
                # 질의 처리
                response = processor.process(
                    query=query,
                    dataset_filter=dataset_filter
                )

                # 라우팅 정보 (작게 표시)
                st.info(f"🎯 처리 모드: **{response.mode}** | {response.routing_info}")

                # Gemini 분석 (메인)
                st.markdown("## 💡 AI 분석 및 의견")
                st.markdown(response.gemini_analysis)

                st.divider()

                # 수집된 데이터 (접을 수 있게)
                with st.expander("📋 수집된 데이터 보기", expanded=False):
                    st.code(response.data_summary)

                # 원본 계산 결과 (모드별)
                if response.mode == "CALC":
                    from calc_engine import CalcResult
                    if isinstance(response.raw_data, CalcResult):
                        calc_result = response.raw_data

                        if calc_result.result_df is not None and len(calc_result.result_df) > 0:
                            with st.expander("📊 계산 결과 테이블", expanded=True):
                                st.dataframe(
                                    calc_result.result_df.head(20),
                                    use_container_width=True
                                )

                elif response.mode == "LOOKUP":
                    from lookup_engine import LookupResult
                    if isinstance(response.raw_data, LookupResult):
                        lookup_result = response.raw_data

                        if lookup_result.found_records:
                            with st.expander(f"🔎 검색된 레코드 ({len(lookup_result.found_records)}개)", expanded=False):
                                for i, record in enumerate(lookup_result.found_records[:5], 1):
                                    st.caption(f"**레코드 {i}**")
                                    st.json(record, expanded=False)

            except Exception as e:
                st.error(f"오류 발생: {e}")
                import traceback
                st.code(traceback.format_exc())

    # 초기 화면
    elif not query:
        st.info("👆 위에 질문을 입력하고 '분석' 버튼을 클릭하세요.")

        # 시스템 설명
        st.markdown("### 🎯 이 시스템의 특징")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **📊 자동 데이터 수집**
            - 질문 분석
            - 관련 데이터 자동 검색
            - 통계 계산
            """)

        with col2:
            st.markdown("""
            **🤖 AI 분석**
            - Google Gemini 사용
            - 데이터 해석
            - 패턴 발견
            """)

        with col3:
            st.markdown("""
            **💡 의사결정 지원**
            - 구체적 인사이트
            - 전략 제안
            - 주의사항 안내
            """)

        st.divider()

        # 사용 예시
        st.markdown("### 📝 질문 예시")

        tab1, tab2, tab3 = st.tabs(["통계 분석", "거래처 분석", "영업 활동"])

        with tab1:
            st.markdown("""
            **질문**: "매출 상위 5개 거래처를 분석하고 각 거래처별 전략을 제안해주세요"

            **시스템 동작**:
            1. pandas로 매출 데이터 집계
            2. 상위 5개 거래처 추출
            3. Gemini가 분석:
               - 매출 패턴 해석
               - 각 거래처 특징 분석
               - 거래처별 맞춤 전략 제안
            """)

        with tab2:
            st.markdown("""
            **질문**: "한국케미칼상사의 최근 거래 현황을 분석하고 주의할 점을 알려주세요"

            **시스템 동작**:
            1. 거래처 정보 검색
            2. 최근 매출 데이터 수집
            3. Gemini가 분석:
               - 거래 추이 분석
               - 리스크 요인 파악
               - 관계 관리 조언
            """)

        with tab3:
            st.markdown("""
            **질문**: "최근 영업활동의 특징과 개선점을 알려주세요"

            **시스템 동작**:
            1. 영업일지 최신 데이터 검색
            2. 활동 패턴 파악
            3. Gemini가 분석:
               - 영업활동 평가
               - 효과적인 패턴 식별
               - 개선 방향 제안
            """)


if __name__ == "__main__":
    main()
