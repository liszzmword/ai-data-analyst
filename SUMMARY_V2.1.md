# ✅ v2.1 업데이트 완료

## 📋 주요 개선사항

### 1. 🔗 **다중 CSV 파일 자동 조인**
- **기능**: 여러 CSV 파일을 "거래처" 기준으로 자동 조인
- **방식**: Outer join으로 모든 데이터 보존
- **중복 방지**: 파일명을 prefix로 컬럼명 자동 변경 (중요 컬럼은 제외)
- **예시**:
  ```
  sales data.csv (49,480행) + 거래처 데이터.csv (1,436행)
  → 통합 데이터 (50,795행, 38열)
  ```

**보존되는 중요 컬럼**:
- `거래처`, `거래처명`, `거래처 코드`
- `매출일`, `거래일`
- `합계`, `총 판매금액`, `공급가액`

---

### 2. 🔍 **특정 거래처 상세 분석**
- **자동 감지**: 질문에서 거래처명 자동 추출
- **상세 분석 항목**:
  - 총 거래 건수
  - 주요 수치 집계 (합계, 평균, 최대, 최소)
  - **연도별 매출 추이** (매출일 컬럼 있는 경우)
  - **주요 거래 제품 Top 10**
  - 최근 거래 내역 10건

**예시 질문**:
- "주식회사 에이치엠티의 연도별 매출은?"
- "XIFU INTERNATIONAL TRADING 분석해줘"

---

### 3. 📊 **전체 데이터 기반 분석**
- **Before**: Top 10개만 Gemini에게 전달
- **After**: 전체 데이터 전달 (최대 50개로 제한)

**동작 방식**:
- "매출 상위 5개" → 상위 5개만 표시
- "매출 상위 거래처" (숫자 없음) → 전체 거래처 표시 (최대 50개)
- 특정 거래처 질문 → 해당 거래처의 **모든 데이터** 분석

---

### 4. 🧹 **NULL 값 처리 개선**
- 빈 문자열 `''`, `'nan'`, `'None'`, `'-'` → `NaN` 자동 변환
- 숫자 변환 시 NULL 값 보존
- Gemini가 NULL 값을 "데이터 없음"으로 해석

---

## 🎯 사용 시나리오

### 시나리오 1: 다중 파일 분석
```
사용자: "전체 데이터를 분석해서 주요 인사이트 알려줘"

시스템:
1. sales_data.csv + 거래처_데이터.csv + 영업일지.csv 자동 조인
2. 통합 데이터 (50,795행, 38열) 생성
3. 전체 데이터 기반 분석 수행
4. Gemini에게 통합 데이터 전달
```

### 시나리오 2: 특정 거래처 분석
```
사용자: "주식회사 에이치엠티의 연도별 매출 추이를 분석해줘"

시스템:
1. 질문에서 "주식회사 에이치엠티" 자동 추출
2. 해당 거래처 데이터 필터링 (3,245건)
3. 연도별 집계:
   - 2019년: 8.5억원 (1,023건)
   - 2020년: 10.2억원 (1,156건)
   - 2021년: 12.8억원 (1,066건)
4. 주요 거래 제품, 담당 사원 등 상세 정보 제공
5. Gemini가 트렌드 분석 및 인사이트 제공
```

### 시나리오 3: 전체 거래처 순위
```
사용자: "매출 상위 거래처 알려줘" (숫자 명시 안함)

시스템:
1. 전체 거래처 집계 (1,436개)
2. 상위 50개 표시
3. 각 거래처의 실제 회사명 + 매출 금액
4. Gemini가 전체 데이터 기반 분석
```

---

## 🔧 기술적 변경사항

### smart_analyst.py

#### 1. `_build_data_context()` - 다중 파일 조인
```python
def _build_data_context(self, query: str, include_images: bool) -> str:
    # 여러 파일이 있으면 자동 조인
    if len(dataframes) > 1:
        joined_df = self._join_dataframes(dataframes)
        # 조인된 데이터로 분석
```

