"""
설정 파일
"""
import os
from pathlib import Path

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).parent

# 데이터 파일 경로 (로컬 경로로 수정)
DATA_DIR = BASE_DIR
CODEBOOK_PATH = DATA_DIR / "데이터 db.csv"
SALES_JOURNAL_PATH = DATA_DIR / "영업일지2.csv"
SALES_DATA_PATH = DATA_DIR / "sales data.csv"
CLIENT_DATA_PATH = DATA_DIR / "거래처 데이터.csv"

# 벡터 스토어 설정
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
CACHE_DIR = BASE_DIR / ".cache"

# Google Gemini API 설정
# 환경 변수에서 로드 (보안)
GOOGLE_API_KEY = None

# Streamlit Cloud에서 실행 중인지 확인
try:
    import streamlit as st
    # Streamlit Cloud의 secrets 사용
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
except:
    pass

# Streamlit secrets에 없으면 .env 파일에서 로드
if not GOOGLE_API_KEY:
    from dotenv import load_dotenv
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# API 키 확인
if not GOOGLE_API_KEY:
    raise ValueError(
        "⚠️ GOOGLE_API_KEY가 설정되지 않았습니다!\n\n"
        "로컬 개발:\n"
        "  1. .env 파일을 생성하세요 (.env.example 참고)\n"
        "  2. GOOGLE_API_KEY=your-api-key-here 추가\n\n"
        "Streamlit Cloud 배포:\n"
        "  1. Settings > Secrets 메뉴에서\n"
        "  2. GOOGLE_API_KEY = \"your-api-key-here\" 추가"
    )

# 임베딩 모델 설정
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# RAG 설정
DEFAULT_TOP_K = 5
MAX_TOP_K = 20

# 통계성 질의 키워드
STAT_KEYWORDS = [
    "합계", "총", "Top", "top", "상위", "추이", "월별", "분기별",
    "최근", "기간", "평균", "평균값", "최대", "최소", "개수", "건수",
    "순위", "랭킹", "통계", "집계", "분석", "비교", "증가", "감소",
    "많은", "적은", "높은", "낮은"
]

# 민감정보 마스킹 패턴
SENSITIVE_PATTERNS = {
    "사업자등록번호": r"\d{3}-\d{2}-\d{5}",
    "주민등록번호": r"\d{6}-\d{7}",
    "전화번호": r"\d{2,3}-\d{3,4}-\d{4}",
}

# 데이터셋 정의
DATASETS = {
    "거래처": "거래처 데이터",
    "매출": "매출 데이터",
    "영업일지": "영업일지"
}

# 인코딩 fallback 순서
ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
