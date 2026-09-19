import hashlib
import feedparser
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from data.models import NewsArticle
from config.settings import settings

def generate_news_hash(title: str, url: str) -> str:
    """Generate SHA-256 hash based on normalized title string."""
    clean_str = title.strip().lower()
    return hashlib.sha256(clean_str.encode('utf-8')).hexdigest()

class NewsIngestionService:
    @staticmethod
    async def fetch_latest_news(db: AsyncSession) -> List[Dict[str, Any]]:
        raw_articles = []
        seen_in_batch = set()  # In-memory batch deduplication tracker
        
        for feed_url in settings.NEWS_RSS_FEEDS:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:10]:
                title = entry.title
                url = getattr(entry, 'link', '')
                hash_id = generate_news_hash(title, url)
                
                # 1. Skip if already seen in this current run
                if hash_id in seen_in_batch:
                    continue
                
                # 2. Skip if already exists in database (Hard Deduplication)
                stmt = select(NewsArticle).where(NewsArticle.hash_id == hash_id)
                res = await db.execute(stmt)
                if res.scalar_one_or_none() is not None:
                    continue  
                
                seen_in_batch.add(hash_id)
                raw_articles.append({
                    "hash_id": hash_id,
                    "title": title,
                    "url": url,
                    "source": getattr(entry, 'source', {}).get('title', 'AgNews')
                })
        
        return raw_articles