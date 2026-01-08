"""
코드북 로더 및 코드-항목명 매핑 생성
"""
import pandas as pd
from typing import Dict
from config import CODEBOOK_PATH
from utils import load_csv_with_fallback


class CodebookLoader:
    """코드북을 로드하고 코드→항목명 매핑을 관리하는 클래스"""

    def __init__(self):
        self.codebook_df = None
        self.code_to_name = {}  # {파일구분: {코드: (항목명, 항목설명)}}
        self.load_codebook()

    def load_codebook(self):
        """코드북 CSV를 로드합니다."""
        print(f"\n📚 코드북 로딩 중: {CODEBOOK_PATH}")

        self.codebook_df = load_csv_with_fallback(str(CODEBOOK_PATH))

        if self.codebook_df is None:
            print("✗ 코드북 로드 실패")
            return

        print(f"✓ 코드북 로드 완료: {len(self.codebook_df)} 행")
        print(f"  컬럼: {list(self.codebook_df.columns)}")

        # 코드→항목명 매핑 생성
        self._create_mappings()

    def _create_mappings(self):
        """파일별로 코드→항목명 매핑을 생성합니다."""
        if self.codebook_df is None:
            return

        # 필수 컬럼 확인
        required_cols = ['파일 구분', '번호', '항목']
        for col in required_cols:
            if col not in self.codebook_df.columns:
                print(f"✗ 코드북에 필수 컬럼 '{col}'이 없습니다.")
                return

        # 파일별로 그룹화
        file_groups = self.codebook_df.groupby('파일 구분')

        for file_name, group in file_groups:
            self.code_to_name[file_name] = {}

            for _, row in group.iterrows():
                code = row.get('번호', '')
                item_name = row.get('항목', '')
                item_desc = row.get('항목설명', '')

                if pd.notna(code) and pd.notna(item_name):
                    code = str(code).strip()
                    item_name = str(item_name).strip()
                    item_desc = str(item_desc).strip() if pd.notna(item_desc) else ""

                    self.code_to_name[file_name][code] = (item_name, item_desc)

        # 매핑 결과 출력
        print(f"\n📋 코드-항목명 매핑 생성 완료:")
        for file_name, mapping in self.code_to_name.items():
            print(f"  - {file_name}: {len(mapping)} 개 코드")

    def get_column_mapping(self, file_type: str) -> Dict[str, str]:
        """
        특정 파일 타입의 코드→항목명 매핑을 반환합니다.

        Args:
            file_type: 파일 구분 (예: "거래처 데이터", "매출 데이터", "영업일지")

        Returns:
            {코드: 항목명} 딕셔너리
        """
        if file_type not in self.code_to_name:
            print(f"⚠ 파일 타입 '{file_type}'에 대한 매핑이 없습니다.")
            return {}

        # (항목명, 항목설명) 튜플에서 항목명만 추출
        return {code: name_desc[0] for code, name_desc in self.code_to_name[file_type].items()}

    def get_column_description(self, file_type: str, code: str) -> str:
        """
        특정 코드의 설명을 반환합니다.

        Args:
            file_type: 파일 구분
            code: 컬럼 코드

        Returns:
            항목 설명
        """
        if file_type not in self.code_to_name:
            return ""

        if code not in self.code_to_name[file_type]:
            return ""

        return self.code_to_name[file_type][code][1]

    def translate_column_name(self, file_type: str, code: str) -> str:
        """
        코드를 항목명으로 번역합니다.

        Args:
            file_type: 파일 구분
            code: 컬럼 코드

        Returns:
            항목명 (매핑이 없으면 원본 코드 반환)
        """
        mapping = self.get_column_mapping(file_type)
        return mapping.get(code, code)

    def get_all_file_types(self) -> list:
        """
        모든 파일 타입을 반환합니다.

        Returns:
            파일 타입 리스트
        """
        return list(self.code_to_name.keys())


# 싱글톤 인스턴스
_codebook_loader = None


def get_codebook_loader() -> CodebookLoader:
    """
    CodebookLoader 싱글톤 인스턴스를 반환합니다.

    Returns:
        CodebookLoader 인스턴스
    """
    global _codebook_loader
    if _codebook_loader is None:
        _codebook_loader = CodebookLoader()
    return _codebook_loader


if __name__ == "__main__":
    # 테스트
    loader = CodebookLoader()

    print("\n=== 코드북 로더 테스트 ===")
    print(f"파일 타입들: {loader.get_all_file_types()}")

    for file_type in loader.get_all_file_types():
        print(f"\n[{file_type}] 매핑:")
        mapping = loader.get_column_mapping(file_type)
        for code, name in list(mapping.items())[:5]:  # 처음 5개만
            desc = loader.get_column_description(file_type, code)
            print(f"  {code} → {name} ({desc})")
