from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.chat_models import ChatOpenAI
from langchain_core.runnables.base import RunnableSequence  # Corrected import
from genfoundry.km.query.tools.utils import FilterNormalizer
from typing import Type
from pydantic import BaseModel, Field
import os
import json
import logging
from typing import Any, Dict, Optional

class ExtractFiltersInput(BaseModel):
    question: str


class ExtractFiltersTool(BaseTool):
    llm: Optional[Any] = None
    prompt: Optional[PromptTemplate] = None
    chain: Optional[RunnableSequence] = None  # Using RunnableSequence instead of LLMChain

    name = "extract_filters_from_query"
    description = (
        "Extracts structured filters such as role, location, and years of experience "
        "from a user's query. Adjusts years of experience into a flexible range."
    )
    args_schema: Type[BaseModel] = ExtractFiltersInput

    def __init__(self, llm=None, **kwargs):
        super().__init__(**kwargs)
        llm_model = os.getenv("LLM_MODEL")
        if self.llm is None:
            self.llm = llm or ChatOpenAI(model=llm_model, temperature=0)

        self.prompt = PromptTemplate(
            input_variables=["question"],
            template="""
You are a resume search assistant. From the user query, extract a list of filters in JSON format.

Rules:
- Include keys like "role", "location", "years_of_experience".
- For "years_of_experience", convert a specific number into a RANGE:
    - If 2 → use 1 to 4
    - If 5 → use 3 to 7
    - If 10 → use 7 to 12
    - If 15 → use 12 to 18
    - If 20 → use 15 to 25
    - Always return "operator": "range" and a dict with "min" and "max" values
- Only return valid filters found in the query.
- Return a JSON object with a top-level `filters` key.

Format:
{{
  "filters": [
    {{"key": "role", "value": "Senior Data Scientist", "operator": "=="}},
    {{
      "key": "years_of_experience",
      "value": {{"min": 7, "max": 12}},
      "operator": "range"
    }},
    {{"key": "location", "value": "New York", "operator": "=="}}
  ]
}}

Now process this query:
Query: {question}
"""
        )
        
        # Using RunnableSequence for chaining the prompt and LLM invocation
        self.chain = RunnableSequence(self.prompt, self.llm)

    def invoke(self, question: str) -> Dict[str, Any]:
        """Invoke the tool to extract filters from the user's query."""
        try:
            # Format the prompt with the question
            prompt_input = self.prompt.format(question=question)

            # Run the prompt through the LLM to get the response
            result = self.llm.invoke(prompt_input)  # This should call the LLM's invoke method
            
            # Log the raw result before parsing
            logging.debug(f"Raw result from LLM: {result}")

            # Parse the result into a dictionary (assuming the response is in JSON format)
            parsed_result = json.loads(result)

            # Log the parsed result
            logging.debug(f"Parsed result: {parsed_result}")

            # Extract filters from the parsed result
            raw_filters = {
                f["key"]: f["value"]
                for f in parsed_result.get("filters", [])
                if "key" in f and "value" in f
            }

            # Normalize and return the extracted filters
            return FilterNormalizer.normalize(raw_filters)

        except Exception as e:
            logging.error(f"Error in ExtractFiltersTool invoke: {str(e)}")
            return {}
        
    def _run(self, *args, **kwargs):
        """Placeholder to fulfill the BaseTool abstract class #requirement."""
        raise NotImplementedError("The _run method is not implemented for this tool.")
    
    async def _arun(self, question: str):
        """Optional async version of invoke (if you plan to handle async tasks)."""
        raise NotImplementedError("Async not supported for this tool.")
