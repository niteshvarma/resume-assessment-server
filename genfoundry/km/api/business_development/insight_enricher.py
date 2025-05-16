import json
import logging
import re
from typing import List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from genfoundry.km.api.business_development.insight import Insight, InsightList

# Initialize logging
logger = logging.getLogger(__name__)

# Prompt template for enrichment
prompt_template = PromptTemplate(
    input_variables=["content"],
    template="""
You are a business insights assistant that enriches news with structured metadata for recruitment industry professionals.

Given the following content and source URL, extract and complete the following fields, and return a valid **minified JSON object only**:

- **title**: Generate a meaningful title if missing; otherwise use the original. If you can’t generate one, default to `"Untitled Insight"`.
- **category**: Must be one of the following (pick the most relevant based on the content):
  - **Layoffs** (e.g., job cuts, downsizing, redundancies)
  - **Hiring** (e.g., job openings, recruitment drives, team expansion)
  - **Leadership Changes** (e.g., new CEO, executive departures, key promotions)
  - **M&A** (mergers and acquisitions activity)
  - **Strategic Partnerships** (alliances, co-branded initiatives, joint ventures)
  - **Investments** (new investments made *by* the company)
  - **New Funding** (new funding *received* by the company such as Series A, B, etc.) 
  - **Product Launches** (new products, services, or features)
  - **Spin-offs** (splits, divestitures, or spinoff plans)
  - **Other** (when none of the above clearly apply)
- **content**: The original content provided in the input.
- **confidence**: A float between 0.0 and 1.0 based on clarity, specificity, and informativeness of the content.
- **source_url**: Include the original source URL provided.

### Output Requirements
- Respond **only** with a valid **minified JSON object**.
- Do **not** include:
  - Markdown
  - Triple quotes
  - Backticks
  - Comments
  - Any text before or after the JSON
- Escape internal quotes (e.g., `\"`) when necessary.
- MUST INCLUDE `category` field. If unsure, make your best-educated guess based on the `content` field.

Here is an example output where the category is "Funding":
{{
  "title": "TechCorp Announces $20M Series B Funding",
  "category": "Funding",
  "content": "TechCorp has secured $20 million in Series B funding to expand its AI-powered hiring platform. The round was led by Growth Capital Partners.",
  "confidence": 0.93,
  "source_url": "https://example.com/news/techcorp-funding"
}}

Here is an example output where the category is "Hiring":
{{
  "title": "TechCorp Expands Team with 50 New Hires",
  "category": "Hiring",
  "content": "TechCorp has announced plans to hire 50 new employees in its engineering department to support product development.",
  "confidence": 0.85,
  "source_url": "https://example.com/news/techcorp-hiring"
}}

Here is an example output where the category is "Leadership Changes":
{{
  "title": "TechCorp Appoints New CTO",
  "category": "Leadership Changes",
  "content": "TechCorp has appointed Jane Doe as its new CTO, effective immediately. Jane brings over 20 years of experience in the tech industry.",
  "confidence": 0.90,
  "source_url": "https://example.com/news/techcorp-new-ceo"
}}

Content:
{content}
"""
)


class InsightEnricher:
    def __init__(self, llm_model: Optional[ChatOpenAI] = None):
        self.llm = ChatOpenAI(model=llm_model, temperature=0.0)
        self.prompt = prompt_template
        self.enrichment_chain = self.prompt | self.llm

    def enrich(self, insights: InsightList) -> InsightList:
        enriched_insights = []

        for insight in insights.insights:
            # Determine whether enrichment is needed
            #needs_enrichment = not all([insight.category, insight.relevance])

            #if needs_enrichment:
                # Build prompt content with fallback to empty strings
            content_parts = [insight.content or "", insight.title or "", insight.source_url or ""]
            content = "\n".join(content_parts).strip()

            try:
                # Invoke the LLM
                response = self.enrichment_chain.invoke({"content": content})

                # Clean and parse the response
                raw_output = response.content if hasattr(response, "content") else response
                cleaned_json = clean_llm_json_output(raw_output)
                enriched_data = json.loads(cleaned_json)

                # Safely update only missing fields
                insight.title = insight.title
                insight.category = enriched_data.get("category", "Uncategorized")
                insight.content = insight.content
                try:
                    # Cast confidence to float with fallback
                    insight.confidence = insight.confidence or float(enriched_data.get("confidence", 0.0))
                except (ValueError, TypeError):
                    insight.confidence = insight.confidence or 0.0

                insight.source_url = insight.source_url or enriched_data.get("source_url", "")

            except Exception as e:
                logging.error(f"Failed to enrich insight with title '{insight.title}': {e}")

            enriched_insights.append(insight)

        return InsightList(enriched_insights)

    def enrich_doc(self, doc: dict) -> Optional[Insight]:
        c = doc.get("content", "")
        url = doc.get("url", "")

        try:
            response = self.enrichment_chain.invoke({"content": c})
            enriched_data = json.loads(clean_llm_json_output(response.content))

            return Insight(
                title=enriched_data.get("title", "Untitled Insight"),
                category=enriched_data.get("category", "Uncategorized"),
                content=enriched_data.get("content", ""),
                confidence=float(enriched_data.get("confidence", doc.get("score", 0.0))),
                source_url=enriched_data.get("source_url", url),
                company=doc.get("company", ""),
                location=doc.get("location", ""),
                industry=doc.get("industry", "")
            )
        except Exception as e:
            logging.warning(f"Failed to enrich doc: {e} — {doc.get('title', '')}")
            return None

    def enrich_docs(self, docs: List[dict]) -> InsightList:
        enriched = [
            self.enrich_doc(doc) for doc in docs
        ]
        valid_insights = [insight for insight in enriched if insight and insight.is_valid()]
        return InsightList(valid_insights)
    
def clean_llm_json_output(text: str) -> str:
    # Remove any non-JSON prefix/suffix
    json_start = text.find('{')
    json_end = text.rfind('}')
    if json_start != -1 and json_end != -1:
        text = text[json_start:json_end + 1]

    # Replace single quotes with double quotes
    text = text.replace("'", '"')

    # Replace None with null
    text = re.sub(r'\bNone\b', 'null', text)

    # Replace Python booleans with JSON booleans
    text = text.replace("True", "true").replace("False", "false")

    # Remove trailing commas
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    return text


