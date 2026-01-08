"""
통합 질의 처리기 - 데이터 기반 의사결정 지원
모든 질문에 대해: 데이터 검색 → 컨텍스트 구성 → Gemini 분석 + 의견
"""
import google.generativeai as genai
import pandas as pd
from typing import Dict, Any, List
from dataclasses import dataclass

from config import GOOGLE_API_KEY
from router import QueryRouter
from calc_engine import CalcEngine
from lookup_engine import LookupEngine
from data_loader import DataLoader


# Gemini API 설정
genai.configure(api_key=GOOGLE_API_KEY)


@dataclass
class UnifiedResponse:
    """통합 응답"""
    mode: str
    query: str
    data_summary: str  # 데이터 요약
    gemini_analysis: str  # Gemini 분석 + 의견
    raw_data: Any  # 원본 계산/검색 결과
    routing_info: str


class UnifiedProcessor:
    """데이터 기반 의사결정 지원 처리기"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.router = QueryRouter()
        self.calc_engine = CalcEngine(data_loader)
        self.lookup_engine = LookupEngine(data_loader)
        self.llm = genai.GenerativeModel('gemini-2.5-flash')

        print("✓ 통합 의사결정 지원 시스템 초기화 완료")

    def process(self, query: str, dataset_filter: str = "전체") -> UnifiedResponse:
        """
        질문 처리: 데이터 수집 → Gemini 분석

        Args:
            query: 사용자 질문
            dataset_filter: 데이터셋 필터

        Returns:
            UnifiedResponse
        """
        print(f"\n{'='*60}")
        print(f"🔍 질문: {query}")
        print(f"{'='*60}")

        # 1. 라우팅
        routing = self.router.route(query)
        print(f"📍 모드: {routing.mode} ({routing.confidence:.0%})")
        print(f"   이유: {routing.reasoning}")

        # 2. 모드별 데이터 수집
        if routing.mode == "CALC":
            data_summary, raw_data = self._collect_calc_data(query, dataset_filter)
        elif routing.mode == "LOOKUP":
            data_summary, raw_data = self._collect_lookup_data(query, dataset_filter)
        else:  # RAG
            data_summary, raw_data = self._collect_rag_data(query)

        # 3. Gemini 분석 + 의견
        gemini_analysis = self._generate_analysis(query, data_summary, routing.mode)

        return UnifiedResponse(
            mode=routing.mode,
            query=query,
            data_summary=data_summary,
            gemini_analysis=gemini_analysis,
            raw_data=raw_data,
            routing_info=routing.reasoning
        )

    def _collect_calc_data(self, query: str, dataset_filter: str) -> tuple[str, Any]:
        """CALC 모드: pandas 계산 수행"""
        print("📊 pandas 계산 중...")

        result = self.calc_engine.calculate(query, dataset_filter)

        # 데이터 요약 텍스트 생성
        summary_parts = []

        if result.filter_conditions:
            summary_parts.append(f"**적용 조건**: {', '.join(result.filter_conditions)}")

        if result.result_df is not None and len(result.result_df) > 0:
            summary_parts.append(f"\n**계산 결과** ({len(result.result_df)}개 항목):\n")
            summary_parts.append(result.result_df.head(10).to_string())

            # 샘플 원본 데이터
            if result.sample_rows:
                summary_parts.append("\n\n**원본 데이터 샘플**:")
                for i, row in enumerate(result.sample_rows[:3], 1):
                    summary_parts.append(f"\n{i}. {row}")

        data_summary = "\n".join(summary_parts)

        return data_summary, result

    def _collect_lookup_data(self, query: str, dataset_filter: str) -> tuple[str, Any]:
        """LOOKUP 모드: 레코드 검색"""
        print("🔎 레코드 검색 중...")

        result = self.lookup_engine.lookup(query, dataset_filter)

        # 데이터 요약 텍스트 생성
        summary_parts = []

        if result.search_conditions:
            summary_parts.append(f"**검색 조건**: {result.search_conditions}")

        if result.found_records:
            summary_parts.append(f"\n**검색 결과**: {len(result.found_records)}개 레코드\n")

            for i, record in enumerate(result.found_records[:5], 1):
                summary_parts.append(f"\n[레코드 {i}]")
                for key, value in list(record.items())[:10]:
                    if key not in ['dataset', 'row_id']:
                        summary_parts.append(f"  {key}: {value}")
        else:
            summary_parts.append("검색 결과 없음")

        data_summary = "\n".join(summary_parts)

        return data_summary, result

    def _collect_rag_data(self, query: str) -> tuple[str, Any]:
        """RAG 모드: 코드북 정보"""
        print("📚 코드북 검색 중...")

        # 코드북에서 직접 검색
        codebook_df = self.data_loader.codebook_loader.codebook_df

        # 관련 항목 찾기
        relevant_items = []
        for idx, row in codebook_df.iterrows():
            row_text = f"{row.get('번호', '')} {row.get('항목', '')} {row.get('항목설명', '')}"
            if any(keyword in row_text for keyword in [query, query.replace(' ', '')]):
                relevant_items.append(row)

        if not relevant_items:
            # 키워드로 재검색
            for idx, row in codebook_df.iterrows():
                row_text = str(row).lower()
                if any(keyword.lower() in row_text for keyword in query.split()):
                    relevant_items.append(row)

        # 데이터 요약
        summary_parts = []
        summary_parts.append("**코드북 정보**:\n")

        for i, item in enumerate(relevant_items[:5], 1):
            summary_parts.append(f"{i}. 번호: {item.get('번호', 'N/A')}")
            summary_parts.append(f"   항목: {item.get('항목', 'N/A')}")
            summary_parts.append(f"   설명: {item.get('항목설명', 'N/A')}")
            summary_parts.append(f"   파일: {item.get('파일 구분', 'N/A')}\n")

        if not relevant_items:
            summary_parts.append("관련 코드북 항목 없음")

        data_summary = "\n".join(summary_parts)

        return data_summary, relevant_items

    def _generate_analysis(self, query: str, data_summary: str, mode: str) -> str:
        """Gemini로 데이터 분석 + 의사결정 지원"""
        print("🤖 Gemini 분석 중...")

        prompt = f"""당신은 **비즈니스 데이터 분석 전문가**입니다.

