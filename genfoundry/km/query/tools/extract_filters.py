from langchain.tools import BaseTool
from genfoundry.km.query.helper.filter_normalizer import FilterNormalizer
from typing import Type
from pydantic import BaseModel, Field, Literal

from typing import Any, Dict

from genfoundry.km.query.helper.filter_extractor import FilterExtractor

from pydantic import BaseModel

class ExtractFiltersInput(BaseModel):
    question: str

class ExtractFiltersTool(BaseTool):
    name: str = Field(default="extract_filters_from_query")
    description: str = (
        "Extracts structured filters such as role, location, and years of experience "
        "from a user's query. Adjusts years of experience into a flexible range."
    )
    args_schema: Type[BaseModel] = ExtractFiltersInput

    def __init__(self, llm=None, **kwargs):
        super().__init__(**kwargs)
        self.extractor = FilterExtractor(llm)

    def invoke(self, question: str) -> Dict[str, Any]:
        return self.extractor.extract(question)

    def _run(self, *args, **kwargs):
        raise NotImplementedError("The _run method is not implemented for this tool.")

    async def _arun(self, question: str):
        raise NotImplementedError("Async not supported for this tool.")
