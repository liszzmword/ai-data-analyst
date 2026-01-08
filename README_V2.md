# 📊 정형데이터 QA + RAG 챗봇 V2

Router 기반 3-모드 자동 선택 시스템

## ✨ 주요 특징

### 🎯 3가지 모드 자동 선택
질문을 분석하여 최적의 처리 방식을 자동으로 선택합니다:

1. **CALC 모드** 🧮
   - **언제**: 합계, 평균, Top N, 거래처별 집계 등
   - **방식**: pandas로 **전체 데이터** 직접 계산
   - **장점**: 정확한 통계, 빠른 속도
   - **예시**: "매출 상위 5개 거래처는?", "거래처별 매출 합계"

2. **LOOKUP 모드** 🔎
   - **언제**: 특정 거래처/레코드 조회
   - **방식**: pandas 필터링으로 검색
   - **장점**: 정확한 레코드 매칭
   - **예시**: "한국케미칼상사 정보", "최근 영업일지"

3. **RAG 모드** 🤖
   - **언제**: 코드북 정의, 영업일지 메모 검색
   - **방식**: 벡터 검색 + LLM 생성
   - **장점**: 자연어 답변, 컨텍스트 이해
   - **예시**: "거래처코드란?", "J-6 항목 설명"

## 🏗️ 아키텍처

```
사용자 질문
    ↓
┌─────────────┐
│   ROUTER    │ ← 키워드/패턴 분석
└─────────────┘
    ↓ (모드 선택)
    ├─→ CALC    → pandas 집계/통계 → 표 + 샘플 행
    ├─→ LOOKUP  → pandas 필터링   → 레코드 상세
    └─→ RAG     → 벡터 검색 + LLM → 자연어 답변 + 출처
```

## 📁 파일 구조

```
rag_Test/
├── 🆕 router.py              # 질문 분류 라우터
├── 🆕 calc_engine.py         # pandas 계산 엔진
├── 🆕 lookup_engine.py       # 레코드 검색 엔진
├── 🆕 rag_engine.py          # RAG 엔진 (코드북+영업일지)
├── 🆕 query_processor_v2.py  # 통합 처리기
├── 🆕 app_v2.py              # Streamlit UI V2
│
├── data_loader.py            # 데이터 로더
├── vector_store.py           # 벡터 스토어
├── codebook_loader.py        # 코드북 로더
├── config.py                 # 설정
├── utils.py                  # 유틸리티
│
├── requirements.txt          # 의존성 (tabulate 추가)
└── README_V2.md             # 이 파일
```

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

**새로 추가된 패키지**: `tabulate` (마크다운 테이블 생성용)

### 2. 애플리케이션 실행
```bash
streamlit run app_v2.py
```

### 3. 브라우저 접속
- Local: http://localhost:8501
- Network: http://192.168.45.26:8501

## 📖 사용 방법

### 예시 질문 (모드별)

#### 🧮 CALC 모드 질문
```
매출 상위 5개 거래처는?
거래처별 매출 합계를 알려주세요
제품별 평균 단가는?
2024년 1월 매출 추이
월별 거래 건수
```

**CALC 모드 키워드**:
- 집계: 합계, 총, 평균, 최대, 최소
- 순위: 상위, 하위, Top N, 랭킹
- 그룹: 거래처별, 제품별, 월별, 분기별
- 추이: 증감, 추이, 변화, 전월대비

#### 🔎 LOOKUP 모드 질문
```
한국케미칼상사의 정보를 알려주세요
이놀의 거래처 정보
최근 영업일지를 보여주세요
2024년 1월 방문 기록
특정 거래처의 최근 거래 내역
```

**LOOKUP 모드 키워드**:
- 특정, 해당, 이 거래처, 이 제품
- 최근, 지난, 날짜 지정
- 거래처명, 코드

#### 🤖 RAG 모드 질문
```
거래처코드란 무엇인가요?
J-6 항목은 어떤 의미인가요?
B-2 컬럼 설명해주세요
영업일지에 어떤 내용이 기록되나요?
```

**RAG 모드 키워드**:
- 무엇, 의미, 설명, 정의
- ~란?, ~는?
- 코드북, 항목, 컬럼

## 🎯 라우팅 규칙

Router는 다음 규칙으로 모드를 선택합니다:

1. **키워드 매칭**: 각 모드별 키워드 점수 계산
2. **패턴 인식**:
   - "Top N", "상위 N" → CALC +2점
   - "~별" 패턴 → CALC +1.5점
   - "~란?" 패턴 → RAG +2.5점
   - 거래처명 포함 → LOOKUP +2점
3. **최고점 모드 선택**

### 라우팅 예시

