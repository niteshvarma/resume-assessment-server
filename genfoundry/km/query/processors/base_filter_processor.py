import json
import logging
from typing import Any, Dict, Optional
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from genfoundry.km.query.helper.filter_normalizer import FilterNormalizer
import os
from genfoundry.km.query.helper.llm_prompt_templates import filter_extractor_prompt

class BaseFilterProcessor:
    def __init__(self, llm: Optional[Any] = None):
        llm_model = os.getenv("LLM_MODEL")
        self.llm = llm or ChatOpenAI(model=llm_model, 
                                     openai_api_key = os.getenv("OPENAI_API_KEY"),
                                     temperature=0)

    def extract(self, question: str) -> Dict[str, Any]:
        logging.debug(f"[BaseFilterProcessor] Extracting filters from question: {question}")

        try:
            prompt_str = filter_extractor_prompt(question)
            result = self.llm.invoke(prompt_str)
            content = getattr(result, "content", str(result))
            logging.info(f"[BaseFilterProcessor] LLM response content: {content}")

            parsed_result = json.loads(content)
            logging.info(f"[BaseFilterProcessor] Parsed result: {parsed_result}")

            raw_filters = {}
            for f in parsed_result.get("filters", []):
                key = f.get("key")
                value = f.get("value")
                if key is None:
                    continue

                # Try to parse stringified JSON (like "[\"AWS\"]" or "{\"min\":10}")
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        value = parsed_value
                    except json.JSONDecodeError:
                        pass  # Leave as-is if not valid JSON

                raw_filters[key] = value

            return raw_filters

        except Exception as e:
            logging.error(f"[BaseFilterProcessor] Failed to extract filters: {e}")
            return {}
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        question = input_data.get("question")
        if not question:
            raise ValueError("[BaseFilterProcessor] Missing 'question' in input")

        filters = self.extract(question)
        return {
            **input_data,
            "filters": filters
        }