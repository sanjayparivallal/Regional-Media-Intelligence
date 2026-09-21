"""
LFM Service.

Integration with Liquid LFM2.5-2.6B via Ollama HTTP API.
Handles entity verification, sentiment, crisis analysis, and summaries.
Forces structured JSON output with Pydantic validation.
"""

import json
import logging
import time
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Default Ollama endpoint & LFM 2.5 model
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "LiquidAI/lfm2.5-2.6b:q4_k_m"


# --- Pydantic models for LFM structured output ---


class LFMEntityResult(BaseModel):
    """Validated entity verification output."""
    entities: List[Dict[str, Any]] = Field(default_factory=list)


class LFMSentimentResult(BaseModel):
    """Validated sentiment analysis output."""
    sentiment: str = Field(description="positive, neutral, or negative")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class LFMCrisisResult(BaseModel):
    """Validated crisis analysis output."""
    crisis: bool = False
    category: str = ""
    reason: str = ""
    severity: float = Field(default=0.0, ge=0.0, le=1.0)


class LFMSummaryResult(BaseModel):
    """Validated summary output."""
    summary: str = ""


class LFMAnalysisResult(BaseModel):
    """Combined LFM analysis output."""
    entities: Dict[str, Any] = Field(default_factory=dict)
    sentiment: Dict[str, Any] = Field(default_factory=lambda: {"sentiment": "neutral", "confidence": 0.0})
    crisis: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


@dataclass
class LFMServiceResult:
    """Result from LFM analysis."""
    entities: Dict = field(default_factory=dict)
    sentiment: Dict = field(default_factory=dict)
    crisis: Dict = field(default_factory=dict)
    summary: str = ""
    processing_time: float = 0.0
    model_used: str = MODEL_NAME
    status: str = "success"
    error: Optional[str] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "entities": self.entities,
            "sentiment": self.sentiment,
            "crisis": self.crisis,
            "summary": self.summary,
            "processing_time": self.processing_time,
            "model_used": self.model_used,
            "status": self.status,
        }


