"""
질문 분류 라우터 (CALC/LOOKUP/RAG)
"""
import re
from typing import Literal
from dataclasses import dataclass


QueryMode = Literal["CALC", "LOOKUP", "RAG"]


@dataclass
class RoutingResult:
    """라우팅 결과"""
    mode: QueryMode
    confidence: float
    reasoning: str


class QueryRouter:
    """질문을 CALC/LOOKUP/RAG로 분류하는 라우터"""

    # CALC 모드 키워드 (집계/통계)
    CALC_KEYWORDS = [
        "합계", "총", "평균", "최대", "최소", "최댓값", "최솟값",
        "상위", "하위", "Top", "top", "랭킹", "순위",
        "추이", "전월", "전년", "증감", "증가", "감소", "변화",
        "월별", "분기별", "년도별", "기간별", "일별", "주별",
        "그룹별", "거래처별", "제품별", "품목별", "지역별", "담당자별",
        "필터", "조건", "범위",
        "몇", "얼마", "몇개", "몇건", "건수", "개수", "수량",
        "비율", "퍼센트", "%", "점유율", "비중"
    ]

    # LOOKUP 모드 키워드 (특정 레코드 조회)
    LOOKUP_KEYWORDS = [
        "특정", "해당", "이 거래처", "이 주문", "이 제품",
        "언제", "누가", "어디", "무엇",
        "주문번호", "거래코드", "사업자번호"
    ]

    # RAG 모드 키워드 (정의/설명/메모)
    RAG_KEYWORDS = [
        "이란", "무엇", "뭐야", "설명", "정의", "의미",
        "어떻게", "왜", "이유", "방법",
        "영업일지", "일지", "메모", "기록", "노트",
        "규정", "가이드", "지침", "정책",
        "코드북", "항목", "컬럼", "필드", "데이터",
        "A-", "B-", "C-", "D-", "E-", "F-", "G-", "H-", "I-", "J-"  # 코드북 코드
    ]

    def __init__(self):
        pass

    def route(self, query: str) -> RoutingResult:
        """
        질문을 분석하여 CALC/LOOKUP/RAG 중 하나로 분류합니다.

        Args:
            query: 사용자 질문

        Returns:
            RoutingResult with mode, confidence, reasoning
        """
        query_lower = query.lower()

        # 각 모드별 점수 계산
        calc_score = self._calculate_score(query_lower, self.CALC_KEYWORDS)
        lookup_score = self._calculate_score(query_lower, self.LOOKUP_KEYWORDS)
        rag_score = self._calculate_score(query_lower, self.RAG_KEYWORDS)

        # 추가 규칙 적용

        # 규칙 1: 숫자와 함께 "Top N", "상위 N" 패턴
        if re.search(r'(top|상위|하위)\s*\d+', query_lower):
            calc_score += 2.0

        # 규칙 2: "~별" 패턴 (그룹화 의도)
        if re.search(r'\w+별', query):
            calc_score += 1.5

        # 규칙 3: 비교/범위 표현
        if any(word in query for word in ["비교", "차이", "이상", "이하", "초과", "미만"]):
            calc_score += 1.0

        # 규칙 4: 물음표로 끝나고 "~란?" "~는?" "~인가요?" 패턴
        if re.search(r'(이란|란|는|은|무엇|뭐|의미|설명|인가요|인가)\?*$', query):
            rag_score += 3.0
            lookup_score -= 1.0  # LOOKUP 페널티

        # 규칙 5: 특정 거래처명이 포함된 경우
        if self._contains_specific_name(query):
            # "합계/평균" 같은 집계 키워드가 있으면 CALC, 없으면 LOOKUP
            if calc_score > 0:
                calc_score += 1.0
            else:
                lookup_score += 2.0

        # 규칙 6: 날짜 범위 패턴
        if re.search(r'\d{4}년|\d+월|\d+일|최근|지난|올해|작년', query):
            if calc_score > 0:
                calc_score += 1.0
            else:
                lookup_score += 0.5

        # 최종 결정
        scores = {
            "CALC": calc_score,
            "LOOKUP": lookup_score,
            "RAG": rag_score
        }

        max_score = max(scores.values())

        # 점수가 모두 0이면 기본값은 LOOKUP
        if max_score == 0:
            return RoutingResult(
                mode="LOOKUP",
                confidence=0.3,
                reasoning="키워드 매칭 없음 → 기본 LOOKUP 모드"
            )

        # 최고점 모드 선택
        selected_mode = max(scores.items(), key=lambda x: x[1])[0]
        confidence = min(max_score / 3.0, 1.0)  # 정규화

        reasoning = self._generate_reasoning(query, scores, selected_mode)

        return RoutingResult(
            mode=selected_mode,
            confidence=confidence,
            reasoning=reasoning
        )

    def _calculate_score(self, query: str, keywords: list) -> float:
        """키워드 매칭 점수 계산"""
        score = 0.0
        for keyword in keywords:
            if keyword.lower() in query:
                score += 1.0
        return score

    def _contains_specific_name(self, query: str) -> bool:
        """특정 거래처/제품명이 포함되어 있는지 확인"""
        # 한글 이름 패턴 (2글자 이상 연속된 한글)
        korean_pattern = r'[가-힣]{2,}'
        matches = re.findall(korean_pattern, query)

        # 질문어를 제외한 고유명사가 있는지 확인
        question_words = ["무엇", "어디", "언제", "누구", "왜", "어떻게", "합계", "평균", "알려", "보여"]
        for match in matches:
            if match not in question_words:
                return True
        return False

    def _generate_reasoning(self, query: str, scores: dict, selected_mode: str) -> str:
        """라우팅 이유 생성"""
        reasoning_parts = []

        for mode, score in scores.items():
            if score > 0:
                reasoning_parts.append(f"{mode}={score:.1f}")

        if not reasoning_parts:
            return "키워드 없음"

        reasoning = ", ".join(reasoning_parts)
        reasoning += f" → {selected_mode} 선택"

        return reasoning


if __name__ == "__main__":
    # 테스트
    router = QueryRouter()

    test_queries = [
        "매출 상위 5개 거래처는?",
        "거래처별 매출 합계를 알려주세요",
        "한국케미칼상사의 최근 거래 내역은?",
        "영업일지에서 최근 방문 기록을 보여줘",
        "거래처코드란 무엇인가요?",
        "2024년 1월 매출 추이",
        "제품별 평균 단가는?",
        "주문번호 12345의 상태는?",
    ]

    print("=" * 60)
    print("라우터 테스트")
    print("=" * 60)

    for query in test_queries:
        result = router.route(query)
        print(f"\n질문: {query}")
        print(f"  → 모드: {result.mode} (신뢰도: {result.confidence:.2f})")
        print(f"  → 이유: {result.reasoning}")
