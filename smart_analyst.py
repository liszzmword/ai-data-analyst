"""
스마트 데이터 분석기
업로드된 데이터를 자동 분석하고 Gemini로 인사이트 제공
"""
import google.generativeai as genai
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import base64

from config import GOOGLE_API_KEY
from upload_handler import UploadHandler, UploadedFile


# Gemini API 설정
genai.configure(api_key=GOOGLE_API_KEY)


@dataclass
class AnalysisResult:
    """분석 결과"""
    query: str
    data_context: str  # 사용된 데이터 요약
    gemini_response: str  # Gemini 응답
    charts: List[Dict] = None  # 차트 데이터
    tables: List[pd.DataFrame] = None  # 결과 테이블


class SmartAnalyst:
    """업로드된 데이터를 분석하는 AI 분석가"""

    def __init__(self, upload_handler: UploadHandler):
        self.upload_handler = upload_handler
        self.llm = genai.GenerativeModel('gemini-2.5-pro')  # 최신 Pro 모델
        print("✓ 스마트 분석기 초기화 (Gemini 2.5 Pro)")

    def analyze(self, query: str, include_images: bool = True, conversation_context: list = None) -> AnalysisResult:
        """
        질문에 대한 분석 수행 (대화 컨텍스트 지원)

        Args:
            query: 사용자 질문
            include_images: 이미지 포함 여부
            conversation_context: 이전 대화 컨텍스트 (최근 3개)

        Returns:
            AnalysisResult
        """
        print(f"\n{'='*60}")
        print(f"🔍 질문: {query}")
        if conversation_context:
            print(f"📝 이전 대화: {len(conversation_context)}개")
        print(f"{'='*60}")

        # 1. 데이터 컨텍스트 구성
        data_context = self._build_data_context(query, include_images)

        # 2. Gemini 분석 (대화 컨텍스트 포함)
        gemini_response = self._generate_analysis(query, data_context, include_images, conversation_context)

        # 3. 결과 테이블/차트 추출 (필요시)
        tables, charts = self._extract_results(query, data_context)

        return AnalysisResult(
            query=query,
            data_context=data_context,
            gemini_response=gemini_response,
            charts=charts,
            tables=tables
        )

    def _build_data_context(self, query: str, include_images: bool) -> str:
        """데이터 컨텍스트 구성 - 다중 파일 조인 지원"""
        print("📊 데이터 컨텍스트 구성 중...")

        context_parts = []
        context_parts.append("=== 업로드된 데이터 ===\n")

        # DataFrame 데이터
        dataframes = self.upload_handler.get_all_dataframes()
        if dataframes:
            context_parts.append(f"**테이블 데이터** ({len(dataframes)}개 파일):\n")

            # 여러 파일이 있고 거래처 기준 조인 가능한 경우
            if len(dataframes) > 1:
                joined_df = self._join_dataframes(dataframes)
                if joined_df is not None:
                    context_parts.append(f"\n[통합 데이터 (거래처 기준 조인)]")
                    context_parts.append(f"- 총 행 수: {len(joined_df):,}")
                    context_parts.append(f"- 총 열 수: {len(joined_df.columns)}")
                    context_parts.append(f"- 거래처 수: {joined_df['거래처'].nunique() if '거래처' in joined_df.columns else 'N/A'}\n")

                    # 조인된 데이터로 분석
                    relevant_data = self._find_relevant_data(query, joined_df, "통합 데이터")
                    if relevant_data:
                        context_parts.append(f"관련 데이터:")
                        context_parts.append(relevant_data)

                    # 개별 파일 정보도 간략히 표시
                    context_parts.append(f"\n**개별 파일 정보**:")
                    for filename, df in dataframes.items():
                        context_parts.append(f"- {filename}: {len(df):,}행, {len(df.columns)}열")
                else:
                    # 조인 실패 시 개별 파일로 분석
                    for filename, df in dataframes.items():
                        context_parts.append(f"\n[{filename}]")
                        context_parts.append(f"- 행 수: {len(df):,}")
                        context_parts.append(f"- 열: {', '.join(df.columns[:10].tolist())}")

                        relevant_data = self._find_relevant_data(query, df, filename)
                        if relevant_data:
                            context_parts.append(f"\n관련 데이터:")
                            context_parts.append(relevant_data)
            else:
                # 파일이 1개인 경우 기존 방식
                for filename, df in dataframes.items():
                    context_parts.append(f"\n[{filename}]")
                    context_parts.append(f"- 행 수: {len(df):,}")
                    context_parts.append(f"- 열: {', '.join(df.columns[:10].tolist())}")

                    relevant_data = self._find_relevant_data(query, df, filename)
                    if relevant_data:
                        context_parts.append(f"\n관련 데이터:")
                        context_parts.append(relevant_data)

        # 이미지 데이터
        if include_images:
            images = [f for f in self.upload_handler.uploaded_files if f.type == 'image']
            if images:
                context_parts.append(f"\n**이미지** ({len(images)}개):")
                for img_file in images:
                    context_parts.append(f"- {img_file.name}")

        return "\n".join(context_parts)

    def _join_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """여러 DataFrame을 거래처 기준으로 조인 (거래처코드 ↔ 거래처명 매핑 지원)"""
        try:
            # 1. 거래처 코드 ↔ 거래처명 매핑 테이블 생성
            code_to_name_map = {}
            name_to_code_map = {}

            for filename, df in dataframes.items():
                if '거래처 코드' in df.columns and '거래처' in df.columns:
                    for _, row in df[['거래처 코드', '거래처']].dropna().iterrows():
                        code = str(row['거래처 코드']).strip()
                        name = str(row['거래처']).strip()
                        code_to_name_map[code] = name
                        name_to_code_map[name] = code
                elif '거래처 코드' in df.columns and '거래처명' in df.columns:
                    for _, row in df[['거래처 코드', '거래처명']].dropna().iterrows():
                        code = str(row['거래처 코드']).strip()
                        name = str(row['거래처명']).strip()
                        code_to_name_map[code] = name
                        name_to_code_map[name] = code

            print(f"  → 거래처 매핑: 코드 {len(code_to_name_map)}개, 이름 {len(name_to_code_map)}개")

            # 2. 거래처 컬럼이 있는 파일들만 선택
            joinable_dfs = []
            for filename, df in dataframes.items():
                if '거래처' in df.columns or '거래처명' in df.columns or '거래처 코드' in df.columns:
                    df_copy = df.copy()

                    # 거래처 컬럼 통일 (우선순위: 거래처 > 거래처명 > 거래처 코드를 이름으로 변환)
                    if '거래처' not in df_copy.columns:
                        if '거래처명' in df_copy.columns:
                            df_copy['거래처'] = df_copy['거래처명']
                        elif '거래처 코드' in df_copy.columns:
                            # 거래처 코드를 거래처명으로 변환
                            df_copy['거래처'] = df_copy['거래처 코드'].apply(
                                lambda x: code_to_name_map.get(str(x).strip(), str(x)) if pd.notna(x) else None
                            )
                            print(f"  → {filename}: 거래처 코드 → 거래처명 변환")

                    # 파일명을 prefix로 컬럼명 변경 (중복 방지)
                    file_prefix = filename.replace('.csv', '').replace(' ', '_').replace('(', '').replace(')', '').replace('ver1', '').replace('_1', '')
                    rename_dict = {}
                    important_cols = ['거래처', '거래처명', '거래처 코드', '매출일', '거래일', '합계', '총 판매금액', '공급가액', '마진율', '제품명', '제품군']

                    for col in df_copy.columns:
                        if col not in important_cols:
                            rename_dict[col] = f"{file_prefix}_{col}"

                    df_copy = df_copy.rename(columns=rename_dict)
                    joinable_dfs.append((filename, df_copy))

            if len(joinable_dfs) < 2:
                return None

            # 3. 첫 번째 DataFrame부터 순차적으로 조인
            result_df = joinable_dfs[0][1]
            print(f"  → 조인 시작: {joinable_dfs[0][0]} ({len(result_df):,}행)")

            for i in range(1, len(joinable_dfs)):
                filename, df = joinable_dfs[i]
                before_rows = len(result_df)

                # outer join으로 모든 데이터 보존
                result_df = pd.merge(
                    result_df,
                    df,
                    on='거래처',
                    how='outer',
                    suffixes=('', f'_{i}')
                )

                print(f"  → {filename} 조인: {before_rows:,}행 → {len(result_df):,}행")

            print(f"✓ 조인 완료: 총 {len(result_df):,}행, {len(result_df.columns)}열")
            return result_df

        except Exception as e:
            print(f"  ⚠ 조인 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _find_relevant_data(self, query: str, df: pd.DataFrame, filename: str) -> str:
        """질문과 관련된 데이터 찾기 - PANDAS 계산 포함"""
        # 키워드 기반 필터링
        keywords = self._extract_keywords(query)

        relevant_parts = []

        # 컬럼명에서 키워드 찾기
        matching_cols = []
        for col in df.columns:
            if any(keyword in str(col).lower() for keyword in keywords):
                matching_cols.append(col)

        # ===== 특정 거래처 검색 (최우선) =====
        company_name = self._extract_company_name(query, df)
        if company_name:
            calculated_data = self._analyze_specific_company(company_name, df, query)
            if calculated_data:
                relevant_parts.append("=== 특정 거래처 분석 ===")
                relevant_parts.append(calculated_data)
                return "\n".join(relevant_parts)

        # ===== PANDAS 계산 추가 =====
        # 상위 N개 요청 (매출 상위, 거래처 상위 등)
        if any(word in query for word in ['상위', 'top', '많이', '높은', '순위']):
            calculated_data = self._calculate_top_n(query, df)
            if calculated_data:
                relevant_parts.append("=== 계산된 결과 (Pandas 집계) ===")
                relevant_parts.append(calculated_data)

        # 합계/평균 요청
        elif any(word in query for word in ['합계', '총', '평균', '총합']):
            calculated_data = self._calculate_aggregates(query, df)
            if calculated_data:
                relevant_parts.append("=== 계산된 결과 (Pandas 집계) ===")
                relevant_parts.append(calculated_data)

        # 전체 회사/거래처 목록 요청
        elif any(word in query for word in ['전체', '모든', '리스트', '목록']) and any(word in query for word in ['회사', '거래처', '업체']):
            if '거래처' in df.columns or '거래처명' in df.columns:
                col_name = '거래처' if '거래처' in df.columns else '거래처명'
                unique_companies = df[col_name].unique()
                relevant_parts.append(f"\n전체 거래처 목록 ({len(unique_companies)}개):")
                relevant_parts.append(", ".join([str(c) for c in unique_companies[:100]]))  # 최대 100개

        # 일반 데이터 샘플 (계산 없는 경우)
        if not relevant_parts:
            if matching_cols:
                relevant_parts.append(f"관련 컬럼: {', '.join(matching_cols)}")
                # 더 많은 샘플 데이터 (5개 → 20개)
                sample_df = df[matching_cols].head(20)
                relevant_parts.append(sample_df.to_string())
            else:
                # 전체 데이터 샘플
                relevant_parts.append("데이터 샘플 (처음 20행):")
                relevant_parts.append(df.head(20).to_string())

        return "\n".join(relevant_parts) if relevant_parts else ""

    def _calculate_top_n(self, query: str, df: pd.DataFrame) -> str:
        """상위 N개 계산 (Pandas groupby + sort) - 전체 데이터 반환"""
        try:
            # N 추출 (상위 5개, Top 10 등)
            n = None  # 사용자가 명시한 경우만 제한
            for word in query.split():
                if word.isdigit():
                    n = int(word)
                    break

            results = []

            # 거래처별 매출 집계
            if '거래처' in df.columns:
                # 매출 관련 숫자 컬럼 찾기 (날짜 컬럼 제외)
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                amount_cols = [col for col in numeric_cols
                             if any(keyword in col for keyword in ['합계', '금액', '공급가액', '부가세'])
                             and '번호' not in col and '코드' not in col]

                if amount_cols:
                    for amount_col in amount_cols[:1]:  # 가장 중요한 컬럼 1개만 (합계 or 공급가액)
                        try:
                            # 거래처별 집계 - 전체 데이터
                            grouped = df.groupby('거래처')[amount_col].sum().sort_values(ascending=False)

                            # 사용자가 N을 명시한 경우만 제한
                            if n:
                                grouped = grouped.head(n)
                                results.append(f"\n[거래처별 {amount_col} 상위 {n}개]")
                            else:
                                # 전체 거래처 (너무 많으면 상위 50개)
                                if len(grouped) > 50:
                                    results.append(f"\n[거래처별 {amount_col} 전체 (총 {len(grouped)}개 중 상위 50개)]")
                                    grouped = grouped.head(50)
                                else:
                                    results.append(f"\n[거래처별 {amount_col} 전체 ({len(grouped)}개)]")

                            results.append("순위 | 거래처 | 금액")
                            results.append("-" * 50)

                            for rank, (company, value) in enumerate(grouped.items(), 1):
                                results.append(f"{rank}위 | {company} | {value:,.0f}")
                        except Exception as e:
                            print(f"컬럼 {amount_col} 계산 오류: {e}")
                            continue

            # 제품별 집계
            if '품목명' in df.columns or '제품명' in df.columns or '거래 제품명' in df.columns:
                product_col = '품목명' if '품목명' in df.columns else ('제품명' if '제품명' in df.columns else '거래 제품명')
                amount_cols = [col for col in df.select_dtypes(include=['number']).columns
                             if any(keyword in col for keyword in ['합계', '금액', '수량'])
                             and '번호' not in col and '코드' not in col]

                if amount_cols:
                    try:
                        grouped = df.groupby(product_col)[amount_cols[0]].sum().sort_values(ascending=False)

                        if n:
                            grouped = grouped.head(n)
                            results.append(f"\n[{product_col}별 {amount_cols[0]} 상위 {n}개]")
                        else:
                            if len(grouped) > 30:
                                results.append(f"\n[{product_col}별 {amount_cols[0]} 상위 30개 (총 {len(grouped)}개)]")
                                grouped = grouped.head(30)
                            else:
                                results.append(f"\n[{product_col}별 {amount_cols[0]} 전체 ({len(grouped)}개)]")

                        results.append("순위 | 제품 | 금액")
                        results.append("-" * 50)

                        for rank, (product, value) in enumerate(grouped.items(), 1):
                            results.append(f"{rank}위 | {product} | {value:,.0f}")
                    except:
                        pass

            return "\n".join(results) if results else ""

        except Exception as e:
            print(f"상위 계산 오류: {e}")
            return ""

    def _calculate_aggregates(self, query: str, df: pd.DataFrame) -> str:
        """합계/평균 계산"""
        try:
            results = []

            # 숫자 컬럼만 선택
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

            # 번호, 코드 같은 의미없는 컬럼 제외
            exclude_keywords = ['번호', '코드', 'id', 'index']
            meaningful_cols = [col for col in numeric_cols
                             if not any(keyword in col.lower() for keyword in exclude_keywords)]

            if meaningful_cols:
                results.append("[전체 데이터 집계]")
                results.append("컬럼 | 합계 | 평균 | 최대 | 최소")
                results.append("-" * 70)

                for col in meaningful_cols[:10]:  # 최대 10개
                    total = df[col].sum()
                    mean = df[col].mean()
                    max_val = df[col].max()
                    min_val = df[col].min()

                    results.append(f"{col} | {total:,.0f} | {mean:,.1f} | {max_val:,.0f} | {min_val:,.0f}")

            # 거래처별 집계 (있는 경우)
            if '거래처' in df.columns and meaningful_cols:
                results.append("\n[거래처별 집계 (상위 10개)]")

                for col in meaningful_cols[:2]:
                    try:
                        grouped = df.groupby('거래처')[col].agg(['sum', 'mean', 'count']).nlargest(10, 'sum')

                        results.append(f"\n{col}:")
                        results.append("거래처 | 합계 | 평균 | 건수")
                        results.append("-" * 70)

                        for company, row in grouped.iterrows():
                            results.append(f"{company} | {row['sum']:,.0f} | {row['mean']:,.1f} | {int(row['count'])}")
                    except:
                        continue

            return "\n".join(results) if results else ""

        except Exception as e:
            print(f"집계 계산 오류: {e}")
            return ""

    def _extract_company_name(self, query: str, df: pd.DataFrame) -> Optional[str]:
        """질문에서 거래처명 추출"""
        if '거래처' not in df.columns and '거래처명' not in df.columns:
            return None

        col_name = '거래처' if '거래처' in df.columns else '거래처명'
        all_companies = df[col_name].unique()

        # 질문에서 실제 거래처명 찾기
        for company in all_companies:
            if pd.notna(company) and str(company) in query:
                return str(company)

        return None

    def _analyze_specific_company(self, company_name: str, df: pd.DataFrame, query: str) -> str:
        """특정 거래처에 대한 상세 분석"""
        try:
            col_name = '거래처' if '거래처' in df.columns else '거래처명'

            # 해당 거래처 데이터 필터링
            company_data = df[df[col_name] == company_name].copy()

            if len(company_data) == 0:
                return f"'{company_name}' 거래처의 데이터를 찾을 수 없습니다."

            results = []
            results.append(f"\n[{company_name} 거래처 상세 분석]")
            results.append(f"총 거래 건수: {len(company_data):,}건\n")

            # 숫자 컬럼 집계
            numeric_cols = company_data.select_dtypes(include=['number']).columns.tolist()
            exclude_keywords = ['번호', '코드', 'id', 'index']
            meaningful_cols = [col for col in numeric_cols
                             if not any(keyword in col.lower() for keyword in exclude_keywords)]

            if meaningful_cols:
                results.append("**주요 수치 집계**:")
                results.append("항목 | 합계 | 평균 | 최대 | 최소")
                results.append("-" * 70)

                for col in meaningful_cols[:10]:
                    total = company_data[col].sum()
                    mean = company_data[col].mean()
                    max_val = company_data[col].max()
                    min_val = company_data[col].min()
                    results.append(f"{col} | {total:,.0f} | {mean:,.1f} | {max_val:,.0f} | {min_val:,.0f}")

            # 연도별 분석 (매출일 컬럼이 있는 경우)
            if '매출일' in company_data.columns or '거래일' in company_data.columns or '일자' in company_data.columns:
                date_col = '매출일' if '매출일' in company_data.columns else ('거래일' if '거래일' in company_data.columns else '일자')

                try:
                    # 날짜 파싱
                    company_data[date_col] = pd.to_datetime(company_data[date_col], errors='coerce')
                    company_data['연도'] = company_data[date_col].dt.year

                    # 연도별 집계
                    if '합계' in company_data.columns:
                        yearly = company_data.groupby('연도')['합계'].agg(['sum', 'count']).sort_index()

                        results.append("\n**연도별 매출 추이**:")
                        results.append("연도 | 매출 합계 | 거래 건수")
                        results.append("-" * 50)

                        for year, row in yearly.iterrows():
                            results.append(f"{int(year)}년 | {row['sum']:,.0f} | {int(row['count'])}건")
                except:
                    pass

            # 제품별 분석 (있는 경우)
            product_cols = ['품목명', '제품명', '거래 제품명']
            product_col = None
            for col in product_cols:
                if col in company_data.columns:
                    product_col = col
                    break

            if product_col and '합계' in company_data.columns:
                product_sales = company_data.groupby(product_col)['합계'].sum().sort_values(ascending=False).head(10)

                results.append(f"\n**주요 거래 제품 (상위 10개)**:")
                results.append("제품명 | 매출 합계")
                results.append("-" * 50)

                for product, sales in product_sales.items():
                    results.append(f"{product} | {sales:,.0f}")

            # 전체 데이터 샘플 (최근 10건)
            results.append("\n**최근 거래 내역 (10건)**:")
            sample_data = company_data.tail(10)
            results.append(sample_data.to_string(index=False))

            return "\n".join(results)

        except Exception as e:
            print(f"거래처 분석 오류: {e}")
            return f"'{company_name}' 분석 중 오류 발생: {e}"

    def _extract_keywords(self, query: str) -> List[str]:
        """질문에서 키워드 추출"""
        # 간단한 키워드 추출 (불용어 제거)
        stopwords = ['을', '를', '이', '가', '은', '는', '의', '에', '에서', '으로', '부터', '까지',
                     '해', '해주', '해줘', '알려', '알려줘', '보여', '보여줘', '분석', '설명']

        words = query.replace('?', '').replace(',', '').split()
        keywords = [w.lower() for w in words if w not in stopwords and len(w) > 1]

        return keywords

    def _generate_analysis(self, query: str, data_context: str, include_images: bool, conversation_context: list = None) -> str:
        """Gemini로 분석 생성 (AI 판단 강화 + 대화 컨텍스트)"""
        print("🤖 Gemini 분석 중...")

        # 이미지가 있으면 multimodal 프롬프트
        if include_images:
            images = [f for f in self.upload_handler.uploaded_files if f.type == 'image']
            if images:
                return self._generate_multimodal_analysis(query, data_context, images)

        # 대화 컨텍스트 구성
        context_str = ""
        if conversation_context and len(conversation_context) > 0:
            context_str = "\n**이전 대화 내역** (참고용):\n"
            for i, ctx in enumerate(conversation_context[-3:], 1):  # 최근 3개만
                context_str += f"{i}. 질문: {ctx['query']}\n"
                context_str += f"   답변: {ctx['response'][:200]}...\n\n"  # 답변은 200자까지만

        # 텍스트 전용 프롬프트
        prompt = f"""당신은 **비즈니스 데이터 분석 전문가**입니다.

사용자가 업로드한 데이터를 바탕으로 질문에 답변하세요.
{context_str}
**현재 질문**: {query}

**업로드된 데이터 정보**:
{data_context}

**답변 작성 가이드**:
1. **데이터 요약**: 업로드된 데이터의 핵심 내용
2. **질문에 대한 답변**: 구체적인 수치와 함께 명확히 답변
3. **인사이트 및 AI 판단**:
   - 데이터에서 발견한 중요한 패턴/특징
   - **연평균 성장률 (CAGR)**: 연도별 데이터가 있으면 성장률 계산 공식 = ((최종년도값/초기년도값)^(1/(년수-1)) - 1) × 100
   - **거래 끊길 위험 분석**: 최근 3개월 매출이 이전 3개월 대비 50% 이상 감소한 거래처, 또는 거래 빈도가 급격히 줄어든 거래처
   - **고객 등급별 특징**: R(Recency), F(Frequency), M(Monetary) 기준 충성고객, 잠재고객, 위험고객 분류
   - **제품군별 트렌드**: 특정 제품군 매출 증가/감소 추세
4. **제안 및 조언**:
   - 의사결정에 도움되는 구체적 조언
   - 주의가 필요한 거래처/제품
   - 추가 분석이 필요한 부분

**중요 - 반드시 지켜야 할 규칙**:
- 한국어로 답변
- **위에 제공된 "계산된 결과" 섹션의 실제 회사명/제품명만 사용할 것**
- **절대로 존재하지 않는 회사명을 지어내지 말 것 (예: "주식회사 가나다라", "베스트출판" 같은 가짜 이름 금지)**
- **중국어 기업명을 한국어로 번역하지 말 것 (예: "쓰촨쉬홍 OPTO-전자"는 원문 그대로 사용)**
- 구체적인 숫자/사실만 언급
- 데이터에 없는 내용은 추측하지 말고 "데이터에 없음"이라고 명시
- 제공된 pandas 계산 결과를 우선적으로 활용
- 거래처 코드가 주어지면 반드시 거래처명으로 변환해서 답변
- NULL/빈 값은 "데이터 없음" 또는 "-"로 표시

답변:"""

        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"✗ Gemini 오류: {e}")
            return f"분석 중 오류 발생: {e}\n\n데이터 컨텍스트:\n{data_context}"

    def _generate_multimodal_analysis(
        self, query: str, data_context: str, images: List[UploadedFile]
    ) -> str:
        """이미지 포함 멀티모달 분석"""
        print(f"🖼️ 이미지 포함 분석 ({len(images)}개)")

        # 이미지를 Gemini가 읽을 수 있는 형태로 변환
        image_parts = []
        for img_file in images[:5]:  # 최대 5개
            # base64 → bytes
            image_bytes = base64.b64decode(img_file.content)
            image_parts.append({
                'mime_type': 'image/jpeg',
                'data': image_bytes
            })

        prompt = f"""당신은 **비즈니스 데이터 분석 전문가**입니다.

사용자가 업로드한 데이터(테이블 + 이미지/차트)를 바탕으로 질문에 답변하세요.

**사용자 질문**: {query}

**업로드된 테이블 데이터**:
{data_context}

**이미지/차트**: {len(images)}개 제공됨

**답변 작성 가이드**:
1. **이미지 분석**: 차트/그래프가 보여주는 핵심 내용
2. **데이터 해석**: 테이블 데이터와 이미지를 종합 분석
3. **인사이트**: 발견한 패턴/트렌드/이상치
4. **제안**: 의사결정에 도움되는 조언

**중요**:
- 한국어로 답변
- 이미지의 구체적 내용 언급 (예: "차트에서 2024년 매출이 급증")
- 테이블 데이터와 이미지를 연결하여 해석

답변:"""

        try:
            # Gemini에 이미지 + 텍스트 전송
            content_parts = [prompt] + image_parts
            response = self.llm.generate_content(content_parts)
            return response.text
        except Exception as e:
            print(f"✗ 멀티모달 분석 오류: {e}")
            # Fallback: 텍스트만 분석
            return self._generate_analysis(query, data_context, include_images=False)

    def _extract_results(self, query: str, data_context: str) -> tuple:
        """결과 테이블/차트 추출"""
        # 통계 계산이 필요한 경우
        tables = []
        charts = []

        dataframes = self.upload_handler.get_all_dataframes()

        # 간단한 집계 수행
        if any(word in query for word in ['상위', 'Top', '순위']):
            for filename, df in dataframes.items():
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    # 첫 번째 숫자 컬럼 기준 정렬
                    sort_col = numeric_cols[0]
                    top_df = df.nlargest(10, sort_col)
                    tables.append(top_df)
                    break

        return tables, charts


if __name__ == "__main__":
    # 테스트
    print("="*60)
    print("스마트 분석기 테스트")
    print("="*60)

    from upload_handler import UploadHandler

    # 업로드 핸들러 생성
    handler = UploadHandler()

    # 테스트 파일 로드
    test_csv = "/Users/inseoplee/Desktop/rag_Test/sales data.csv"
    with open(test_csv, 'rb') as f:
        file_bytes = f.read()
        uploaded = handler.process_upload(file_bytes, "sales data.csv")
        handler.add_file(uploaded)

    # 분석기 생성
    analyst = SmartAnalyst(handler)

    # 테스트 질문
    result = analyst.analyze("매출 상위 5개 항목을 분석하고 전략을 제안해주세요")

    print(f"\n{'='*60}")
    print("분석 결과")
    print(f"{'='*60}")
    print(result.gemini_response)
