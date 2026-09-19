from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config.settings import settings
from typing import List, Dict, Any

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
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

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

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisBatchResult,
                temperature=0.2,
            ),
        )
        
        return response.parsed