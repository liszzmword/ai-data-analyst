"""
LOOKUP 모드: 특정 레코드 검색 엔진
"""
import pandas as pd
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LookupResult:
    """조회 결과"""
    answer: str
    found_records: List[Dict]
    search_conditions: List[str]


class LookupEngine:
    """특정 레코드를 검색하는 엔진"""

    def __init__(self, data_loader):
        """
        Args:
            data_loader: DataLoader 인스턴스
        """
        self.data_loader = data_loader
        self.codebook_loader = data_loader.codebook_loader

    def lookup(self, query: str, dataset_filter: str = "전체") -> LookupResult:
        """
        질문을 분석하여 특정 레코드를 검색합니다.

        Args:
            query: 사용자 질문
            dataset_filter: 데이터셋 필터

        Returns:
            LookupResult
        """
        print(f"\n🔎 LOOKUP 모드: 레코드 검색")
        print(f"  질문: {query}")
        print(f"  필터: {dataset_filter}")

        # 데이터셋 선택
        target_datasets = self._select_datasets(query, dataset_filter)
        print(f"  대상 데이터셋: {target_datasets}")

        # 검색 조건 추출
        search_conditions = self._extract_search_conditions(query)
        print(f"  검색 조건: {search_conditions}")

        # 레코드 검색
        found_records = []
        for dataset_name in target_datasets:
            records = self._search_in_dataset(dataset_name, search_conditions)
            found_records.extend(records)

        # 답변 생성
        answer = self._generate_lookup_answer(query, found_records, search_conditions)

        return LookupResult(
            answer=answer,
            found_records=found_records,
            search_conditions=search_conditions
        )

    def _select_datasets(self, query: str, dataset_filter: str) -> List[str]:
        """질문과 필터에 따라 대상 데이터셋 선택"""
        if dataset_filter != "전체":
            return [dataset_filter]

        datasets = []

        # 키워드로 데이터셋 추론
        if any(word in query for word in ["거래처", "고객", "업체", "상호", "사업자"]):
            datasets.append("거래처")

        if any(word in query for word in ["매출", "판매", "주문", "제품", "거래", "내역"]):
            datasets.append("매출")

        if any(word in query for word in ["영업일지", "일지", "방문", "메모", "활동"]):
            datasets.append("영업일지")

        # 기본값: 모든 데이터셋
        if not datasets:
            datasets = ["거래처", "매출", "영업일지"]

        return datasets

    def _extract_search_conditions(self, query: str) -> Dict[str, str]:
        """질문에서 검색 조건 추출"""
        conditions = {}

        # 한글 이름 패턴 (거래처명/제품명)
        korean_names = re.findall(r'[가-힣]{2,}(?:상사|케미칼|이엠|기공|신문|코리아|산업|전자)?', query)
        question_words = ["무엇", "어디", "언제", "누구", "왜", "어떻게", "합계", "평균", "알려", "보여", "최근", "방문"]

        for name in korean_names:
            if name not in question_words:
                conditions["name"] = name
                break

        # 날짜 패턴
        year_match = re.search(r'(\d{4})년', query)
        month_match = re.search(r'(\d+)월', query)
        if year_match:
            conditions["year"] = year_match.group(1)
            if month_match:
                conditions["month"] = month_match.group(1).zfill(2)

        # 상대 시간
        if "최근" in query:
            conditions["recent"] = True
        elif "지난" in query:
            conditions["past"] = True

        # 코드 패턴
        code_match = re.search(r'[A-Z0-9]{3,}', query)
        if code_match:
            conditions["code"] = code_match.group(0)

        return conditions

    def _search_in_dataset(self, dataset_name: str, conditions: Dict) -> List[Dict]:
        """데이터셋에서 조건에 맞는 레코드 검색"""
        df = self.data_loader.get_dataframe(dataset_name)
        if df is None:
            return []

        # 초기 데이터프레임
        filtered_df = df.copy()

        # 이름 조건
        if "name" in conditions:
            name = conditions["name"]
            # B-1 (거래처명) 또는 C-2 (제품명) 검색
            name_cols = []
            if 'B-1' in df.columns:
                name_cols.append('B-1')
            if 'C-2' in df.columns:
                name_cols.append('C-2')

            if name_cols:
                mask = pd.Series([False] * len(filtered_df))
                for col in name_cols:
                    mask |= filtered_df[col].astype(str).str.contains(name, na=False)
                filtered_df = filtered_df[mask]

        # 코드 조건
        if "code" in conditions:
            code = conditions["code"]
            # B-2 (거래처코드) 검색
            if 'B-2' in df.columns:
                filtered_df = filtered_df[
                    filtered_df['B-2'].astype(str).str.contains(code, na=False)
                ]

        # 날짜 조건
        if "year" in conditions:
            year = conditions["year"]
            if 'A-2' in df.columns:
                filtered_df = filtered_df[
                    filtered_df['A-2'].astype(str).str.contains(year, na=False)
                ]

        if "month" in conditions:
            month = conditions["month"]
            if 'A-2' in df.columns:
                filtered_df = filtered_df[
                    filtered_df['A-2'].astype(str).str.contains(f"-{month}", na=False)
                ]

        # 최근 데이터 (날짜 컬럼 기준 정렬)
        if conditions.get("recent") and 'A-2' in filtered_df.columns:
            filtered_df = filtered_df.sort_values('A-2', ascending=False)

        # 결과 제한 (최대 10개)
        filtered_df = filtered_df.head(10)

        # 코드북으로 컬럼명 변환
        filtered_df = self._translate_columns(filtered_df, dataset_name)

        # Dictionary로 변환
        records = []
        for idx, row in filtered_df.iterrows():
            record = {"dataset": dataset_name, "row_id": int(idx)}
            for col, value in row.items():
                if pd.notna(value):
                    # 민감정보 마스킹
                    value_str = str(value)
                    if self._is_sensitive(col):
                        from utils import mask_sensitive_info
                        value_str = mask_sensitive_info(value_str)
                    record[col] = value_str
            records.append(record)

        return records

    def _translate_columns(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """코드북을 사용하여 컬럼명을 한글로 변환"""
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

    def _is_sensitive(self, column_name: str) -> bool:
        """민감정보 컬럼인지 확인"""
        sensitive_keywords = ["사업자", "주민", "등록번호", "전화", "핸드폰", "이메일"]
        return any(keyword in column_name for keyword in sensitive_keywords)

    def _generate_lookup_answer(
        self, query: str, found_records: List[Dict], search_conditions: Dict
    ) -> str:
        """조회 결과를 자연어 답변으로 생성"""
        if not found_records:
            return f"검색 조건에 맞는 레코드를 찾을 수 없습니다.\n검색 조건: {search_conditions}"

        answer_parts = []

        # 검색 조건
        condition_texts = []
        if "name" in search_conditions:
            condition_texts.append(f"이름: {search_conditions['name']}")
        if "year" in search_conditions:
            year_text = f"{search_conditions['year']}년"
            if "month" in search_conditions:
                year_text += f" {search_conditions['month']}월"
            condition_texts.append(year_text)
        if "recent" in search_conditions:
            condition_texts.append("최근 데이터")

        if condition_texts:
            answer_parts.append(f"**검색 조건**: {', '.join(condition_texts)}")
            answer_parts.append("")

        # 결과 요약
        answer_parts.append(f"**검색 결과**: 총 {len(found_records)}개 레코드")
        answer_parts.append("")

        # 레코드 상세
        for i, record in enumerate(found_records, 1):
            answer_parts.append(f"### [{i}] {record.get('dataset', '')} (행 {record.get('row_id', 'N/A')})")

            # 주요 필드만 표시
            display_fields = []
            for key, value in record.items():
                if key not in ["dataset", "row_id"]:
                    display_fields.append(f"- **{key}**: {value}")

            answer_parts.extend(display_fields[:10])  # 최대 10개 필드
            answer_parts.append("")

        if len(found_records) > 5:
            answer_parts.append(f"*(상위 5개만 상세 표시, 전체 {len(found_records)}개)*")

        return "\n".join(answer_parts)


if __name__ == "__main__":
    # 테스트
    from data_loader import DataLoader

    print("=" * 60)
    print("LOOKUP 엔진 테스트")
    print("=" * 60)

    data_loader = DataLoader()
    lookup_engine = LookupEngine(data_loader)

    test_queries = [
        "한국케미칼상사의 정보를 알려주세요",
        "이놀의 거래처 정보를 알려주세요",
        "최근 영업일지를 보여주세요",
    ]

    for query in test_queries:
        print(f"\n질문: {query}")
        print("-" * 60)
        result = lookup_engine.lookup(query, dataset_filter="전체")
        print(result.answer)
