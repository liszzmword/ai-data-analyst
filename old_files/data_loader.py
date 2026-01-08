"""
데이터 로더 및 문서 변환
"""
import pandas as pd
from typing import List, Dict
from config import (
    SALES_JOURNAL_PATH,
    SALES_DATA_PATH,
    CLIENT_DATA_PATH,
)
from utils import (
    load_csv_with_fallback,
    mask_sensitive_info,
    is_empty_value,
    extract_date_columns,
    parse_date_safe
)
from codebook_loader import get_codebook_loader


class Document:
    """RAG 문서 클래스"""

    def __init__(self, text: str, metadata: Dict):
        self.text = text
        self.metadata = metadata

    def __repr__(self):
        return f"Document(metadata={self.metadata})"


class DataLoader:
    """데이터를 로드하고 문서로 변환하는 클래스"""

    def __init__(self):
        self.codebook_loader = get_codebook_loader()
        self.documents = []
        self.raw_dataframes = {}  # {dataset_name: DataFrame}

    def load_all_data(self):
        """모든 데이터 파일을 로드하고 문서로 변환합니다."""
        print("\n📁 데이터 로딩 시작...")

        # 1. 거래처 데이터
        self._load_and_convert(
            file_path=str(CLIENT_DATA_PATH),
            file_type="거래처 데이터",
            dataset_name="거래처"
        )

        # 2. 매출 데이터
        self._load_and_convert(
            file_path=str(SALES_DATA_PATH),
            file_type="매출 데이터",
            dataset_name="매출"
        )

        # 3. 영업일지
        self._load_and_convert(
            file_path=str(SALES_JOURNAL_PATH),
            file_type="영업일지",
            dataset_name="영업일지"
        )

        print(f"\n✓ 총 {len(self.documents)} 개의 문서 생성 완료")
        return self.documents

    def _load_and_convert(self, file_path: str, file_type: str, dataset_name: str):
        """
        CSV 파일을 로드하고 문서로 변환합니다.

        Args:
            file_path: CSV 파일 경로
            file_type: 파일 타입 (코드북의 "파일 구분"과 일치해야 함)
            dataset_name: 데이터셋 이름
        """
        print(f"\n📄 {dataset_name} 로딩 중...")

        # CSV 로드
        df = load_csv_with_fallback(file_path)
        if df is None:
            print(f"✗ {dataset_name} 로드 실패")
            return

        print(f"✓ {dataset_name} 로드 완료: {len(df)} 행, {len(df.columns)} 열")

        # 원본 DataFrame 저장
        self.raw_dataframes[dataset_name] = df

        # 컬럼 매핑 가져오기
        column_mapping = self.codebook_loader.get_column_mapping(file_type)
        print(f"  코드 매핑: {len(column_mapping)} 개")

        # 날짜 컬럼 추출
        date_columns = extract_date_columns(df)
        print(f"  날짜 컬럼: {date_columns}")

        # 각 행을 문서로 변환
        documents_created = 0
        for idx, row in df.iterrows():
            doc = self._row_to_document(
                row=row,
                row_id=idx,
                dataset_name=dataset_name,
                file_type=file_type,
                column_mapping=column_mapping,
                date_columns=date_columns
            )

            if doc:
                self.documents.append(doc)
                documents_created += 1

        print(f"  → {documents_created} 개 문서 생성")

    def _row_to_document(
            self,
            row: pd.Series,
            row_id: int,
            dataset_name: str,
            file_type: str,
            column_mapping: Dict[str, str],
            date_columns: List[str]
    ) -> Document:
        """
        DataFrame의 한 행을 Document로 변환합니다.

        Args:
            row: DataFrame 행
            row_id: 행 ID
            dataset_name: 데이터셋 이름
            file_type: 파일 타입
            column_mapping: 컬럼 코드→항목명 매핑
            date_columns: 날짜 컬럼 리스트

        Returns:
            Document 객체
        """
        # 메타데이터 초기화
        metadata = {
            "dataset": dataset_name,
            "file_type": file_type,
            "row_id": int(row_id),
            "source": f"{dataset_name} (행 {row_id + 1})"
        }

        # 텍스트 내용 구성
        text_parts = []
        text_parts.append(f"[{dataset_name}]")

        # 각 컬럼 처리
        for col_code in row.index:
            value = row[col_code]

            # 빈 값 스킵
            if is_empty_value(value):
                continue

            # 컬럼명 번역
            col_name = column_mapping.get(col_code, col_code)

            # 값 처리
            value_str = str(value)

            # 민감정보 마스킹
            value_str = mask_sensitive_info(value_str)

            # 텍스트에 추가
            text_parts.append(f"{col_name}: {value_str}")

            # 특정 컬럼을 메타데이터에 추가
            # B-2 = 거래처코드
            if col_code == 'B-2':
                metadata['거래처코드'] = value_str

            # B-1 = 거래처명
            if col_code == 'B-1':
                metadata['거래처명'] = value_str

            # 날짜 컬럼 처리
            if col_code in date_columns:
                date_str = parse_date_safe(value)
                if date_str:
                    if '날짜' not in metadata:
                        metadata['날짜'] = []
                    metadata['날짜'].append(date_str)

        # 최종 텍스트 생성
        text = "\n".join(text_parts)

        # 디버깅용: 원본 코드/값도 추가
        text += f"\n\n[원본 코드]"
        for col_code in row.index[:5]:  # 처음 5개만
            value = row[col_code]
            if not is_empty_value(value):
                text += f"\n{col_code}={value}"

        return Document(text=text, metadata=metadata)

    def get_dataframe(self, dataset_name: str) -> pd.DataFrame:
        """
        특정 데이터셋의 원본 DataFrame을 반환합니다.

        Args:
            dataset_name: 데이터셋 이름

        Returns:
            DataFrame 또는 None
        """
        return self.raw_dataframes.get(dataset_name)

    def filter_documents(self, dataset_filter: str = "전체") -> List[Document]:
        """
        데이터셋 필터에 따라 문서를 필터링합니다.

        Args:
            dataset_filter: 필터 ("전체", "거래처", "매출", "영업일지")

        Returns:
            필터링된 문서 리스트
        """
        if dataset_filter == "전체":
            return self.documents

        return [doc for doc in self.documents if doc.metadata.get("dataset") == dataset_filter]


if __name__ == "__main__":
    # 테스트
    loader = DataLoader()
    loader.load_all_data()

    print("\n=== 문서 샘플 ===")
    for i, doc in enumerate(loader.documents[:3]):
        print(f"\n--- 문서 {i + 1} ---")
        print(f"메타데이터: {doc.metadata}")
        print(f"텍스트:\n{doc.text[:500]}...")
