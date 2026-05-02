import praw
from datetime import datetime
from typing import List
from collectors.base import BaseCollector, Article
from config import config

class RedditCollector(BaseCollector):
    name = "reddit"
    
    def __init__(self):
        self.client = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
        )
    
    def fetch(self, limit: int = 50) -> List[Article]:
        articles = []
        for sub in config.REDDIT_SUBREDDITS:
            try:
                for post in self.client.subreddit(sub).new(limit=limit):
                    articles.append(Article(
                        source=f"reddit:{sub}",
                        source_type="reddit",
                        title=post.title,
                        summary=(post.selftext or "")[:500],
                        url=f"https://reddit.com{post.permalink}",
                        published_at=datetime.utcfromtimestamp(post.created_utc),
                    ))
            except Exception as e:
                print(f"[Reddit] fetch error on {sub}: {e}")
        return articles
