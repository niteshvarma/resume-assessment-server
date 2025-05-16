from langchain_openai import ChatOpenAI
import json
import os
import logging
import re
from typing import Any, Optional, Dict, List
from genfoundry.km.query.helper.llm_prompt_templates import geo_location_expansion_prompt


class GeoExpansionProcessor:
    def __init__(self, llm: Optional[Any] = None):
        llm_model = os.getenv("LLM_MODEL", "gpt-4-1106-preview")
        
        self.llm = llm or ChatOpenAI(model=llm_model, 
                                     openai_api_key = os.getenv("OPENAI_API_KEY"),
                                     temperature=0)

    def expand_location(self, location: str) -> List[str]:
        try:
            prompt_str = geo_location_expansion_prompt(location)
            result = self.llm.invoke(prompt_str)

            response_text = result.content.strip()

            # Defensive coding: Remove any markdown formatting like ```json
            response_text = re.sub(r"^```json\n|```$", "", response_text)

            # Defensive: Remove any other markdown/extra text before or after the JSON, if needed
            response_text = re.sub(r"^.*\{", "{", response_text)  # Remove any text before the JSON starts
            response_text = re.sub(r"\}.*$", "}", response_text)  # Remove any text after the JSON ends

            # Try parsing the cleaned response as JSON
            response_json = json.loads(response_text)
            expanded_locations = response_json.get("expanded_locations", [])
            logging.debug(f"[GeoExpansionProcessor] Expanded location filter: {expanded_locations}")
            return expanded_locations
        except Exception as e:
            logging.error(f"[GeoExpansionProcessor] Failed to expand location: {e}")
            return []

    def process(self, data: dict) -> dict:
        filters = data.get("filters", {})

        # Defensive: ensure filters is a dict, not list
        if isinstance(filters, list):
            # Convert to dict for easier handling
            filters_dict = {}
            for f in filters:
                filters_dict[f["key"]] = f["value"]
            filters = filters_dict

        location_value = filters.get("location")
        if not location_value:
            logging.debug("[GeoExpansionProcessor] No location filter to expand")
            return data

        # 💡 Normalize location_value in case it's a stringified list
        if isinstance(location_value, str):
            try:
                location_value = json.loads(location_value)
            except json.JSONDecodeError:
                pass  # leave as-is if not parseable

        # Flatten single value into list
        if not isinstance(location_value, list):
            location_value = [location_value]

        # Run expansion on the first (or only) value
        expanded = self.expand_location(location_value[0]) if location_value else []

        filters["location"] = expanded if expanded else location_value
        data["filters"] = filters
        return data
