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
    key_narrative: str = Field(description="Concise summary in simple everyday English")

class MultiTimeframeBias(BaseModel):
    monthly: str = Field(description="BULLISH, BEARISH, or VOLATILITY WATCH")
    weekly: str = Field(description="BULLISH, BEARISH, or VOLATILITY WATCH")
    daily: str = Field(description="BULLISH, BEARISH, or VOLATILITY WATCH")

class MacroDriver(BaseModel):
    event: str = Field(description="e.g., DXY Spike, Crude Oil Rally, Fed Rate Stance")
    fact: str = Field(description="Factual core development")
    impact: str = Field(description="Direct impact on broader market liquidity and edible oil demand")

class GeopoliticalDriver(BaseModel):
    policy: str = Field(description="e.g., Indonesian DMO Policy, EUDR Regulation, India Import Tax")
    fact: str = Field(description="Policy or regulatory fact")
    reaction: str = Field(description="Regional or international market reaction")

class MicroDerivativesDriver(BaseModel):
    catalyst: str = Field(description="e.g., MPOB Stock Report, SGS Export Estimates, Harvest Yields")
    fact: str = Field(description="Factual fundamental shift")
    price_impact: str = Field(description="Immediate price impact on FCPO")
    metric: str = Field(description="Open Interest (OI) shift, Spreads, or Funding/Margins")
    squeeze_risk: str = Field(description="Risk of short squeeze, long liquidation, or fakeout")

class AnalysisBatchResult(BaseModel):
    articles: List[ArticleEvaluation]
    asset_ticker: str = Field(default="FCPO Continuous Futures", description="Asset Ticker, e.g., FCPO / MYR")
    timeframe: str = Field(default="Intra-day / Swing", description="Scalp, Intra-day, or Swing")
    futures_bias: str = Field(description="BULLISH, BEARISH, or VOLATILITY WATCH")
    biases: MultiTimeframeBias
    confluence_score: int = Field(description="Score from 1 to 10")
    confluence_explanation: str = Field(description="1 sentence explaining why macro, micro, and policy align or conflict")
    
    macro_drivers: List[MacroDriver]
    geopolitical_drivers: List[GeopoliticalDriver]
    micro_drivers: List[MicroDerivativesDriver]
    
    key_trigger_level: str = Field(description="Crucial price point or upcoming event timestamp to watch")
    execution_risk: str = Field(description="Simple breakdown of the biggest trap or risk right now")

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
                timeframe="Intra-day / Swing",
                futures_bias="VOLATILITY WATCH",
                biases=MultiTimeframeBias(
                    monthly="NEUTRAL",
                    weekly="NEUTRAL",
                    daily="NEUTRAL"
                ),
                confluence_score=5,
                confluence_explanation="No fresh macro or fundamental headlines; market is consolidating in a tight range.",
                macro_drivers=[
                    MacroDriver(event="USD/MYR & Crude", fact="FX and Energy prices steady", impact="Neutral impact on global import pricing")
                ],
                geopolitical_drivers=[
                    GeopoliticalDriver(policy="Export Levies", fact="No policy alterations reported", reaction="Trade flows continuing normally")
                ],
                micro_drivers=[
                    MicroDerivativesDriver(
                        catalyst="MPOB Production", 
                        fact="Supply tracking seasonal averages", 
                        price_impact="Range-bound pricing", 
                        metric="Open Interest Stable", 
                        squeeze_risk="Low liquidation risk"
                    )
                ],
                key_trigger_level="Benchmark RM 4,350 support level",
                execution_risk="Low volume range-bound chop with risk of false breakouts."
            )

        prompt = f"""
        You are a Principal FCPO (Futures Crude Palm Oil) & Macro Commodity Strategist.
        Analyze the incoming news across 4 critical layers for the {session_name} market update:

        1. MACROECONOMICS: US Dollar Index (DXY), inflation figures, central bank rates, USD/MYR, and global energy/fiat liquidity (Brent Crude).
        2. GEOPOLITICS & POLICY: Local and international regulations (Indonesian DMO/levies, MPOB rules, EUDR regulations, India/China import duties).
        3. MICRO & DERIVATIVES: MPOB supply/demand estimates, SGS/AmSpec exports, harvest yields, Open Interest (OI), contract spreads, and liquidation traps.
        4. CONFLUENCE SCORE: Rate alignment from 1/10 (Conflicting signal / high risk of trap) to 10/10 (Strong alignment across macro, micro, and policy).

        FORMATTING & TONE RULES:
        - Use plain, everyday English so any trader can understand instantly.
        - Keep text scannable and direct. Never add fluff or narrative filler.
        - Map drivers to factual causes and direct impacts.

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