"""
NotebookLM 스타일 데이터 분석 챗봇
파일 업로드 → AI 분석
"""
import streamlit as st
import pandas as pd
from upload_handler import UploadHandler
from smart_analyst import SmartAnalyst


# 페이지 설정
st.set_page_config(
    page_title="AI 데이터 분석 노트",
    page_icon="📓",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session():
    """세션 초기화"""
    # 버전 체크 (코드 업데이트 시 세션 초기화)
    CURRENT_VERSION = "3.0"  # 대화 컨텍스트 유지 + 거래처코드 매핑 + AI 판단 강화

    if 'version' not in st.session_state or st.session_state.version != CURRENT_VERSION:
        # 버전이 다르면 모든 세션 초기화
        st.session_state.clear()
        st.session_state.version = CURRENT_VERSION
        st.info("🔄 코드가 업데이트되어 세션을 초기화했습니다. 파일을 다시 업로드해주세요.")

    if 'upload_handler' not in st.session_state:
        st.session_state.upload_handler = UploadHandler()

    if 'analyst' not in st.session_state:
        st.session_state.analyst = SmartAnalyst(st.session_state.upload_handler)

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if 'conversation_context' not in st.session_state:
        # 대화 컨텍스트: 최근 3개의 질문-답변 저장
        st.session_state.conversation_context = []


def main():
    """메인 앱"""
    initialize_session()

    # 헤더
    st.title("📓 AI 데이터 분석 노트")

    # 사이드바: 파일 관리
    with st.sidebar:
        st.header("📂 데이터 소스")

        # 파일 업로드
        uploaded_files = st.file_uploader(
            "파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'pdf'],
            accept_multiple_files=True,
            help="CSV, Excel, 이미지, PDF 지원"
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                # 이미 추가된 파일인지 확인
                existing = st.session_state.upload_handler.get_file_by_name(uploaded_file.name)

                if not existing:
                    try:
                        file_bytes = uploaded_file.read()
                        processed_file = st.session_state.upload_handler.process_upload(
                            file_bytes, uploaded_file.name
                        )
                        st.session_state.upload_handler.add_file(processed_file)
                        st.success(f"✓ {uploaded_file.name} 추가됨")
                    except Exception as e:
                        st.error(f"✗ {uploaded_file.name}: {e}")

        st.divider()

        # 업로드된 파일 목록
        st.subheader("📋 업로드된 파일")

        handler = st.session_state.upload_handler

        if len(handler.uploaded_files) == 0:
            st.info("파일을 업로드하세요")
        else:
            for i, file in enumerate(handler.uploaded_files):
                col1, col2 = st.columns([3, 1])

                with col1:
                    icon = "📊" if file.type in ['csv', 'excel'] else "🖼️"
                    st.text(f"{icon} {file.name}")
                    st.caption(f"{file.size:,} bytes")

                with col2:
                    if st.button("🗑️", key=f"del_{i}"):
                        handler.uploaded_files.remove(file)
                        st.rerun()

                # 파일 정보 expander
                with st.expander(f"📄 {file.name} 정보", expanded=False):
                    st.text(file.summary)

                    if file.type in ['csv', 'excel']:
                        st.dataframe(file.content.head(5), use_container_width=True)

                    elif file.type == 'image':
                        import base64
                        image_bytes = base64.b64decode(file.content)
                        st.image(image_bytes)

            st.divider()

            if st.button("🗑️ 모두 제거", use_container_width=True):
                handler.clear_files()
                st.session_state.chat_history = []
                st.rerun()

        st.divider()

        # 사용 가이드
        st.subheader("💡 사용 방법")
        st.markdown("""
        1. **파일 업로드**: CSV, Excel, 이미지
        2. **질문 입력**: 데이터에 대해 자유롭게 질문
        3. **AI 분석**: Gemini가 답변 + 인사이트 제공

        **예시 질문**:
        - 이 데이터의 주요 특징은?
        - 매출 상위 10개는?
        - 이 차트가 의미하는 것은?
        - 개선점을 제안해줘
        """)

    # 메인 영역
    if len(handler.uploaded_files) == 0:
        # 시작 화면
        st.markdown("### 🚀 시작하기")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            #### 1️⃣ 데이터 업로드
            - CSV/Excel 파일
            - 차트/그래프 이미지
            - PDF 문서
            """)

        with col2:
            st.markdown("""
            #### 2️⃣ 자유롭게 질문
            - "주요 트렌드는?"
            - "문제점은?"
            - "전략 제안해줘"
            """)

        with col3:
            st.markdown("""
            #### 3️⃣ AI 분석
            - 데이터 자동 분석
            - 인사이트 도출
            - 구체적 조언 제공
            """)

        st.divider()

        st.info("👈 왼쪽 사이드바에서 파일을 업로드하세요")

        # 샘플 데이터 버튼
        st.markdown("### 📊 샘플 데이터로 테스트")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📂 거래처 데이터 로드", use_container_width=True):
                try:
                    with open("/Users/inseoplee/Desktop/rag_Test/거래처 데이터.csv", 'rb') as f:
                        file_bytes = f.read()
                        processed = handler.process_upload(file_bytes, "거래처 데이터.csv")
                        handler.add_file(processed)
                        st.rerun()
                except:
                    st.error("샘플 파일을 찾을 수 없습니다")

        with col2:
            if st.button("📊 매출 데이터 로드", use_container_width=True):
                try:
                    with open("/Users/inseoplee/Desktop/rag_Test/sales data.csv", 'rb') as f:
                        file_bytes = f.read()
                        processed = handler.process_upload(file_bytes, "sales data.csv")
                        handler.add_file(processed)
                        st.rerun()
                except:
                    st.error("샘플 파일을 찾을 수 없습니다")

    else:
        # 채팅 인터페이스
        st.markdown("### 💬 데이터에 대해 질문하세요")

        # 채팅 히스토리 표시
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # 테이블이 있으면 표시
                if "tables" in message and message["tables"]:
                    for table in message["tables"]:
                        st.dataframe(table, use_container_width=True)

        # 입력창
        user_query = st.chat_input("질문을 입력하세요...")

        if user_query:
            # 사용자 메시지 추가
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_query
            })

            with st.chat_message("user"):
                st.markdown(user_query)

            # AI 분석
            with st.chat_message("assistant"):
                with st.spinner("분석 중..."):
                    try:
                        analyst = st.session_state.analyst

                        # 대화 컨텍스트 전달
                        result = analyst.analyze(
                            user_query,
                            include_images=True,
                            conversation_context=st.session_state.conversation_context
                        )

                        # 응답 표시
                        st.markdown(result.gemini_response)

                        # 테이블 표시
                        tables_to_save = []
                        if result.tables:
                            st.markdown("---")
                            st.markdown("#### 📊 계산 결과")
                            for table in result.tables:
                                st.dataframe(table, use_container_width=True)
                                tables_to_save.append(table)

                        # 히스토리에 추가
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": result.gemini_response,
                            "tables": tables_to_save
                        })

                        # 대화 컨텍스트 업데이트 (최근 3개만 유지)
                        st.session_state.conversation_context.append({
                            "query": user_query,
                            "response": result.gemini_response
                        })
                        if len(st.session_state.conversation_context) > 3:
                            st.session_state.conversation_context.pop(0)

                    except Exception as e:
                        error_msg = f"분석 중 오류 발생: {e}"
                        st.error(error_msg)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg
                        })

        # 빠른 질문 버튼
        st.markdown("#### 💡 빠른 질문")

        quick_questions = [
            "이 데이터의 주요 특징을 알려줘",
            "가장 중요한 인사이트 3가지는?",
            "문제점이나 개선점을 찾아줘",
        ]

        cols = st.columns(len(quick_questions))

        for i, question in enumerate(quick_questions):
            with cols[i]:
                if st.button(question, key=f"quick_{i}", use_container_width=True):
                    # 질문을 채팅창에 자동 입력
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": question
                    })

                    with st.spinner("분석 중..."):
                        try:
                            analyst = st.session_state.analyst
                            result = analyst.analyze(
                                question,
                                include_images=True,
                                conversation_context=st.session_state.conversation_context
                            )

                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": result.gemini_response,
                                "tables": result.tables or []
                            })

                            # 대화 컨텍스트 업데이트
                            st.session_state.conversation_context.append({
                                "query": question,
                                "response": result.gemini_response
                            })
                            if len(st.session_state.conversation_context) > 3:
                                st.session_state.conversation_context.pop(0)

                            st.rerun()

                        except Exception as e:
                            st.error(f"분석 중 오류: {e}")


if __name__ == "__main__":
    main()
