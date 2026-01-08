"""
유틸리티 함수 모음
"""
import re
import pandas as pd
from typing import Optional
from config import ENCODINGS, SENSITIVE_PATTERNS


def load_csv_with_fallback(file_path: str) -> Optional[pd.DataFrame]:
    """
    여러 인코딩을 시도하며 CSV 파일을 로드합니다.

    Args:
        file_path: CSV 파일 경로

    Returns:
        DataFrame 또는 None
    """
    for encoding in ENCODINGS:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"✓ {file_path} 로드 성공 (encoding: {encoding})")
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            print(f"✗ 파일을 찾을 수 없습니다: {file_path}")
            return None
        except Exception as e:
            print(f"✗ 파일 로드 중 오류: {file_path}, {e}")
            return None

    print(f"✗ 모든 인코딩 시도 실패: {file_path}")
    return None


def mask_sensitive_info(text: str) -> str:
    """
    민감정보를 마스킹합니다.

    Args:
        text: 원본 텍스트

    Returns:
        마스킹된 텍스트
    """
    if not isinstance(text, str):
        return str(text)

    masked_text = text

    for info_type, pattern in SENSITIVE_PATTERNS.items():
        def mask_match(match):
            original = match.group(0)
            if info_type == "사업자등록번호":
                # 214-86-59900 -> 214-**-***00
                parts = original.split("-")
                if len(parts) == 3:
                    return f"{parts[0]}-**-***{parts[2][-2:]}"
            elif info_type == "주민등록번호":
                # 123456-1234567 -> 123456-*******
                parts = original.split("-")
                if len(parts) == 2:
                    return f"{parts[0]}-*******"
            elif info_type == "전화번호":
                # 010-1234-5678 -> 010-****-5678
                parts = original.split("-")
                if len(parts) == 3:
                    return f"{parts[0]}-{'*' * len(parts[1])}-{parts[2]}"
            return original

        masked_text = re.sub(pattern, mask_match, masked_text)

    return masked_text


def clean_column_name(col_name: str) -> str:
    """
    컬럼명을 정리합니다.

    Args:
        col_name: 원본 컬럼명

    Returns:
        정리된 컬럼명
    """
    if pd.isna(col_name):
        return ""
    return str(col_name).strip()


def is_empty_value(value) -> bool:
    """
    값이 비어있는지 확인합니다.

    Args:
        value: 확인할 값

    Returns:
        비어있으면 True
    """
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def format_number(value) -> str:
    """
    숫자를 포맷팅합니다.

    Args:
        value: 숫자 값

    Returns:
        포맷팅된 문자열
    """
    try:
        # 쉼표가 있는 문자열 숫자 처리
        if isinstance(value, str):
            value = value.replace(",", "")

        num = float(value)

        # 정수인 경우
        if num.is_integer():
            return f"{int(num):,}"
        else:
            return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    텍스트를 지정된 길이로 자릅니다.

    Args:
        text: 원본 텍스트
        max_length: 최대 길이

    Returns:
        잘린 텍스트
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def extract_date_columns(df: pd.DataFrame) -> list:
    """
    날짜 관련 컬럼을 추출합니다.

    Args:
        df: DataFrame

    Returns:
        날짜 컬럼명 리스트
    """
    date_columns = []

    for col in df.columns:
        col_lower = str(col).lower()
        # 날짜 관련 키워드 확인
        if any(keyword in col_lower for keyword in ['date', '날짜', '일자', 'j-1', 'a-2', 'a-3']):
            date_columns.append(col)
            continue

        # 데이터 타입 확인
        try:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_columns.append(col)
                continue
        except:
            pass

        # 샘플 데이터로 날짜 형식 확인
        try:
            sample = df[col].dropna().head(10)
            if len(sample) > 0:
                # YYYY-MM-DD 또는 YYYY.MM.DD 형식 확인
                date_pattern = r'\d{4}[-./]\d{1,2}[-./]\d{1,2}'
                if sample.astype(str).str.match(date_pattern).any():
                    date_columns.append(col)
        except:
            pass

    return date_columns


def parse_date_safe(date_str) -> Optional[str]:
    """
    안전하게 날짜를 파싱합니다.

    Args:
        date_str: 날짜 문자열

    Returns:
        파싱된 날짜 문자열 (YYYY-MM-DD) 또는 None
    """
    if pd.isna(date_str):
        return None

    try:
        # pandas로 파싱 시도
        parsed = pd.to_datetime(date_str, errors='coerce')
        if pd.notna(parsed):
            return parsed.strftime('%Y-%m-%d')
    except:
        pass

    return str(date_str)
