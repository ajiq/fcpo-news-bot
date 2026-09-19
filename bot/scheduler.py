import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from telegram.ext import Application
from data.database import AsyncSessionLocal
from data.models import BotSubscriber, NewsArticle
from services.price_fetcher import MarketDataFetcher
from services.news_fetcher import NewsIngestionService
from services.gemini_analyzer import GeminiFCPOAnalyzer
from services.telegram_formatter import TelegramFormatter

logger = logging.getLogger(__name__)

async def execute_scheduled_update(app: Application, session_name: str):
    logger.info(f"Executing scheduled update for session: {session_name}")
    
    async with AsyncSessionLocal() as db:
        # 1. Fetch Market Prices
        prices = await MarketDataFetcher.get_market_overview()

        # 2. Ingest RSS News (Hard Deduplication via Hash)
        raw_news = await NewsIngestionService.fetch_latest_news(db)

        # 3. Retrieve past 48h active narratives for Gemini soft deduplication
        cutoff = datetime.utcnow() - timedelta(hours=48)
        past_stmt = select(NewsArticle.key_narrative).where(
            NewsArticle.is_posted == True, 
            NewsArticle.created_at >= cutoff
        )
        res = await db.execute(past_stmt)
        past_narratives = [r for r in res.scalars().all() if r]

        # 4. Filter & Analyze with Gemini API
        analyzer = GeminiFCPOAnalyzer()
        analysis_result = await analyzer.analyze_and_filter_news(raw_news, past_narratives, session_name)

        # 5. Persist fresh valid articles to DB
        for art in raw_news:
            # find matching evaluation
            eval_item = next((e for e in analysis_result.articles if e.hash_id == art["hash_id"]), None)
            rel_score = eval_item.relevance_score if eval_item else 0
            narrative = eval_item.key_narrative if eval_item else art["title"]
            
            db_article = NewsArticle(
                hash_id=art["hash_id"],
                title=art["title"],
                url=art["url"],
                source=art["source"],
                relevance_score=rel_score,
                key_narrative=narrative,
                is_posted=(rel_score >= 7 and not getattr(eval_item, 'is_duplicate_narrative', False)),
                posted_schedule=session_name
            )
            db.add(db_article)
        await db.commit()

        # 6. Format Message Template
        message_text = TelegramFormatter.format_briefing(session_name, prices, analysis_result)

        # 7. Broadcast to active subscribers
        sub_stmt = select(BotSubscriber.chat_id).where(BotSubscriber.is_active == True)
        subs = await db.execute(sub_stmt)
        chat_ids = subs.scalars().all()

        for chat_id in chat_ids:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message_text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")