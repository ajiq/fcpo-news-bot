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
    relevance_score: int = Field(description="Relevance score from 1 to 10")
    is_duplicate_narrative: bool = Field(description="True if narrative covered in past 48h without new facts")
    key_narrative: str = Field(description="1-sentence ELI10 summary of the article")

class TrendItem(BaseModel):
    direction: str = Field(description="Up, Down, or Sideways")
    summary: str = Field(description="ELI10 summary with everyday analogy (e.g., 'The giant cruise ship is moving UP')")

class MultiTimeframeCompass(BaseModel):
    monthly: TrendItem
    weekly: TrendItem
    daily: TrendItem

class DriverImpact(BaseModel):
    topic: str = Field(description="Driver topic (e.g., MPOB Stockpiles, Indonesia Biofuel, USD/MYR, CBOT Soyoil)")
    fact: str = Field(description="Factual core news or data detail")
    impact: str = Field(description="ELI10 direct cause-and-effect impact with everyday analogy")

class AnalysisBatchResult(BaseModel):
    articles: List[ArticleEvaluation]
    asset_ticker: str = Field(default="FCPO Continuous Futures", description="Asset Ticker")
    timeframe_focus: str = Field(default="Intra-day / Swing", description="Scalp, Intra-day, or Swing")
    futures_bias: str = Field(description="🟢 BULLISH, 🔴 BEARISH, or ⚠️ VOLATILITY WATCH")
    confluence_score: int = Field(description="Confluence score from 1 to 10")
    confluence_explanation: str = Field(description="1 simple ELI10 sentence explaining if local news, macro, and chart trends agree")
    market_mood: str = Field(description="🔥 RISK-ON, 🛡️ RISK-OFF, or ⛽ ENERGY-DRIVEN")
    market_mood_summary: str = Field(description="1 sentence summary of overall sentiment")
    
    trends: MultiTimeframeCompass
    local_drivers: List[DriverImpact]
    global_drivers: List[DriverImpact]
    derivatives_heat: List[DriverImpact]
    
    key_level_to_watch: str = Field(description="Crucial price point or exact event time")
    biggest_trap: str = Field(description="Simple ELI10 explanation of what could trap lazy traders right now")

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
                asset_ticker="FCPO Continuous Futures",
                timeframe_focus="Intra-day / Swing",
                futures_bias="⚠️ VOLATILITY WATCH",
                confluence_score=5,
                confluence_explanation="No fresh news headlines arrived; local palm oil data and global charts are resting in a tight box.",
                market_mood="⛽ ENERGY-DRIVEN",
                market_mood_summary="Market is calm and watching Crude Oil and Ringgit moves for direction.",
                trends=MultiTimeframeCompass(
                    monthly=TrendItem(direction="Sideways", summary="The big cruise ship is parked in the harbor waiting for new wind."),
                    weekly=TrendItem(direction="Sideways", summary="The ocean waves are gently floating back and forth."),
                    daily=TrendItem(direction="Sideways", summary="Today's wind is steady with no sudden pushes.")
                ),
                local_drivers=[
                    DriverImpact(topic="MPOB Stockpiles", fact="Supply levels stable", impact="Warehouse has normal stock so buyers aren't rushing.")
                ],
                global_drivers=[
                    DriverImpact(topic="Rival Oils", fact="CBOT Soyoil trading flat", impact="US soybean oil is steady, giving palm oil no strong push.")
                ],
                derivatives_heat=[
                    DriverImpact(topic="Open Interest", fact="Trader participation steady", impact="No big crowd rushing in or out right now.")
                ],
                key_level_to_watch="RM 4,350 key benchmark support zone",
                biggest_trap="Trading low-volume sideways chop without a clear breakout."
            )

        prompt = f"""
        You are an ELI10 (Explain Like I'm 10) Futures Market Intelligence AI specializing in the FCPO (Crude Palm Oil) market. 
        Your job is to process raw news feeds, economic data, geopolitical events, local regulatory releases (MPOB, BNM, tariffs), global vegetable oil correlations (CBOT Soyoil, Dalian Olein), and multi-timeframe trends for the {session_name} market update.

        Every explanation must be written so simply that a 10-year-old child could understand it instantly, while keeping data accurate and actionable for professional traders.

        AI KNOWLEDGE MATRIX TO EVALUATE:
        1. MULTI-TIMEFRAME BIAS:
           - Monthly (Big Ocean / Season): Long-term trend.
           - Weekly (Ocean Waves): Mid-term momentum.
           - Daily (Current Wind): Short-term trend. Warn if Daily opposes Monthly/Weekly (Counter-trend trap!).
        2. MARKET MOOD: Risk-On vs. Risk-Off vs. Energy-Driven (Crude oil rising makes biofuel profitable, lifting FCPO).
        3. FCPO & LOCAL DRIVERS: MPOB Stockpiles (High inventory = warehouse overflowing = lower prices), Indonesia Biofuel B35/B40 policy (Indonesia keeps more oil at home = fewer boxes for the world = higher global prices), USD/MYR currency impact (Weaker Ringgit = FCPO cheaper for foreign buyers).
        4. GLOBAL VEG-OIL & MACRO: CBOT Soyoil / Dalian Olein spreads, China & India demand (Indian import taxes/festivals), Fed rates & DXY.
        5. DERIVATIVES HEAT: Open Interest (Are new traders entering or leaving?), Liquidation traps.
        6. CONFLUENCE SCORE (1-10): 1-3 (TRAP/CONFLICTING), 4-6 (NEUTRAL/CHOPPY), 7-10 (HIGH CONFLUENCE).

        PAST 48H COVERED NARRATIVES (Mark soft duplicates as is_duplicate_narrative=True if no new facts exist):
        {past_narratives}

        INCOMING ARTICLES:
        {news_items}
        """

        candidate_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
            "gemini-2.5-flash"
        ]

        preferred = os.getenv("GEMINI_MODEL") or getattr(settings, "GEMINI_MODEL", None)
        if preferred and preferred not in candidate_models:
            candidate_models.insert(0, preferred)

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