| 질문 | CALC | LOOKUP | RAG | 선택 |
|------|------|--------|-----|------|
| "매출 상위 5개" | 4.0 | 0 | 1.5 | **CALC** |
| "한국케미칼 정보" | 0 | 2.0 | 0 | **LOOKUP** |
| "거래처코드란?" | 0 | 3.0 | 3.5 | **RAG** |

## 💡 핵심 원칙

### ✅ DO (이렇게 하세요)

1. **CALC/LOOKUP은 전체 데이터 기준**
   - RAG 검색 결과를 계산의 전제로 사용하지 않음
   - pandas가 전체 DataFrame에서 직접 계산

2. **RAG는 코드북 + 영업일지만**
   - 매출 데이터(49,480행)는 RAG 인덱싱 제외
   - 벡터 인덱스 크기: ~161개 (코드북 61 + 영업일지 100)
   - 빠른 검색, 적은 메모리

3. **라우팅 로그 표시**
   - UI 상단에 작게 표시: 모드, 신뢰도, 이유
   - 디버깅 정보 expander에 숨김

### ❌ DON'T (하지 마세요)

1. **RAG로 통계 계산 시도**
   - "매출 합계" 같은 질문을 RAG로 처리하면 부정확
   - 반드시 CALC 모드로 라우팅

2. **LOOKUP에서 집계 시도**
   - LOOKUP은 단일 레코드 조회용
   - 집계는 CALC 모드

3. **매출 데이터를 RAG에 인덱싱**
   - 5만 행 인덱싱은 느리고 불필요
   - CALC/LOOKUP으로 충분

## 🔧 주요 API

### QueryProcessorV2

```python
processor = QueryProcessorV2(data_loader, vector_store)

response = processor.process_query(
    query="매출 상위 5개 거래처는?",
    top_k=5,              # RAG 검색 문서 수
    dataset_filter="전체"  # 전체/거래처/매출/영업일지
)

# response.mode: "CALC" | "LOOKUP" | "RAG"
# response.routing: RoutingResult (신뢰도, 이유)
# response.answer: str (최종 답변)
# response.details: CalcResult | LookupResult | RAGResult
```

### Router

```python
from router import QueryRouter

router = QueryRouter()
result = router.route("매출 상위 5개 거래처는?")

# result.mode: "CALC"
# result.confidence: 1.0
# result.reasoning: "CALC=4.0, RAG=1.5 → CALC 선택"
```

### CalcEngine

```python
from calc_engine import CalcEngine

calc_engine = CalcEngine(data_loader)
result = calc_engine.calculate(
    query="거래처별 매출 합계",
    dataset_filter="매출"
)

# result.result_df: DataFrame (계산 결과)
# result.filter_conditions: List[str]
# result.sample_rows: List[Dict] (근거 샘플)
```

## 📊 성능 비교

| 항목 | V1 (기존) | V2 (Router) |
|------|-----------|-------------|
| 벡터 인덱스 크기 | 50,980개 | 161개 |
| 초기화 시간 | ~10분 | ~1분 |
| 통계 질문 정확도 | ⚠️ 낮음 (RAG 추론) | ✅ 높음 (pandas 계산) |
| 메모리 사용량 | ~2GB | ~500MB |
| 레코드 조회 속도 | 느림 (벡터 검색) | 빠름 (pandas 필터) |

## 🐛 문제 해결

### "Missing optional dependency 'tabulate'"
```bash
pip install tabulate
```

### 라우팅이 잘못됨
- `router.py`의 키워드 리스트 확인
- 점수 가중치 조정 (규칙 1~6)

### CALC 결과가 비어있음
- `calc_engine.py`의 `_select_datasets` 로직 확인
- 데이터셋 필터 확인

### RAG 답변이 부정확
- RAG 인덱스에 코드북 + 영업일지만 포함되었는지 확인
- `top_k` 값 증가 (5 → 10)

## 📝 향후 개선 사항

- [ ] DuckDB 통합 (SQL 쿼리 지원)
- [ ] 캐시 정책 개선 (TTL, 선택적 재생성)
- [ ] 라우팅 신뢰도 임계값 설정
- [ ] 다중 모드 조합 (CALC + RAG)
- [ ] 시각화 추가 (차트, 그래프)

## 📞 지원

문제가 있으면 다음을 확인하세요:

1. Python 버전: 3.8 이상
2. 모든 의존성 설치: `pip install -r requirements.txt`
3. CSV 파일 존재: 거래처 데이터.csv, sales data.csv, 영업일지2.csv, 데이터 db.csv
4. API 키 유효성: config.py의 GOOGLE_API_KEY

---

**V2의 핵심**: 정형데이터는 **pandas로 직접 계산**, RAG는 **코드북/메모 검색**에만 사용! 🎯
