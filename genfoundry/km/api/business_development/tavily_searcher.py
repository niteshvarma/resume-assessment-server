from langchain_community.tools.tavily_search.tool import TavilySearchResults
#from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOpenAI
#from tavily import TavilyClient
from genfoundry.km.api.business_development.insight_enricher import InsightEnricher
from genfoundry.km.api.business_development.insight import Insight, InsightList
from typing import List, Optional
import logging
import json
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse
import asyncio
from tavily import AsyncTavilyClient
import os

logger = logging.getLogger(__name__)

        
class TavilySearcher:
    def __init__(self, llm_model: Optional[ChatOpenAI] = None):
        self.llm = ChatOpenAI(model=llm_model, temperature=0.3)

        self.company_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert business analyst. Review search results about a company and provide business development insights."),
            ("user", (
                "Company: {company_name}\n\n"
                "Top Result:\n{document}\n\n"
                "Return a JSON list of 1-3 insights. Each insight must have:\n"
                "- title: string (A short 5-10 word headline for the insight)\n"
                "- category: string (e.g. 'Funding', 'M&A', 'Leadership Change')\n"
                "- summary: string\n"
                "- confidence: float between 0 and 1 (e.g. 0.9)\n"
                "- source_url: string\n\n"
                "Only return a valid JSON list of dictionaries. Example:\n"
                "[\n"
                "  {{\n"
                "    \"title\": \"Company X raises new funding.\", \n"
                "    \"category\": \"Funding\", \n"
                "    \"summary\": \"Company X raised $200M in a Series F round.\", \n"
                "    \"confidence\": 0.92, \n"
                "    \"source_url\": \"{{https://example.com/article}}\"\n"
                "  }},\n"
                "  {{\n"
                "    \"title\": \"New CEO appointed at Company Y.\", \n"
                "    \"category\": \"Leadership Change\", \n"
                "    \"summary\": \"Company Y hired a new CEO with 20 years of experience in tech.\", \n"
                "    \"confidence\": 0.85, \n"
                "    \"source_url\": \"{{https://example.com/article2}}\"\n"
                "  }}\n"
                "]"
            )),
        ])

        self.location_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert business analyst. Review search results about companies in the given location and industry and provide business development insights."),
            ("user", (
                "Location: {location}\n\n"
                "Industry: {industry}\n\n"
                "Top Result:\n{document}\n\n"
                "Return a JSON list of 1-3 insights. Each insight must have:\n"
                "- Company: string (The name of the company about which the insight is about)\n"
                "- title: string (A short 5-10 word headline for the insight)\n"
                "- category: string (e.g. 'Funding', 'M&A', 'Leadership Change')\n"
                "- summary: string\n"
                "- confidence: float between 0 and 1 (e.g. 0.9)\n"
                "- source_url: string\n\n"
                "Only return a valid JSON list of dictionaries. Example:\n"
                "[\n"
                "  {{\n"
                "    \"location\": \"San Jose, CA\", \n"
                "    \"industry\": \"Technology\", \n"
                "    \"company\": \"Company X\", \n"
                "    \"title\": \"Company X raises new funding.\", \n"
                "    \"category\": \"Funding\", \n"
                "    \"summary\": \"Company X raised $200M in a Series F round.\", \n"
                "    \"confidence\": 0.92, \n"
                "    \"source_url\": \"{{https://example.com/article}}\"\n"
                "  }},\n"
                "  {{\n"
                "    \"location\": \"Reston, VA\", \n"
                "    \"industry\": \"Consulting\", \n"
                "    \"company\": \"Company Y \", \n"
                "    \"title\": \"New CEO appointed at Company Y.\", \n"
                "    \"category\": \"Leadership Change\", \n"
                "    \"summary\": \"Company Y hired a new CEO with 20 years of experience in tech.\", \n"
                "    \"confidence\": 0.85, \n"
                "    \"source_url\": \"{{https://example.com/article2}}\"\n"
                "  }}\n"
                "]"
            )),
        ])

        self.lucky_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert business analyst. Review search results about companies in the news today and provide business development insights."),
            ("user", (
                "Top Result:\n{document}\n\n"
                "Return a JSON list of 1-3 insights. Each insight must have:\n"
                "- Company: string (The name of the company about which the insight is about)\n"
                "- title: string (A short 5-10 word headline for the insight)\n"
                "- category: string (e.g. 'Funding', 'M&A', 'Leadership Change')\n"
                "- summary: string\n"
                "- confidence: float between 0 and 1 (e.g. 0.9)\n"
                "- source_url: string\n\n"
                "Only return a valid JSON list of dictionaries. Example:\n"
                "[\n"
                "  {{\n"
                "    \"company\": \"Company X\", \n"
                "    \"title\": \"Company X raises new funding.\", \n"
                "    \"category\": \"Funding\", \n"
                "    \"summary\": \"Company X raised $200M in a Series F round.\", \n"
                "    \"confidence\": 0.92, \n"
                "    \"source_url\": \"{{https://example.com/article}}\"\n"
                "  }},\n"
                "  {{\n"
                "    \"company\": \"Company Y\", \n"
                "    \"title\": \"New CEO appointed at Company Y.\", \n"
                "    \"category\": \"Leadership Change\", \n"
                "    \"summary\": \"Company Y hired a new CEO with 20 years of experience in tech.\", \n"
                "    \"confidence\": 0.85, \n"
                "    \"source_url\": \"{{https://example.com/article2}}\"\n"
                "  }}\n"
                "]"
            )),
        ])

        self.enricher = InsightEnricher(llm_model)
        self.search_tool = TavilySearchResults()
        self.tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        

    # def search_insights_by_company(self, company_name: str, since: Optional[str] = None) -> InsightList:
    #     since = since or datetime.today().strftime('%Y-%m-%d')
    #     chain = self.company_prompt | self.llm
    #     results = []

    #     query = (
    #         f"Find recent news about {company_name} related to: "
    #         "funding rounds (Series B, C, D, E), executive leadership changes (CEO, CTO), "
    #         "layoffs, hiring trends, job openings, spin-offs, strategic alliances, "
    #         "partnerships, mergers, acquisitions, investments, joint ventures, or collaborations."
    #     )
    #     tool_input = {"query": query}
    #     if since:
    #         time_range = self._parse_time_range(since)
    #         if time_range:
    #             tool_input["time_range"] = time_range

    #     docs = self.search_tool.run(tool_input)
    #     if not docs:
    #         logger.warning(f"No results found for company: {company_name}")
    #         return InsightList([])
    #     for doc in docs[:3]:
    #         try:
    #             title = doc.get('title', 'No title available')
    #             content = doc.get('content', 'No content available')
    #             url = doc.get('url', 'No URL available')

    #             logging.debug(f"Processing document: {title} - {content} ({url})")

    #             raw_output = chain.invoke({
    #                 "company_name": company_name,
    #                 "document": f"{title} - {content} ({url})"
    #             })

    #             logging.debug(f"Raw output from LLM: {raw_output}")

    #             cleaned_output = clean_llm_json_output(raw_output.content)
    #             raw_insights = json.loads(cleaned_output)
    #             sanitized_url_insights = sanitize_insights(raw_insights)
    #             for insight_data in sanitized_url_insights:
    #                 try:
    #                     insight = Insight(**insight_data)
    #                     results.append(insight)
    #                 except Exception as e:
    #                     logging.error(f"Invalid insight format: {e} - {insight_data}")
    #         except Exception as e:
    #             logging.error(f"Failed to process document: {e}")

    #     return InsightList(results)

    # def search_insights_by_company(self, company_name: str, since: Optional[str] = None) -> InsightList:
    #     since = since or datetime.today().strftime('%Y-%m-%d')
    #     results = []

    #     queries = [
    #         #f"Competitors of company {company_name}.",
    #         #f"Financial performance of company {company_name}.",
    #         f"Recent developments of company {company_name}.",
    #         #f"Latest industry trends related to {company_name}.",
    #         f"Executive leadership changes at {company_name} (CEO, CTO).",
    #         f"Funding rounds (Series B, C, D, E) involving {company_name}.",
    #         f"Layoffs at {company_name}.",
    #         f"Hiring trends at {company_name}.",
    #         f"Job openings at {company_name}.",
    #         #f"Strategic alliances and partnerships of {company_name}.",
    #         f"Mergers and acquisitions involving {company_name}.",
    #         #f"Investments and joint ventures of {company_name}."
    #     ]

    #     # Run the async batch search
    #     try:
    #         logger.info(f"Running batch search for: {queries}")
    #         raw_results = asyncio.run(self.batch_search(queries, time_range=since))
    #         logger.info(f"Batch search results: {raw_results}")        
    #     except Exception as e:
    #         logger.error(f"Unrecoverable error during batch search: {e}")
    #         return InsightList([])

    #     # Iterate over the search results and their corresponding queries
    #     for query, result in zip(queries, raw_results):
    #         if isinstance(result, Exception):
    #             logger.warning(f"Search failed for query: '{query}' — {result}")
    #             continue

    #         if not result:
    #             logger.warning(f"No results found for query: {query}")
    #             continue

    #         for doc in result[:3]:  # Process top 3 docs per query
    #             try:
    #                 title = doc.get("title", "No title available")
    #                 content = doc.get("content", "No content available")
    #                 url = doc.get("url", "No URL available")

    #                 logger.debug(f"Processing document: {title} - {content} ({url})")

    #                 raw_output = self.company_prompt | self.llm.invoke({
    #                     "company_name": company_name,
    #                     "document": f"{title} - {content} ({url})"
    #                 })

    #                 logger.debug(f"Raw output from LLM: {raw_output}")

    #                 cleaned_output = clean_llm_json_output(raw_output.content)
    #                 raw_insights = json.loads(cleaned_output)
    #                 sanitized_insights = sanitize_insights(raw_insights)

    #                 for insight_data in sanitized_insights:
    #                     try:
    #                         insight = Insight(**insight_data)
    #                         results.append(insight)
    #                     except Exception as e:
    #                         logger.error(f"Invalid insight format: {e} — {insight_data}")
    #             except Exception as e:
    #                 logger.error(f"Failed to process document: {e}")

    #     return InsightList(results)
    
    def search_insights_by_company(self, company_name: str, since: Optional[str] = None) -> InsightList:
        since = since or datetime.today().strftime('%Y-%m-%d')

        queries = [
            f"Executive leadership changes at {company_name} (CEO, CTO).",
            f"Funding rounds (Series B, C, D, E) involving {company_name}.",
            f"Layoffs at {company_name}.",
            f"Hiring Talent Acquisition teams at {company_name}.",
            f"Mergers and acquisitions involving {company_name}.",
            f"Investments and joint ventures of {company_name}."
        ]

        all_docs = []

        # Run async batch search
        try:
            logger.info(f"TavilySearcher: Running batch search for: {queries}")
            raw_results = asyncio.run(self.batch_search(queries, time_range=since))
            logger.info(f"TavilySearcher: Batch search results: {raw_results}")
        except Exception as e:
            logger.error(f"Unrecoverable error during batch search: {e}")
            return InsightList([])

        for query, result in zip(queries, raw_results):
            logger.debug(f"TavilySearcher: Processing query: {query}")
            if isinstance(result, Exception):
                logger.warning(f"Search failed for query: '{query}' — {result}")
                continue

            if not result:
                logger.warning(f"No results found for query: {query}")
                continue
            logger.debug(f"TavilySearcher: Found {len(result)} results for query: {query}")
            try:
                top_docs = result[:3]
                all_docs.extend(top_docs)  # Collect all documents
            except Exception as e:
                logger.error(f"Error processing top_docs for query '{query}': {e}\nResult: {result}", exc_info=True)
        logger.info(f"TavilySearcher: Total documents collected: {len(all_docs)}")
        try:
            logger.debug(f"TavilySearcher: Converting {len(all_docs)} docs to InsightList...")
            insight_list = InsightList.from_docs(all_docs)
            logger.debug(f"Initial InsightList: {insight_list}")

            logger.debug("TavilySearcher: Enriching insights via LLM...")
            enriched_insights = self.enricher.enrich(insight_list)
            logger.debug(f"TavilySearcher: Enriched insights: {enriched_insights}")
            return enriched_insights

        except Exception as e:
            logger.error(f"Failed during conversion or enrichment: {e}")
            return InsightList([])

    
    # def search_insights_by_location(self, location: str, industry: str, since: Optional[str] = None) -> InsightList:
    #     since = since or datetime.today().strftime('%Y-%m-%d')
    #     chain = self.location_prompt | self.llm
    #     results = []

    #     query = (
    #         f"In {location}, in the {industry} sector, find news about companies that have had: "
    #         f"new funding (Series B, C, D, E), executive changes (CEO/CTO), layoffs, hiring, "
    #         f"new job openings, spin-offs, strategic alliances, partnerships, mergers, acquisitions, "
    #         f"investments, joint ventures, or collaborations."
    #     )

    #     tool_input = {"query": query}
    #     time_range = self._parse_time_range(since)
    #     if time_range:
    #         tool_input["time_range"] = time_range

    #     docs = self.search_tool.run(tool_input)
    #     if not docs:
    #         logger.warning(f"No results found for location: {location}")
    #         return InsightList([])
    #     for doc in docs[:3]:
    #         try:
    #             title = doc.get('title', 'No title available')
    #             content = doc.get('content', 'No content available')
    #             url = doc.get('url', 'No URL available')

    #             logging.debug(f"Processing document: {title} - {content} ({url})")

    #             raw_output = chain.invoke({
    #                 "location": location,
    #                 "industry": industry,
    #                 "document": f"{title} - {content} ({url})"
    #             })

    #             logging.debug(f"Raw output from LLM: {raw_output}")
    #             cleaned_output = clean_llm_json_output(raw_output.content)
    #             raw_insights = json.loads(cleaned_output)
    #             sanitized_url_insights = sanitize_insights(raw_insights)
                
    #             for insight_data in sanitized_url_insights:
    #                 try:
    #                     logging.debug(f"Raw insight: {insight_data}")
    #                     insight = Insight(**insight_data)
    #                     logging.debug(f"Parsed insight URL: {insight.source_url}")
    #                     results.append(insight)
    #                 except Exception as e:
    #                     logging.error(f"Invalid insight format: {e} - {insight_data}")
    #         except Exception as e:
    #             logging.error(f"Failed to process document: {e}")

    #     return InsightList(results)

    def search_insights_by_location(self, location: str, industry: str, since: Optional[str] = None) -> InsightList:
        since = since or datetime.today().strftime('%Y-%m-%d')

        queries = [
            f"In {location}, in the {industry} sector: executive leadership changes (CEO, CTO).",
            f"In {location}, in the {industry} sector: funding rounds (Series B, C, D, E).",
            f"In {location}, in the {industry} sector: layoffs or hiring trends.",
            f"In {location}, in the {industry} sector: job openings.",
            f"In {location}, in the {industry} sector: mergers and acquisitions.",
            f"In {location}, in the {industry} sector: investments, joint ventures, or collaborations.",
            f"In {location}, in the {industry} sector: spin-offs or strategic partnerships.",
            f"In {location}, in the {industry} sector: hiring Talent Acquisition teams.",
        ]

        all_docs = []

        try:
            logger.info(f"TavilySearcher: Running batch search for: {queries}")
            raw_results = asyncio.run(self.batch_search(queries, time_range=since))
            logger.info(f"TavilySearcher: Batch search results: {raw_results}")
        except Exception as e:
            logger.error(f"Unrecoverable error during batch search: {e}")
            return InsightList([])

        for query, result in zip(queries, raw_results):
            logger.debug(f"TavilySearcher: Processing query: {query}")
            if isinstance(result, Exception):
                logger.warning(f"Search failed for query: '{query}' — {result}")
                continue

            if not result:
                logger.warning(f"No results found for query: {query}")
                continue

            try:
                top_docs = result[:3]
                all_docs.extend(top_docs)
            except Exception as e:
                logger.error(f"Error processing top_docs for query '{query}': {e}\nResult: {result}", exc_info=True)

        logger.info(f"TavilySearcher: Total documents collected: {len(all_docs)}")

        try:
            insight_list = InsightList.from_docs(all_docs)
            logger.debug("TavilySearcher: Enriching insights via LLM...")
            enriched_insights = self.enricher.enrich(insight_list)
            return enriched_insights
        except Exception as e:
            logger.error(f"Failed during conversion or enrichment: {e}")
            return InsightList([])

    
    # def feeling_lucky(self):
    #     chain = self.lucky_prompt | self.llm
    #     results = []

    #     query = (
    #         "Surprise me with recent company news involving major events like: "
    #         "funding rounds (Series B through E), executive changes (CEO, CTO), "
    #         "layoffs, hiring announcements, spin-offs, strategic partnerships, mergers, acquisitions, investments, or collaborations."
    #     )
    #     tool_input = {"query": query}
    #     since = datetime.today().strftime('%Y-%m-%d')
    #     time_range = self._parse_time_range(since)
    #     if time_range:
    #         tool_input["time_range"] = time_range

    #     docs = self.search_tool.run(tool_input)
    #     for doc in docs[:3]:
    #         try:
    #             title = doc.get('title', 'No title available')
    #             content = doc.get('content', 'No content available')
    #             url = doc.get('url', 'No URL available')

    #             logging.debug(f"Processing document: {title} - {content} ({url})")

    #             raw_output = chain.invoke({
    #                 "document": f"{title} - {content} ({url})"
    #             })

    #             logging.debug(f"Raw output from LLM: {raw_output}")

    #             cleaned_output = clean_llm_json_output(raw_output.content)
    #             raw_insights = json.loads(cleaned_output)
    #             sanitized_url_insights = sanitize_insights(raw_insights)

    #             for insight_data in sanitized_url_insights:
    #                 try:
    #                     insight = Insight(**insight_data)
    #                     results.append(insight)
    #                 except Exception as e:
    #                     logging.error(f"Invalid insight format: {e} - {insight_data}")
    #         except Exception as e:
    #             logging.error(f"Failed to process document: {e}")

    #     return InsightList(results)

    def feeling_lucky(self) -> InsightList:
        since = datetime.today().strftime('%Y-%m-%d')

        queries = [
            "Surprise me with recent company news involving funding rounds (Series B through E).",
            "Surprise me with executive changes (CEO, CTO) at notable companies.",
            "Surprise me with recent company layoffs.",
            "Surprise me with recent hiring announcements or job postings.",
            "Surprise me with spin-offs or new ventures.",
            "Surprise me with strategic partnerships, mergers, or acquisitions.",
            "Surprise me with investments or collaborations."
        ]

        all_docs = []

        try:
            logger.info("TavilySearcher: Running 'Feeling Lucky' batch search...")
            raw_results = asyncio.run(self.batch_search(queries, time_range=since))
            logger.info(f"TavilySearcher: Received 'Feeling Lucky' search results.")
        except Exception as e:
            logger.error(f"Unrecoverable error during 'Feeling Lucky' search: {e}")
            return InsightList([])

        for query, result in zip(queries, raw_results):
            logger.debug(f"Processing query: {query}")
            if isinstance(result, Exception):
                logger.warning(f"Search failed for query: '{query}' — {result}")
                continue

            if not result:
                logger.warning(f"No results found for query: {query}")
                continue

            try:
                top_docs = result[:3]
                all_docs.extend(top_docs)
            except Exception as e:
                logger.error(f"Error processing documents for query '{query}': {e}", exc_info=True)

        logger.info(f"TavilySearcher: Total documents collected: {len(all_docs)}")

        try:
            insight_list = InsightList.from_docs(all_docs)
            logger.debug("TavilySearcher: Enriching 'Feeling Lucky' insights via LLM...")
            enriched_insights = self.enricher.enrich(insight_list)
            return enriched_insights
        except Exception as e:
            logger.error(f"Failed during conversion or enrichment: {e}")
            return InsightList([])

    
    async def batch_search(self, queries, time_range=None):
        """
        Performs multiple search queries concurrently using asyncio.

        Args:
            queries (list): A list of search queries (strings).
            time_range (str): Optional time range for the search.
        Returns:
            list: A list of lists, where each inner list contains results for a query.
        """
        try:
            logger.info(f"Starting batch search: {queries}")
            raw_responses = await asyncio.gather(
                *(
                    self.tavily_client.search(
                        query=q,
                        # topic="news",
                        max_results=5,
                        time_range=time_range,
                    ) for q in queries
                ),
                return_exceptions=True
            )
            logger.info("Completed batch search")

            normalized_responses = []
            for i, res in enumerate(raw_responses):
                if isinstance(res, Exception):
                    logger.warning(f"Query {queries[i]} failed with error: {res}")
                    normalized_responses.append(res)
                elif isinstance(res, dict) and "results" in res:
                    normalized_responses.append(res["results"])
                else:
                    logger.warning(f"Query {queries[i]} returned unexpected format: {res}")
                    normalized_responses.append([])  # fallback to empty list

            return normalized_responses
        except Exception as e:
            logger.error(f"Error during batch search: {e}")
            return []

    def _parse_time_range(self, since: str) -> Optional[str]:
        try:
            since_date = datetime.strptime(since, "%Y-%m-%d")
            days_diff = (datetime.now() - since_date).days
            if days_diff <= 7:
                return "week"
            elif days_diff <= 30:
                return "month"
            elif days_diff <= 365:
                return "year"
            else:
                return None
        except Exception as e:
            logging.warning(f"Could not parse 'since' date: {e}")
            return None
        
    import json