사용자는 의사결정을 위해 질문했습니다.
당신의 역할: 데이터를 분석하고, 인사이트를 도출하고, 구체적인 의견을 제시하세요.

**사용자 질문**: {query}

**수집된 데이터**:
{data_summary}

**답변 작성 가이드**:
1. **데이터 요약**: 핵심 수치/패턴을 3줄 이내로 요약
2. **분석**: 데이터가 의미하는 것 해석 (비교, 추이, 이상치 등)
3. **인사이트**: 발견한 중요한 패턴이나 특이사항
4. **의견 및 제안**:
   - 의사결정에 도움되는 구체적 조언
   - 주의할 점이나 추가 확인이 필요한 사항
   - 다음 액션 아이템 제안

**중요**:
- 한국어로 답변
- 구체적인 숫자를 언급하며 설명
- "~인 것 같습니다", "~으로 보입니다" 같은 추측성 표현 대신 데이터 기반 명확한 표현 사용
- 단순 나열이 아닌 **분석 + 의견** 제공
- 데이터가 부족하면 솔직히 말하고 필요한 추가 정보 제안

답변:"""

        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"✗ Gemini 오류: {e}")
            return f"분석 중 오류 발생: {e}\n\n수집된 데이터:\n{data_summary}"

    def format_response(self, response: UnifiedResponse) -> str:
        """응답 포맷팅"""
        parts = []

        # 헤더
        parts.append(f"# 📊 질문: {response.query}\n")
        parts.append(f"<small>🎯 처리 모드: **{response.mode}** | {response.routing_info}</small>\n")
        parts.append("---\n")

        # Gemini 분석
        parts.append("## 💡 분석 및 의견\n")
        parts.append(response.gemini_analysis)
        parts.append("\n---\n")

        # 원본 데이터
        parts.append("## 📋 수집된 데이터\n")
        parts.append(f"```\n{response.data_summary}\n```")

        return "\n".join(parts)


if __name__ == "__main__":
    # 테스트
    print("="*60)
    print("통합 의사결정 지원 시스템 테스트")
    print("="*60)

    from data_loader import DataLoader

    data_loader = DataLoader()
    data_loader.load_all_data()

    processor = UnifiedProcessor(data_loader)

    test_queries = [
        "매출 상위 5개 거래처는?",
        "한국케미칼상사에 대해 알려주고 거래 전략 제안해줘",
        "최근 영업활동은 어떤가요?",
    ]

    for query in test_queries:
        print(f"\n\n{'='*60}")
        print(f"테스트: {query}")
        print('='*60)

        response = processor.process(query)
        formatted = processor.format_response(response)
        print(formatted)