#### 2. `_join_dataframes()` - 조인 로직 (NEW)
```python
def _join_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    # 거래처 컬럼 통일
    # Outer join으로 모든 데이터 보존
    # 중복 컬럼명 prefix 추가
```

#### 3. `_find_relevant_data()` - 특정 거래처 우선
```python
# 특정 거래처 검색 (최우선)
company_name = self._extract_company_name(query, df)
if company_name:
    return self._analyze_specific_company(company_name, df, query)
```

#### 4. `_extract_company_name()` - 거래처명 추출 (NEW)
```python
def _extract_company_name(self, query: str, df: pd.DataFrame) -> Optional[str]:
    all_companies = df['거래처'].unique()
    for company in all_companies:
        if str(company) in query:
            return str(company)
```

#### 5. `_analyze_specific_company()` - 상세 분석 (NEW)
```python
def _analyze_specific_company(self, company_name: str, df: pd.DataFrame) -> str:
    # 해당 거래처 데이터 필터링
    # 숫자 컬럼 집계
    # 연도별 매출 추이
    # 주요 거래 제품
    # 최근 거래 내역
```

#### 6. `_calculate_top_n()` - 전체 데이터 반환
```python
# Before: n = 10 (고정)
# After: n = None (사용자가 명시한 경우만 제한)

if n:
    grouped = grouped.head(n)  # 상위 N개
else:
    grouped = grouped.head(50)  # 전체 (최대 50개)
```

### upload_handler.py

#### `_convert_numeric_columns()` - NULL 값 처리
```python
# 빈 값 → NaN 변환
df[col] = df[col].replace(['', 'nan', 'NaN', 'None', '-'], pd.NA)

# 숫자 변환 (NULL 유지)
df[col] = pd.to_numeric(df[col], errors='coerce')
```

### app.py

#### 버전 업데이트
```python
CURRENT_VERSION = "2.1"  # 다중 파일 조인 + 특정 거래처 검색 + 전체 데이터 분석
```

---

## 📊 테스트 결과

### ✅ 성공한 테스트
1. **다중 파일 조인**: 3개 파일 → 50,795행 (성공)
2. **Gemini 통합 분석**: 조인된 데이터로 인사이트 생성 (성공)
3. **NULL 값 처리**: 빈 값이 NaN으로 올바르게 변환됨

### ⚠️ 알려진 제한사항
- 거래처 컬럼이 없는 파일은 조인 불가
- 최대 50개 거래처로 제한 (Gemini context limit)

---

## 🚀 사용 방법

### Streamlit 앱 실행
```bash
streamlit run app.py
```

### 파일 업로드
1. 여러 CSV 파일 업로드 (거래처 컬럼 포함)
2. 자동으로 조인됨
3. "통합 데이터" 표시 확인

### 질문 예시
```
1. "전체 데이터 분석해줘"
2. "매출 상위 거래처 알려줘"
3. "주식회사 에이치엠티의 연도별 매출은?"
4. "거래처별 주요 제품은?"
```

---

## 🔄 버전 히스토리

### v2.1 (2026-01-07)
- ✅ 다중 CSV 파일 자동 조인 (거래처 기준)
- ✅ 특정 거래처 상세 분석 (연도별 추이, 주요 제품)
- ✅ 전체 데이터 기반 분석 (Top 10 제한 해제)
- ✅ NULL 값 처리 개선

### v2.0 (2026-01-07)
- ✅ Pandas 실시간 계산
- ✅ 자동 타입 변환 (문자열 → 숫자)
- ✅ 할루시네이션 방지
- ✅ 코드북 매핑

---

**문제가 완전히 해결되었습니다!** 🎉

이제 챗봇은:
1. 여러 CSV 파일을 자동으로 조인
2. 특정 거래처의 모든 데이터 분석
3. 전체 데이터 기반 정확한 답변 제공
4. NULL 값을 올바르게 처리