def clean_llm_json_output(raw_output: str):
    # Remove Markdown code block syntax
    cleaned = re.sub(r'^(```json|json)?\s*', '', raw_output.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'```$', '', cleaned.strip())
    return cleaned
    
def sanitize_insights(raw_insights: list) -> list:
    """Validate and sanitize insights to ensure each has a valid source_url."""
    sanitized = []
    for entry in raw_insights:
        url = entry.get("source_url", "").strip()

        # Basic URL validation
        parsed = urlparse(url)
        is_valid_url = all([parsed.scheme in ("http", "https"), parsed.netloc])

        if not is_valid_url:
            print(f"Warning: Invalid or missing source_url in insight: '{entry.get('title', 'Untitled')}'")
            entry["source_url"] = "[no valid source]"

        sanitized.append(entry)

    return sanitized

def tavily_to_initial_insights(tavily_results: List[dict]) -> List[Insight]:
    insights = []
    for doc in tavily_results:
        try:
            insight = Insight(
                title=doc.get("title", "Untitled Insight"),
                category=doc.get("search_type", "Uncategorized"),
                summary=doc.get("content", "")[:500],  # Truncated to avoid overload
                confidence=float(doc.get("score", 0.0)),
                source_url=doc.get("url", "https://example.com")
            )
            if insight.is_valid():
                insights.append(insight)
        except Exception as e:
            logger.error(f"Error converting Tavily result: {e} — {doc}")
    return insights


    # queries = [
    #         #f"Competitors of company {company_name}.",
    #         #f"Financial performance of company {company_name}.",
    #         #f"Recent developments of company {company_name}.",
    #         #f"Latest industry trends related to {company_name}.",
    #         f"Executive leadership changes at {company_name} (CEO, CTO).",
    #         f"Funding rounds (Series B, C, D, E) involving {company_name}.",
    #         f"Layoffs at {company_name}.",
    #         #f"Hiring trends at {company_name}.",
    #         #f"Job openings at {company_name}.",
    #         f"Hiring Talent Acquisition teams at {company_name}.",
    #         #f"Strategic alliances and partnerships of {company_name}.",
    #         f"Mergers and acquisitions involving {company_name}.",
    #         f"Investments and joint ventures of {company_name}."
    #     ]
