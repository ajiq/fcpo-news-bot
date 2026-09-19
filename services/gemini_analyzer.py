import os
import logging
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from config.settings import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ArticleEvaluation(BaseModel):
    hash_id: str
    relevance_score: int = Field(description="Relevance to FCPO/Palm Oil price action from 1 to 10")
    is_duplicate_narrative: bool = Field(description="True if narrative has been covered in past 48h without new facts")
    key_narrative: str = Field(description="One sentence summary of the news development")
    market_bias: str = Field(description="BULLISH, BEARISH, or NEUTRAL")

class AnalysisBatchResult(BaseModel):
    articles: List[ArticleEvaluation]
    market_synthesis: str = Field(description="2-3 sentence executive synthesis for FCPO traders")
    overall_bias: str = Field(description="Overall day/session bias: BULLISH, BEARISH, or NEUTRAL")

class GeminiFCPOAnalyzer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key or api_key.strip() == "":
            raise ValueError(
                "CRITICAL ERROR: GEMINI_API_KEY is empty or missing! "
                "Please verify that 'GEMINI_API_KEY' is added under GitHub Repository Secrets -> Actions."
            )
        self.client = genai.Client(api_key=api_key.strip())

    async def analyze_and_filter_news(
        self, 
        news_items: List[Dict[str, Any]], 
        past_narratives: List[str],
        session_name: str
    ) -> AnalysisBatchResult:
        if not news_items:
            return AnalysisBatchResult(
                articles=[], 
                market_synthesis="No major fresh fundamental news reported in this session cycle.",
                overall_bias="NEUTRAL"
            )

        prompt = f"""
        You are a Principal FCPO (Futures Crude Palm Oil) Analyst. 
        Evaluate these incoming news headlines for the {session_name} market update.
        
        CRITICAL RULES:
        1. Rate relevance to FCPO, Soyoil (CBOT), Dalian Olein, Biodiesel, or Malaysian Ringgit on a 1-10 scale.
        2. Identify soft duplicates. Compare against past 48h active narratives: {past_narratives}. Mark `is_duplicate_narrative=True` if no new factual or numerical progress exists.
        3. Provide an executive market synthesis and session bias.
        
        INCOMING ARTICLES:
        {news_items}
        """

        # Model candidates to cycle through if a 404 NOT_FOUND is returned
        preferred_model = os.getenv("GEMINI_MODEL") or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        candidate_models = [preferred_model, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
        
        # Deduplicate candidates while preserving priority order
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_exception = None
        for model in candidate_models:
            try:
                logger.info(f"Attempting news analysis with model endpoint: {model}")
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AnalysisBatchResult,
                        temperature=0.2,
                    ),
                )
                logger.info(f"Successfully generated analysis with model: {model}")
                return response.parsed
            except ClientError as e:
                if e.code == 404 or "NOT_FOUND" in str(e):
                    logger.warning(f"Model '{model}' returned 404 NOT_FOUND. Trying next fallback model...")
                    last_exception = e
                    continue
                else:
                    raise e
            except Exception as e:
                logger.warning(f"Model '{model}' failed with error: {e}. Trying next fallback...")
                last_exception = e
                continue

        raise RuntimeError(f"All Gemini model candidates failed. Last error: {last_exception}")