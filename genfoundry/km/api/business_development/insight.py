from typing import List, Optional
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from typing import List, Optional

SCORE_THRESHOLD = 0.70

@dataclass
class Insight:
    title: str = ""
    content: str = ""  # Full original content
    category: str = ""
    confidence: float = 0.0
    source_url: str = ""
    relevance: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None

    def __post_init__(self):
        if not self.title:
            self.title = "Untitled Insight"
        if not self.category:
            self.category = "Unknown"

    def is_valid(self) -> bool:
        # Only basic fields required at this stage
        return bool(self.title and self.content)

    def to_dict(self):
        return {
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'confidence': self.confidence,
            'source_url': self.source_url,
        }

@dataclass
class InsightList:
    insights: List[Insight] = field(default_factory=list)

    def __post_init__(self):
        self.insights = [i for i in self.insights if i.is_valid()]

    def to_list(self) -> List[dict]:
        return [insight.to_dict() for insight in self.insights]

    @classmethod
    def from_docs(cls, docs: List[dict], score_threshold: float = SCORE_THRESHOLD) -> 'InsightList':
        insights: List[Insight] = []

        for doc in docs:
            try:
                score = doc.get("score", 0.0)
                if score < score_threshold:
                    continue  # Skip low-confidence results

                title = doc.get("title", "").strip()
                content = doc.get("content", "").strip()
                url = doc.get("url", "").strip()

                insight = Insight(
                    title=title or "Untitled Insight",
                    content=content,
                    category="",  # To be filled in later by LLM
                    confidence=score,
                    source_url=url
                )

                if insight.is_valid():
                    insights.append(insight)
                else:
                    logger.debug(f"Skipped invalid insight: {insight}")

            except Exception as e:
                logger.warning(f"Error processing doc: {e}\nDoc: {doc}")

        return cls(insights=insights)