"""
파일 업로드 핸들러
CSV, Excel, 이미지, PDF 지원
"""
import pandas as pd
import io
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import base64


@dataclass
class UploadedFile:
    """업로드된 파일 정보"""
    name: str
    type: str  # 'csv', 'excel', 'image', 'pdf'
    content: Any  # DataFrame or image data
    size: int
    summary: str


class UploadHandler:
    """파일 업로드 및 처리"""

    SUPPORTED_FORMATS = {
        'csv': ['.csv'],
        'excel': ['.xlsx', '.xls'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
        'pdf': ['.pdf']
    }

    def __init__(self):
        self.uploaded_files: List[UploadedFile] = []
        self.codebook = self._load_codebook()

    def _load_codebook(self) -> Optional[pd.DataFrame]:
        """코드북 로드"""
        codebook_path = Path(__file__).parent / "데이터 db.csv"
        if codebook_path.exists():
            try:
                return pd.read_csv(codebook_path, encoding='utf-8-sig')
            except:
                return None
        return None

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """문자열로 저장된 숫자 컬럼을 numeric 타입으로 변환 (강화)"""
        for col in df.columns:
            # 숫자 관련 키워드가 포함된 컬럼만 시도
            numeric_keywords = ['합계', '금액', '가액', '세', '단가', '수량', '마진', '율', '%, '개', '건', '일', '월', '년', '점수']

            if any(keyword in col for keyword in numeric_keywords):
                try:
                    # 쉼표 제거 후 숫자로 변환
                    if df[col].dtype == 'object':
                        # 빈 문자열 또는 'nan'을 NaN으로 변환
                        df[col] = df[col].replace(['', 'nan', 'NaN', 'None', '-', ' '], pd.NA)

                        # 문자열에서 쉼표, 공백, % 기호 제거
                        df[col] = df[col].astype(str).str.replace(',', '').str.replace(' ', '').str.replace('%', '')

                        # numeric으로 변환 (변환 불가능한 값은 NaN, 빈 값도 NaN)
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        print(f"  → {col} 컬럼을 숫자로 변환 (NULL 값 유지)")
                except Exception as e:
                    # 변환 실패해도 계속 진행
                    pass

        return df

    def _apply_codebook(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """코드북을 사용해 컬럼명 변환"""
        if self.codebook is None:
            return df

        # 파일명에서 파일 구분 추출
        file_type_mapping = {
            'sales data': 'sales data',
            '매출': 'sales data',
            '거래처': '거래처 데이터',
            '영업일지': '영업일지'
        }

        file_type = None
        for key, value in file_type_mapping.items():
            if key in filename.lower():
                file_type = value
                break

        if not file_type:
            return df

        # 해당 파일 타입의 코드북 추출
        mapping = self.codebook[self.codebook['파일 구분'] == file_type]

        if len(mapping) == 0:
            return df

        # 컬럼명 매핑 딕셔너리 생성
        rename_dict = {}
        for _, row in mapping.iterrows():
            code = str(row['번호'])
            name = str(row['항목'])
            if code in df.columns:
                rename_dict[code] = name

        # 컬럼명 변환
        if rename_dict:
            df = df.rename(columns=rename_dict)
            print(f"✓ 코드북 적용: {len(rename_dict)}개 컬럼 변환")

        return df

    def process_upload(self, file_bytes, filename: str) -> UploadedFile:
        """
        업로드된 파일 처리

        Args:
            file_bytes: 파일 바이트
            filename: 파일명

        Returns:
            UploadedFile
        """
        file_ext = Path(filename).suffix.lower()
        file_type = self._detect_file_type(file_ext)

        print(f"📂 파일 처리: {filename} (타입: {file_type})")

        if file_type == 'csv':
            return self._process_csv(file_bytes, filename)
        elif file_type == 'excel':
            return self._process_excel(file_bytes, filename)
        elif file_type == 'image':
            return self._process_image(file_bytes, filename)
        elif file_type == 'pdf':
            return self._process_pdf(file_bytes, filename)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {file_ext}")

    def _detect_file_type(self, file_ext: str) -> str:
        """파일 확장자로 타입 감지"""
        for file_type, extensions in self.SUPPORTED_FORMATS.items():
            if file_ext in extensions:
                return file_type
        return 'unknown'

    def _process_csv(self, file_bytes, filename: str) -> UploadedFile:
        """CSV 파일 처리"""
        # 인코딩 자동 감지
        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1']

        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
                break
            except:
                continue

        if df is None:
            raise ValueError("CSV 파일을 읽을 수 없습니다")

        # 코드북으로 컬럼명 변환 시도
        df = self._apply_codebook(df, filename)

        # 숫자 컬럼 타입 변환 (문자열로 저장된 숫자를 numeric으로 변환)
        df = self._convert_numeric_columns(df)

        summary = self._generate_dataframe_summary(df)

        return UploadedFile(
            name=filename,
            type='csv',
            content=df,
            size=len(file_bytes),
            summary=summary
        )

    def _process_excel(self, file_bytes, filename: str) -> UploadedFile:
        """Excel 파일 처리"""
        df = pd.read_excel(io.BytesIO(file_bytes))
        summary = self._generate_dataframe_summary(df)

        return UploadedFile(
            name=filename,
            type='excel',
            content=df,
            size=len(file_bytes),
            summary=summary
        )

    def _process_image(self, file_bytes, filename: str) -> UploadedFile:
        """이미지 파일 처리"""
        # base64 인코딩하여 저장
        image_b64 = base64.b64encode(file_bytes).decode()

        summary = f"이미지 파일: {filename} ({len(file_bytes):,} bytes)"

        return UploadedFile(
            name=filename,
            type='image',
            content=image_b64,
            size=len(file_bytes),
            summary=summary
        )

    def _process_pdf(self, file_bytes, filename: str) -> UploadedFile:
        """PDF 파일 처리"""
        summary = f"PDF 파일: {filename} ({len(file_bytes):,} bytes)"

        return UploadedFile(
            name=filename,
            type='pdf',
            content=file_bytes,
            size=len(file_bytes),
            summary=summary
        )

    def _generate_dataframe_summary(self, df: pd.DataFrame) -> str:
        """DataFrame 요약 생성"""
        lines = []
        lines.append(f"행 수: {len(df):,}")
        lines.append(f"열 수: {len(df.columns)}")
        lines.append(f"\n컬럼 목록:")

        for col in df.columns[:20]:  # 최대 20개
            dtype = df[col].dtype
            non_null = df[col].count()
            lines.append(f"  - {col} ({dtype}): {non_null:,}개 값")

        if len(df.columns) > 20:
            lines.append(f"  ... 외 {len(df.columns) - 20}개 컬럼")

        # 샘플 데이터
        lines.append(f"\n샘플 데이터 (처음 3행):")
        lines.append(df.head(3).to_string())

        return "\n".join(lines)

    def add_file(self, uploaded_file: UploadedFile):
        """파일 목록에 추가"""
        self.uploaded_files.append(uploaded_file)
        print(f"✓ 파일 추가: {uploaded_file.name}")

    def get_all_dataframes(self) -> Dict[str, pd.DataFrame]:
        """모든 DataFrame 반환"""
        dataframes = {}
        for file in self.uploaded_files:
            if file.type in ['csv', 'excel']:
                dataframes[file.name] = file.content
        return dataframes

    def get_file_by_name(self, name: str) -> Optional[UploadedFile]:
        """파일명으로 검색"""
        for file in self.uploaded_files:
            if file.name == name:
                return file
        return None

    def clear_files(self):
        """모든 파일 제거"""
        self.uploaded_files.clear()
        print("✓ 모든 파일 제거됨")


if __name__ == "__main__":
    # 테스트
    print("="*60)
    print("업로드 핸들러 테스트")
    print("="*60)

    handler = UploadHandler()

    # CSV 테스트
    test_csv = "/Users/inseoplee/Desktop/rag_Test/거래처 데이터.csv"
    with open(test_csv, 'rb') as f:
        file_bytes = f.read()
        uploaded = handler.process_upload(file_bytes, "거래처 데이터.csv")
        handler.add_file(uploaded)
        print(f"\n파일 요약:\n{uploaded.summary}")

    print(f"\n총 업로드된 파일: {len(handler.uploaded_files)}개")
