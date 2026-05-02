from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List

@dataclass
class Article:
    source: str          # e.g. "reddit:wallstreetbets"
    source_type: str     # reddit / rss / sec / arxiv
    title: str
    summary: str
    url: str
    lang: str = "en"
    published_at: datetime = None
    
    def to_dict(self):
        return asdict(self)


class BaseCollector:
    name = "base"
    
    def fetch(self) -> List[Article]:
        raise NotImplementedError
