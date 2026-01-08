# 🚀 빠른 시작 가이드

## 1단계: 의존성 설치

터미널에서 다음 명령어를 실행하세요:

```bash
pip install -r requirements.txt
```

설치되는 패키지:
- pandas, numpy (데이터 처리)
- sentence-transformers (임베딩)
- faiss-cpu (벡터 검색)
- chromadb (대안 벡터DB)
- streamlit (웹 UI)
- google-generativeai (LLM)

## 2단계: 애플리케이션 실행

```bash
streamlit run app.py
```

## 3단계: 브라우저에서 확인

- 자동으로 브라우저가 열립니다 (`http://localhost:8501`)
- 처음 실행 시 벡터 인덱스를 생성하므로 1-2분 소요됩니다
- 이후 실행은 캐시를 사용하여 빠릅니다

## 4단계: 질문하기

예시 질문을 입력해보세요:

```
한국케미칼상사에 대해 알려주세요
```

```
매출 상위 거래처는?
```

```
최근 영업일지를 보여주세요
```

## 📁 프로젝트 파일 구조

```
rag_Test/
├── 📄 Python 파일들
│   ├── app.py                  # 웹 UI 메인 (실행 파일)
│   ├── config.py               # 설정 (API 키 포함)
│   ├── utils.py                # 유틸리티 함수
│   ├── codebook_loader.py      # 코드북 로더
│   ├── data_loader.py          # 데이터 로더
│   ├── vector_store.py         # 벡터 스토어
│   └── query_processor.py      # 질의 처리
│
├── 📊 데이터 파일들
│   ├── 데이터 db.csv           # 코드북 (필수!)
│   ├── 거래처 데이터.csv        # 거래처 정보
│   ├── sales data.csv          # 매출 데이터
│   └── 영업일지2.csv            # 영업일지
│
├── 📚 문서
│   ├── README.md               # 상세 문서
│   ├── QUICK_START.md          # 이 파일
│   └── requirements.txt        # 의존성 목록
│
└── 💾 캐시 디렉토리
    ├── .cache/                 # 모델 캐시
    └── vector_store/           # 벡터 인덱스 캐시
```

## ⚙️ 설정 변경

`config.py` 파일에서 다음 항목을 수정할 수 있습니다:

### API 키 변경
```python
GOOGLE_API_KEY = "your-api-key-here"
```

### 검색 문서 수 조정
```python
DEFAULT_TOP_K = 5  # 기본값 5개
MAX_TOP_K = 20     # 최대 20개
```

### 임베딩 모델 변경
```python
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

## 🔧 문제 해결

### 문제 1: 모듈 import 오류
```bash
# 해결: 의존성 재설치
pip install -r requirements.txt --upgrade
```

### 문제 2: 인코딩 오류
```python
# config.py에 인코딩 추가
ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"]
```

### 문제 3: API 키 오류
- Google AI Studio (https://aistudio.google.com/) 에서 API 키 발급
- `config.py`의 `GOOGLE_API_KEY` 업데이트

### 문제 4: 메모리 부족
```python
# config.py에서 검색 수 줄이기
DEFAULT_TOP_K = 3
```

### 문제 5: 캐시 문제
```bash
# 캐시 삭제 후 재실행
rm -rf vector_store/ .cache/
streamlit run app.py
```

## 🎯 사용 팁

### 1. 효과적인 질문 작성
- ✅ 구체적: "한국케미칼상사의 최근 거래 내역은?"
- ❌ 모호함: "거래처 알려줘"

### 2. 데이터셋 필터 활용
- 특정 데이터만 검색하려면 좌측 사이드바에서 선택
- 예: 거래처 정보만 필요하면 "거래처" 선택

### 3. Top-K 조정
- 일반 질문: 5개 (기본값)
- 통계 질문: 10-15개 (더 많은 데이터 필요)
- 빠른 검색: 3개

### 4. 통계 질의 키워드
다음 키워드를 포함하면 자동으로 집계 수행:
- "합계", "총", "평균"
- "Top", "상위", "순위"
- "월별", "기간별"
- "최대", "최소", "개수"

## 📊 예시 질문 시나리오

### 시나리오 1: 거래처 조회
```
Q: 한국케미칼상사의 정보를 알려주세요

A: 거래처코드, 담당자, 사업자등록번호(마스킹), 거래 유형 등 제공
   + 근거: 거래처 데이터 (행 1)
```

### 시나리오 2: 매출 분석
```
Q: 매출 상위 5개 거래처는?

A: 통계 계산 수행
   → 거래처별 매출 집계
   → Top 5 표로 제시
   + 근거: 매출 데이터 (여러 행)
```

### 시나리오 3: 영업 활동
```
Q: 최근 방문한 거래처는?

A: 영업일지에서 최근 날짜 기준으로 검색
   → 방문 일자, 거래처명, 활동 내용 제공
   + 근거: 영업일지 (최근 행들)
```

## 🔄 개발 모드

### 코드 수정 후 재실행
```bash
# Streamlit은 파일 변경을 자동 감지
# 브라우저에서 "Rerun" 버튼 클릭
```

### 벡터 인덱스 강제 재생성
```python
# vector_store.py 수정
vector_store.build_index(documents, force_rebuild=True)
```

### 개별 모듈 테스트
```bash
# 코드북 로더 테스트
python codebook_loader.py

# 데이터 로더 테스트
python data_loader.py

# 벡터 스토어 테스트
python vector_store.py

# 질의 처리기 테스트
python query_processor.py
```

## 📞 지원

문제가 계속되면 다음을 확인하세요:

1. Python 버전: 3.8 이상
2. 데이터 파일: 모든 CSV가 같은 디렉토리에 있는지
3. API 키: 유효한 Google Gemini API 키인지
4. 디스크 공간: 벡터 인덱스 저장 공간 확보

---

**즐거운 데이터 탐색 되세요! 🎉**
