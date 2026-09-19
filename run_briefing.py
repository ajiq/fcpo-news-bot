import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from telegram import Bot

from config.settings import settings
from data.database import init_db, AsyncSessionLocal
from data.models import NewsArticle
from services.price_fetcher import FreeMarketDataFetcher
from services.news_fetcher import NewsIngestionService
from services.gemini_analyzer import GeminiFCPOAnalyzer
from services.telegram_formatter import TelegramFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FCPO_Runner")

async def run_single_dispatch():
    # 1. Determine Session Title based on UTC/MYT Time
    now_utc = datetime.utcnow()
    myt_hour = (now_utc.hour + 8) % 24
    
    if myt_hour < 11:
        session_name = "07:00 AM Morning Briefing"
    elif myt_hour < 16:
        session_name = "01:30 PM Mid-Day Briefing"
    else:
        session_name = "08:00 PM Night Briefing"

    logger.info(f"Starting execution for: {session_name}")

    # 2. Ensure Database initialized
    await init_db()

    async with AsyncSessionLocal() as db:
        # 3. Fetch Prices
        prices = await FreeMarketDataFetcher.get_market_overview()

        # 4. Fetch RSS News
        raw_news = await NewsIngestionService.fetch_latest_news(db)

        # 5. Retrieve 48h active narratives for deduplication
        cutoff = datetime.utcnow() - timedelta(hours=48)
        past_stmt = select(NewsArticle.key_narrative).where(
            NewsArticle.is_posted == True,
            NewsArticle.created_at >= cutoff
        )
        res = await db.execute(past_stmt)
        past_narratives = [r for r in res.scalars().all() if r]

        # 6. AI Market Synthesis via Gemini
        analyzer = GeminiFCPOAnalyzer()
        analysis_result = await analyzer.analyze_and_filter_news(raw_news, past_narratives, session_name)

        # 7. Persist articles to DB
        for art in raw_news:
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

        # 8. Format Output
        message_text = TelegramFormatter.format_briefing(session_name, prices, analysis_result)

        # 9. Safely Validate and Send via Telegram
        raw_chat_id = settings.TELEGRAM_CHAT_ID.strip() if settings.TELEGRAM_CHAT_ID else ""
        if not raw_chat_id:
            raise ValueError(
                "CRITICAL CONFIG ERROR: 'TELEGRAM_CHAT_ID' secret is missing or empty! "
                "Please add TELEGRAM_CHAT_ID to your GitHub Repository Secrets."
            )

        # Allow numeric IDs as well as string channel usernames
        try:
            target_chat_id = int(raw_chat_id)
        except ValueError:
            target_chat_id = raw_chat_id

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=target_chat_id,
            text=message_text,
            parse_mode="HTML"
        )
        logger.info("Briefing sent successfully to Telegram!")

if __name__ == "__main__":
    asyncio.run(run_single_dispatch())