class LFMService:
    """
    LFM2.5-2.6B integration via Ollama HTTP API.

    Only processes brand-relevant articles (not entire newspapers).
    Forces structured JSON output with Pydantic validation.
    Single retry on invalid JSON, then human review.
    """

    def __init__(
        self,
        ollama_url: str = OLLAMA_URL,
        model_name: str = MODEL_NAME,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ):
        self._url = ollama_url
        self._model = model_name
        self._max_tokens = max_tokens
        self._temperature = temperature

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = httpx.get(
                self._url.replace("/api/generate", "/api/tags"),
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return any(self._model in m for m in models)
        except Exception:
            pass
        return False

    def analyze(
        self,
        article_text: str,
        entities: Optional[List[str]] = None,
        brand_name: Optional[str] = None,
    ) -> LFMServiceResult:
        """
        Run full LFM analysis on an article.

        Performs:
        1. Entity verification
        2. Sentiment analysis
        3. Crisis analysis
        4. Summary generation

        Args:
            article_text: English article text (post-translation)
            entities: Pre-detected entities for verification
            brand_name: Primary brand being monitored

        Returns:
            LFMServiceResult with validated structured output
        """
        start_time = time.time()

        if not article_text or len(article_text.strip()) < 10:
            return LFMServiceResult(
                status="skipped",
                error="Article text too short for analysis",
                processing_time=round(time.time() - start_time, 2),
            )

        # Build the analysis prompt
        prompt = self._build_prompt(article_text, entities, brand_name)

        # Try once
        result = self._call_ollama(prompt)
        if result is not None:
            parsed = self._parse_response(result)
            if parsed:
                elapsed = round(time.time() - start_time, 2)
                return LFMServiceResult(
                    entities=parsed.entities,
                    sentiment=parsed.sentiment,
                    crisis=parsed.crisis,
                    summary=parsed.summary,
                    processing_time=elapsed,
                    raw_response=result,
                )

        # Retry once with repair prompt
        logger.warning("First LFM attempt returned invalid JSON, retrying...")
        repair_prompt = self._build_repair_prompt(article_text, result)
        result2 = self._call_ollama(repair_prompt)
        if result2 is not None:
            parsed2 = self._parse_response(result2)
            if parsed2:
                elapsed = round(time.time() - start_time, 2)
                return LFMServiceResult(
                    entities=parsed2.entities,
                    sentiment=parsed2.sentiment,
                    crisis=parsed2.crisis,
                    summary=parsed2.summary,
                    processing_time=elapsed,
                    raw_response=result2,
                )

        # Both attempts failed → human review
        elapsed = round(time.time() - start_time, 2)
        logger.error("LFM analysis failed after retry. Flagging for human review.")
        return LFMServiceResult(
            status="failed_needs_review",
            error="LFM returned invalid JSON after retry. Requires human review.",
            processing_time=elapsed,
            raw_response=result or result2,
        )

    def _build_prompt(
        self,
        article_text: str,
        entities: Optional[List[str]] = None,
        brand_name: Optional[str] = None,
    ) -> str:
        """Build structured analysis prompt for LFM."""
        entity_list = ", ".join(entities) if entities else "none detected"
        if brand_name:
            brand_ctx = (
                f"TARGET COMPANY TO ANALYZE: '{brand_name}'.\n"
                f"Carefully examine the article specifically for any negative news, financial loss, regulatory action, "
                f"penalty, lawsuit, scam, fraud, safety issue, or risk concerning '{brand_name}'.\n"
                f"If negative news exists about '{brand_name}', set sentiment to 'negative', crisis to true, "
                f"and write a summary clearly highlighting the exact negative information regarding '{brand_name}'.\n"
                f"If there is NO negative news about '{brand_name}', set sentiment to 'neutral' or 'positive' and crisis to false."
            )
        else:
            brand_ctx = "Analyze general news and company mentions."

        return f"""Analyze this news article and respond with ONLY valid JSON.

Article:
{article_text[:2000]}

Pre-detected entities: {entity_list}
{brand_ctx}

Respond with this exact JSON structure:
{{
  "entities": {{
    "entities": [
      {{"text": "entity name", "type": "ORGANIZATION|PERSON|BRAND|LOCATION|GOVERNMENT_BODY", "verified": true}}
    ]
  }},
  "sentiment": {{
    "sentiment": "positive|neutral|negative",
    "confidence": 0.85,
    "reasoning": "brief reason"
  }},
  "crisis": {{
    "crisis": true,
    "category": "regulatory|fraud|legal|safety|financial|executive|general",
    "reason": "brief reason",
    "severity": 0.7
  }},
  "summary": {{
    "summary": "specific negative information or summary regarding the target company"
  }}
}}

Important: Output ONLY the JSON object, no markdown, no explanation."""

    def _build_repair_prompt(self, article_text: str, failed_response: Optional[str]) -> str:
        """Build a simpler repair prompt for retry."""
        return f"""Analyze this article. Reply with ONLY a JSON object.

Article: {article_text[:1000]}

Required JSON format:
{{
  "entities": {{"entities": []}},
  "sentiment": {{"sentiment": "neutral", "confidence": 0.5, "reasoning": ""}},
  "crisis": {{"crisis": false, "category": "", "reason": "", "severity": 0.0}},
  "summary": {{"summary": ""}}
}}

Output ONLY the JSON."""

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API and return raw response text."""
        try:
            response = httpx.post(
                self._url,
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": self._temperature,
                        "num_predict": self._max_tokens,
                    },
                },
                timeout=120.0,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    def _parse_response(self, raw: str) -> Optional[LFMAnalysisResult]:
        """Parse and validate LFM response using Pydantic."""
        if not raw:
            return None

        # Try to extract JSON from response
        text = raw.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
        else:
            logger.warning("No JSON object found in LFM response")
            return None

        try:
            data = json.loads(json_str)
            result = LFMAnalysisResult(**data)
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
        except ValidationError as e:
            logger.warning(f"Pydantic validation error: {e}")
            # Try partial parse
            try:
                data = json.loads(json_str)
                # Fill in missing fields with defaults
                result = LFMAnalysisResult(
                    entities=LFMEntityResult(**data.get("entities", {})),
                    sentiment=LFMSentimentResult(**data.get("sentiment", {"sentiment": "neutral", "confidence": 0.0})),
                    crisis=LFMCrisisResult(**data.get("crisis", {})),
                    summary=LFMSummaryResult(**data.get("summary", {})),
                )
                return result
            except Exception:
                return None
