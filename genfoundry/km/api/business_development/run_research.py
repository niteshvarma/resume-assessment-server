from flask_restful import Resource, current_app
from flask import Flask, request
from flask_jwt_extended import jwt_required
# from langchain_community.tools.tavily_search.tool import TavilySearchResults
# from langchain.output_parsers import PydanticOutputParser
# from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, field_validator, ValidationError
from typing import Union, List, Optional
import os
import logging

from genfoundry.km.api.business_development.tavily_searcher import TavilySearcher
from genfoundry.km.api.business_development.insight import Insight, InsightList

logger = logging.getLogger(__name__)

"""
This module defines a Flask-based REST API service that performs automated business research
on companies using Tavily search results and a language model (LLM).

Core components:
- Insight and InsightList classes: Data models for structured insights.
- TavilySearcher: Executes search queries and prompts the LLM to extract insights from top results.
- InsightEnricher: Optionally enriches incomplete insights using the LLM.
- RunResearch (Flask Resource): HTTP POST endpoint at /research for retrieving enriched insights
  based on a company name (and optional 'since' filter).

External dependencies:
- langchain (ChatOpenAI, ChatPromptTemplate, TavilySearchResults)
- Flask, Flask-RESTful
"""
class RunResearch(Resource):
    def __init__(self):
        os.environ["TAVILY_API_KEY"] = current_app.config.get("TAVILY_API_KEY")
        os.environ["OPENAI_API_KEY"] = current_app.config.get("OPENAI_API_KEY")
        llm_model = current_app.config.get("LLM_MODEL")
        #self.enricher = InsightEnricher(llm_model)
        self.searcher = TavilySearcher(llm_model)

    # def post(self):
    #     try:
    #         payload = request.get_json()
    #         company = payload.get("company")
    #         if not company:
    #             return {"error": "Missing 'company' parameter"}, 400

    #         insights = self.searcher.search_insights(company)
    #         enriched = self.enricher.enrich(insights)

    #         return {"insights": enriched.to_list()}, 200
    #     except Exception as e:
    #         return {"error": str(e)}, 500
    
    @jwt_required()
    def post(self):
        try:
            payload = request.get_json()
            mode = payload.get("mode", "company")  # default to company mode
            since = payload.get("since")  # may be None

            if mode == "company":
                company = payload.get("company")
                if not company:
                    return {"error": "Missing 'company' parameter"}, 400

                insights = self.searcher.search_insights_by_company(company, since)

            elif mode == "location":
                location = payload.get("location")
                industry = payload.get("industry")
                if not location or not industry:
                    return {"error": "Missing 'location' or 'industry' parameter"}, 400

                insights = self.searcher.search_insights_by_location(location, industry, since)

            elif mode == "lucky":
                insights = self.searcher.feeling_lucky()

            else:
                return {"error": f"Invalid mode: {mode}"}, 400

            #enriched = self.enricher.enrich(insights)
            return {"insights": insights.to_list()}, 200

        except Exception as e:
            return {"error": str(e)}, 500

    
# def parse_insights(raw_response):
#     logger = logging.getLogger(__name__)

#     try:
#         insights_data = json.loads(raw_response)
#         logger.debug(f"Parsed insights data: {insights_data}")

#         validated = InsightList(insights=insights_data)
#         return validated.dict()
#     except Exception as e:
#         logger.error(f"Initial validation failed: {e}")
#         try:
#             partial_results = []
#             for item in insights_data:
#                 # Ensure that all required fields exist before processing
#                 if 'title' not in item or 'category' not in item or 'summary' not in item or 'confidence' not in item or 'source_url' not in item:
#                     logger.error(f"Missing required fields in insight item: {item}")
#                     continue  # Skip this item if it's missing required fields

#                 try:
#                     insight = Insight(**item)
#                     partial_results.append(insight.dict())
#                 except ValidationError as inner_e:
#                     logger.error(f"Validation error for insight item: {inner_e}")
#                 except Exception as inner_e:
#                     logger.error(f"Error parsing individual insight: {inner_e}")

#             return {"insights": partial_results}
#         except Exception as final_fail:
#             logger.error(f"Final error handling failed: {final_fail}")
#             return {"insights": []}



    #@jwt_required()  # Ensure the user is authenticated via JWT token
    # def post(self):
    #     # Step 1: Parse incoming data
    #     parser = reqparse.RequestParser()
    #     parser.add_argument("company_name", required=True)
    #     args = parser.parse_args()
    #     company_name = args["company_name"]

    #     # Step 2: Search using Tavily API
    #     search_tool = TavilySearchResults()
    #     docs = search_tool.run(f"{company_name} funding OR CEO OR executive change OR merger OR acquisition")

    #     logger.debug(f"Tavily search results: {docs}")

    #     if not docs:
    #         return {"error": "No results found from Tavily for this company."}, 404

    #     # Step 3: Setup LangChain components
    #     prompt = ChatPromptTemplate.from_messages([
    #         ("system", "You are an expert business analyst. Review search results about a company and provide business development insights."),
    #         ("user", (
    #             "Company: {company_name}\n\n"
    #             "Top Result:\n{document}\n\n"
    #             "Return a JSON list of 1-3 insights. Each insight must have:\n"
    #             "- category: string (e.g. 'Funding', 'M&A', 'Leadership Change')\n"
    #             "- summary: string\n"
    #             "- confidence: float between 0 and 1 (e.g. 0.9)\n"
    #             "- source_url: string\n\n"
    #             "Only return a valid JSON list of dictionaries. Example:\n"
    #             "[\n"
    #             "  {{\n"
    #             "    \"category\": \"Funding\", \n"
    #             "    \"summary\": \"Company X raised $200M in a Series F round.\", \n"
    #             "    \"confidence\": 0.92, \n"
    #             "    \"source_url\": \"https://example.com/article\"\n"
    #             "  }},\n"
    #             "  {{\n"
    #             "    \"category\": \"Leadership Change\", \n"
    #             "    \"summary\": \"Company Y hired a new CEO with 20 years of experience in tech.\", \n"
    #             "    \"confidence\": 0.85, \n"
    #             "    \"source_url\": \"https://example.com/article2\"\n"
    #             "  }}\n"
    #             "]"
    #         )),
    #     ])

    #     model = ChatOpenAI(model=self.llm_model, temperature=0.3)
    #     parser = PydanticOutputParser(pydantic_object=InsightList)
    #     chain = prompt | model | parser

        # results = []

        # for doc in docs[:3]:
        #     try:
        #         title = doc.get('title', 'No title available')
        #         content = doc.get('content', 'No content available')
        #         url = doc.get('url', 'No URL available')

        #         logger.debug(f"Processing document: {title} - {content} ({url})")

        #         # Run the chain
        #         raw_output = chain.invoke({
        #             "company_name": company_name,
        #             "document": f"{title} - {content} ({url})"
        #         })

        #         logger.debug(f"Raw output from LLM: {raw_output}")

        #         # Step 4: Use the updated parse_llm_output_to_insight function to parse raw output
        #         parsed_insights = parse_llm_output_to_insight(raw_output)

        #         if isinstance(parsed_insights, dict) and 'error' in parsed_insights:
        #             results.append(parsed_insights)
        #         else:
        #             # Extract insights from the parsed output
        #             insights = parsed_insights.insights if isinstance(parsed_insights, InsightList) else [parsed_insights]
        #             results.extend([insight.dict() for insight in insights])

    #         except Exception as e:
    #             logger.error(f"Error parsing insight for document: {str(e)}")
    #             results.append({"error": f"Failed to parse Insight: {str(e)}"})

    #     return {"company_name": company_name, "insights": results}