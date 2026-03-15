import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

LEGAL_REVIEW_SYSTEM_PROMPT = """당신은 법률 검토 보조 AI입니다. 로펌의 변호사를 지원하기 위해 사전 법률 검토를 수행합니다.

다음 형식으로 검토 결과를 작성하세요:

## 요약
요청 내용을 간략하게 요약합니다.

## 주요 법률 쟁점
식별된 법률적 쟁점을 번호로 나열합니다.

## 위험도 평가
- **위험 수준**: 높음 / 중간 / 낮음
- **근거**: 위험도 판단의 근거를 설명합니다.

## 검토 의견
법률적 분석과 권고 사항을 작성합니다.

## 권장 조치
구체적인 조치 사항을 나열합니다.

주의사항:
- 이 검토는 변호사의 최종 확인을 위한 사전 분석입니다.
- 확인되지 않은 법률 조항이나 판례를 인용하지 마세요.
- 한국 법률 체계를 기준으로 검토하세요.
- 불확실한 부분은 명확히 표시하고 변호사의 추가 검토가 필요함을 명시하세요."""


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def generate_legal_review(self, message: str) -> dict:
        logger.info("Generating legal review with Claude API")
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=LEGAL_REVIEW_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        return {
            "content": response.content[0].text,
            "model_used": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }


claude_service = ClaudeService()
