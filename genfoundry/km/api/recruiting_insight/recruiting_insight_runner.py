from flask_restful import Resource, current_app
from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from genfoundry import cache
import os
import logging


logger = logging.getLogger(__name__)

promptTemplate="""
You are a recruitment trends expert.

Given the content below, extract a short, engaging recruiting fact starting with "Did you know". 
Keep it under 50 words, and ensure it's factual and relevant to recruiters.

Content:
{article_content}

Insight:
"""


class RecruitingInsight(Resource):
    def __init__(self):
        os.environ["TAVILY_API_KEY"] = current_app.config.get("TAVILY_API_KEY")
        openai_api_key = current_app.config.get("OPENAI_API_KEY")
        #self.langchain_api_key = langchain_api_key
        llm_model = current_app.config.get("LLM_MODEL")
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0.3, api_key=openai_api_key)

    @jwt_required()
    def get(self):
        logger.debug("Fetching recruiting insight...")
        return self.get_recruiting_insight()
    
    def get_recruiting_insight(self):
        cached_insight = cache.get("daily_recruiting_insight")
        if cached_insight:
            logger.debug("Returning cached recruiting insight...")
            return jsonify({"insight": cached_insight})
        else:
            logger.debug("No cached insight found, fetching a new one...")
            # Check if the insight is already cached
            # If cached, return the cached insight
            # If not cached, fetch a new insight
            insight = self.fetch_recruiting_insight()
            if insight:
                cache.set("daily_recruiting_insight", insight)
                return jsonify({"insight": insight})
            else:
                return jsonify({"error": "Failed to fetch recruiting insight"}), 500
            
    def fetch_recruiting_insight(self):
        logger.debug("Using Tavily search to fetch insight...")
        try:
            # Step 1: Perform Tavily Search
            search_tool = TavilySearchResults()
            search_results = search_tool.run("latest recruitment trends in leveraging AI OR recruitment statistics about AI OR recruitment industry facts regarding impact of AI")

            # Combine top results
            combined_content = "\n\n".join([res["content"] for res in search_results[:3]])
            #logger.debug(f"Combined content: {combined_content}")

            # Step 2: Use Langchain to extract a “Did you know...” insight
            inputs = {
                "article_content": combined_content,
            }

            prompt = PromptTemplate.from_template(promptTemplate)
            chain = prompt| self.llm | StrOutputParser()
            response = chain.invoke(inputs)
            #logger.debug(f"LLM response: {response}")
            return response.strip()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    


    
