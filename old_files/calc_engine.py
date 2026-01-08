"""
CALC 모드: pandas 기반 집계/통계 엔진
"""
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CalcResult:
    """계산 결과"""
    answer: str
    result_df: Optional[pd.DataFrame]
    filter_conditions: List[str]
    sample_rows: List[Dict]
    sql_equivalent: str


class CalcEngine:
    """pandas를 사용한 집계/통계 계산 엔진"""

    def __init__(self, data_loader):
        """
        Args:
            data_loader: DataLoader 인스턴스
        """
        self.data_loader = data_loader
        self.codebook_loader = data_loader.codebook_loader

    def calculate(self, query: str, dataset_filter: str = "전체") -> CalcResult:
        """
        질문을 분석하여 pandas 계산을 수행합니다.

        Args:
            query: 사용자 질문
            dataset_filter: 데이터셋 필터 (전체/거래처/매출/영업일지)

        Returns:
            CalcResult
        """
        print(f"\n📊 CALC 모드: pandas 계산 수행")
        print(f"  질문: {query}")
        print(f"  필터: {dataset_filter}")

        # 데이터셋 선택
        target_datasets = self._select_datasets(query, dataset_filter)
        print(f"  대상 데이터셋: {target_datasets}")

        # 질문 분석
        analysis = self._analyze_query(query)
        print(f"  분석 결과: {analysis}")

        # 계산 수행
        if len(target_datasets) == 1:
            result = self._calculate_single_dataset(
                query, target_datasets[0], analysis
            )
        else:
            result = self._calculate_multi_dataset(
                query, target_datasets, analysis
            )

        return result

    def _select_datasets(self, query: str, dataset_filter: str) -> List[str]:
        """질문과 필터에 따라 대상 데이터셋 선택"""
        if dataset_filter != "전체":
            return [dataset_filter]

        datasets = []

        # 키워드로 데이터셋 추론
        if any(word in query for word in ["거래처", "고객", "업체", "상호"]):
            datasets.append("거래처")

        if any(word in query for word in ["매출", "판매", "주문", "제품", "단가", "금액"]):
            datasets.append("매출")

        if any(word in query for word in ["영업일지", "일지", "방문", "메모", "활동"]):
            datasets.append("영업일지")

        # 기본값: 매출 데이터
        if not datasets:
            datasets.append("매출")

        return datasets

    def _analyze_query(self, query: str) -> Dict:
        """질문 분석"""
        analysis = {
            "aggregation": None,  # sum, mean, count, max, min
            "groupby": None,      # 거래처별, 제품별 등
            "sort": None,         # 상위, 하위
            "limit": None,        # Top N
            "time_range": None,   # 날짜 범위
            "filter_text": []     # 필터 조건
        }

        # 집계 함수
        if any(word in query for word in ["합계", "총", "전체"]):
            analysis["aggregation"] = "sum"
        elif any(word in query for word in ["평균"]):
            analysis["aggregation"] = "mean"
        elif any(word in query for word in ["개수", "건수", "몇", "카운트"]):
            analysis["aggregation"] = "count"
        elif any(word in query for word in ["최대", "최댓값", "최고"]):
            analysis["aggregation"] = "max"
        elif any(word in query for word in ["최소", "최솟값", "최저"]):
            analysis["aggregation"] = "min"

        # 그룹화
        if "거래처별" in query:
            analysis["groupby"] = "거래처"
        elif "제품별" in query or "품목별" in query:
            analysis["groupby"] = "제품"
        elif "월별" in query:
            analysis["groupby"] = "월"
        elif "분기별" in query:
            analysis["groupby"] = "분기"

        # 정렬 및 제한
        if "상위" in query or "top" in query.lower():
            analysis["sort"] = "desc"
            # Top N 추출
            match = re.search(r'(top|상위|하위)\s*(\d+)', query.lower())
            if match:
                analysis["limit"] = int(match.group(2))
            else:
                analysis["limit"] = 5  # 기본값
        elif "하위" in query:
            analysis["sort"] = "asc"
            match = re.search(r'하위\s*(\d+)', query)
            if match:
                analysis["limit"] = int(match.group(2))
            else:
                analysis["limit"] = 5

        # 날짜 범위
        year_match = re.search(r'(\d{4})년', query)
        month_match = re.search(r'(\d+)월', query)
        if year_match:
            analysis["time_range"] = {"year": year_match.group(1)}
            if month_match:
                analysis["time_range"]["month"] = month_match.group(1)

        return analysis

    def _calculate_single_dataset(
        self, query: str, dataset_name: str, analysis: Dict
    ) -> CalcResult:
        """단일 데이터셋에 대한 계산"""
        df = self.data_loader.get_dataframe(dataset_name)
        if df is None:
            return CalcResult(
                answer="데이터를 로드할 수 없습니다.",
                result_df=None,
                filter_conditions=[],
                sample_rows=[],
                sql_equivalent=""
            )

        filter_conditions = []
        sql_parts = [f"SELECT * FROM {dataset_name}"]

        # 날짜 필터 적용
        if analysis["time_range"]:
            time_filter = analysis["time_range"]
            # A-2 컬럼 (날짜)이 있는지 확인
            if 'A-2' in df.columns:
                original_len = len(df)
                if "year" in time_filter:
                    df = df[df['A-2'].astype(str).str.contains(time_filter["year"], na=False)]
                    filter_conditions.append(f"{time_filter['year']}년 데이터")
                if "month" in time_filter:
                    month_str = time_filter["month"].zfill(2)
                    df = df[df['A-2'].astype(str).str.contains(f"-{month_str}", na=False)]
                    filter_conditions.append(f"{time_filter['month']}월 데이터")
                print(f"  날짜 필터: {original_len} → {len(df)} 행")

        # 그룹화 및 집계
        if analysis["groupby"]:
            result_df = self._perform_groupby(df, analysis, dataset_name)
        else:
            result_df = self._perform_simple_aggregation(df, analysis, dataset_name)

        # 정렬 및 제한
        if analysis["sort"] and result_df is not None:
            # 첫 번째 숫자 컬럼으로 정렬
            numeric_cols = result_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                sort_col = numeric_cols[0]
                ascending = (analysis["sort"] == "asc")
                result_df = result_df.sort_values(by=sort_col, ascending=ascending)

                if analysis["limit"]:
                    result_df = result_df.head(analysis["limit"])
                    filter_conditions.append(f"{'상위' if not ascending else '하위'} {analysis['limit']}개")

        # 답변 생성
        answer = self._generate_calc_answer(query, result_df, filter_conditions, analysis)

        # 샘플 행 추출
        sample_rows = self._extract_sample_rows(result_df, limit=5)

        return CalcResult(
            answer=answer,
            result_df=result_df,
            filter_conditions=filter_conditions,
            sample_rows=sample_rows,
            sql_equivalent=" ".join(sql_parts)
        )

    def _calculate_multi_dataset(
        self, query: str, dataset_names: List[str], analysis: Dict
    ) -> CalcResult:
        """다중 데이터셋 계산 (조인 필요시)"""
        # 간단히 첫 번째 데이터셋으로 처리
        return self._calculate_single_dataset(query, dataset_names[0], analysis)

    def _perform_groupby(self, df: pd.DataFrame, analysis: Dict, dataset_name: str) -> Optional[pd.DataFrame]:
        """그룹화 및 집계 수행"""
        groupby_col = None

        if analysis["groupby"] == "거래처":
            # B-1 (거래처명) 컬럼으로 그룹화
            if 'B-1' in df.columns:
                groupby_col = 'B-1'
        elif analysis["groupby"] == "제품":
            # C-2 (제품명) 컬럼으로 그룹화
            if 'C-2' in df.columns:
                groupby_col = 'C-2'
        elif analysis["groupby"] == "월":
            # A-2 (날짜)에서 월 추출
            if 'A-2' in df.columns:
                df['월'] = pd.to_datetime(df['A-2'], errors='coerce').dt.to_period('M').astype(str)
                groupby_col = '월'

        if not groupby_col or groupby_col not in df.columns:
            return None

        # 숫자 컬럼 선택
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        if not numeric_cols:
            # 건수만 세기
            result_df = df.groupby(groupby_col).size().reset_index(name='건수')
        else:
            # 집계 함수 적용
            agg_func = analysis["aggregation"] or "sum"
            if agg_func == "sum":
                result_df = df.groupby(groupby_col)[numeric_cols].sum().reset_index()
            elif agg_func == "mean":
                result_df = df.groupby(groupby_col)[numeric_cols].mean().reset_index()
            elif agg_func == "count":
                result_df = df.groupby(groupby_col).size().reset_index(name='건수')
            elif agg_func == "max":
                result_df = df.groupby(groupby_col)[numeric_cols].max().reset_index()
            elif agg_func == "min":
                result_df = df.groupby(groupby_col)[numeric_cols].min().reset_index()
            else:
                result_df = df.groupby(groupby_col)[numeric_cols].sum().reset_index()

        # 코드북으로 컬럼명 변환
        result_df = self._translate_columns(result_df, dataset_name)

        return result_df

    def _perform_simple_aggregation(self, df: pd.DataFrame, analysis: Dict, dataset_name: str) -> Optional[pd.DataFrame]:
        """단순 집계 (그룹화 없음)"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        if not numeric_cols:
            return pd.DataFrame({"건수": [len(df)]})

        agg_func = analysis["aggregation"] or "sum"

        result_dict = {}
        for col in numeric_cols[:5]:  # 최대 5개 컬럼
            if agg_func == "sum":
                result_dict[col] = [df[col].sum()]
            elif agg_func == "mean":
                result_dict[col] = [df[col].mean()]
            elif agg_func == "count":
                result_dict[col] = [df[col].count()]
            elif agg_func == "max":
                result_dict[col] = [df[col].max()]
            elif agg_func == "min":
                result_dict[col] = [df[col].min()]

        result_df = pd.DataFrame(result_dict)

        # 코드북으로 컬럼명 변환
        result_df = self._translate_columns(result_df, dataset_name)

        return result_df

    def _translate_columns(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """코드북을 사용하여 컬럼명을 한글로 변환"""
        # 매출 데이터 → sales data 매핑
        dataset_map = {
            "거래처": "거래처 데이터",
            "매출": "sales data",
            "영업일지": "영업일지"
        }

        file_type = dataset_map.get(dataset_name, dataset_name)
        column_mapping = self.codebook_loader.get_column_mapping(file_type)

        if not column_mapping:
            return df

        # 컬럼명 변환
        rename_dict = {}
        for col in df.columns:
            if col in column_mapping:
                rename_dict[col] = column_mapping[col]

        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def _generate_calc_answer(
        self, query: str, result_df: Optional[pd.DataFrame],
        filter_conditions: List[str], analysis: Dict
    ) -> str:
        """계산 결과를 자연어 답변으로 생성"""
        if result_df is None or len(result_df) == 0:
            return "계산 결과가 없습니다. 필터 조건을 확인해주세요."

        answer_parts = []

        # 필터 조건
        if filter_conditions:
            answer_parts.append(f"**적용된 조건**: {', '.join(filter_conditions)}")
            answer_parts.append("")

        # 결과 요약
        if len(result_df) == 1 and result_df.shape[1] <= 3:
            # 단순 집계 결과
            answer_parts.append("**계산 결과**:")
            for col in result_df.columns:
                value = result_df[col].iloc[0]
                if isinstance(value, (int, float)):
                    answer_parts.append(f"- {col}: {value:,.0f}")
                else:
                    answer_parts.append(f"- {col}: {value}")
        else:
            # 테이블 형태 결과
            answer_parts.append(f"**결과**: 총 {len(result_df)}개 항목")
            answer_parts.append("")
            answer_parts.append(self._dataframe_to_markdown(result_df.head(10)))

            if len(result_df) > 10:
                answer_parts.append(f"\n*(상위 10개만 표시, 전체 {len(result_df)}개)*")

        return "\n".join(answer_parts)

    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """DataFrame을 마크다운 테이블로 변환"""
        if df is None or len(df) == 0:
            return ""

        # 숫자 포맷팅
        df_display = df.copy()
        for col in df_display.columns:
            if df_display[col].dtype in ['int64', 'float64']:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

        return df_display.to_markdown(index=False)

    def _extract_sample_rows(self, result_df: Optional[pd.DataFrame], limit: int = 5) -> List[Dict]:
        """결과에서 샘플 행 추출"""
        if result_df is None or len(result_df) == 0:
            return []

        sample_df = result_df.head(limit)
        return sample_df.to_dict('records')


if __name__ == "__main__":
    # 테스트
    from data_loader import DataLoader

    print("=" * 60)
    print("CALC 엔진 테스트")
    print("=" * 60)

    data_loader = DataLoader()
    calc_engine = CalcEngine(data_loader)

    test_queries = [
        "매출 상위 5개 거래처는?",
        "거래처별 매출 합계를 알려주세요",
        "2024년 1월 매출 추이",
        "제품별 평균 단가는?",
    ]

    for query in test_queries:
        print(f"\n질문: {query}")
        print("-" * 60)
        result = calc_engine.calculate(query, dataset_filter="전체")
        print(result.answer)
        if result.sample_rows:
            print(f"\n샘플 행 ({len(result.sample_rows)}개):")
            for i, row in enumerate(result.sample_rows[:3], 1):
                print(f"  {i}. {row}")
