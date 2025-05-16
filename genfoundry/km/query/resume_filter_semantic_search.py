import logging
import os
import re
import json
from typing import Optional, Dict, Any, List, Union

from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters, FilterOperator

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

#from genfoundry.km.query.helper.filter_normalizer import FilterNormalizer
#from genfoundry.km.query.helper.metadata_filter import MetadataFilter  
from genfoundry.km.query.helper.llm_prompt_templates import resume_search_prompt


class ResumeFilterSemanticSearcher:
    def __init__(self, similarity_cutoff: float = 0.75):
        logging.debug("Initializing ResumeFilterSemanticSearcher with OpenAI and Pinecone settings.")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX")
        self.llm_model = os.getenv("LLM_MODEL")
        self.resume_details_popup_url = os.getenv("RESUME_DETAILS_POPUP_URL")
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        self.similarity_cutoff = similarity_cutoff

    def search(self, tenant_id: str, question: str, filter_dict: Dict[str, Any]):
        logging.debug(f"Running filtered search for tenant: {tenant_id}")
        logging.debug(f"Filters passed to search(): {filter_dict}")
        try:
            vector_index = self._init_vector_index(tenant_id)

            metadata_filters = self._build_metadata_filters(filter_dict)

            retriever = self._create_retriever(vector_index, metadata_filters)

            # Check if retriever returned any documents
            sample_docs = retriever.retrieve(question)
            if not sample_docs:
                logging.info("No documents retrieved for question – skipping LLM call.")
                return {
                    "result": [],
                    "message": "No matching resumes found for the given filters."
                }

            query_engine = self._build_query_engine(retriever)

            llm_question = self._format_llm_query(question)
            result = query_engine.query(llm_question)

            # Debugging the raw LLM response
            try:
                logging.debug("🔍 Raw LLM Response:\n%s", json.dumps(result.response, indent=2))
            except Exception:
                logging.debug("🔍 Raw LLM Response (non-JSON): %s", result.response)
            
            raw_response = str(result.response) if hasattr(result, "response") else str(result)
            sanitized_response = self._sanitize_llm_response(raw_response)
            # sanitized_response = self._sanitize_llm_response(result.response)
            if sanitized_response is None:
                logging.warning("Sanitized response is None — returning default or error.")
                return {"error": "Unable to parse LLM response"}
            
            logging.debug("🔍 Sanitized LLM Response:\n%s", json.dumps(sanitized_response, indent=2))
            return sanitized_response
            #return self._format_response(sanitized_response)
        except Exception as ex:
            logging.error(f"Error in filtered search: {str(ex)}")
            raise

    def _init_vector_index(self, tenant_id: str):
        pinecone_namespace = f"{tenant_id}_Resumes_NS"
        logging.debug(f"Initializing vector index for namespace: {pinecone_namespace}")
        vector_store = PineconeVectorStore(
            index_name=self.pinecone_index,
            api_key=self.pinecone_api_key,
            namespace=pinecone_namespace
        )
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)

    """     
    def _build_metadata_filters(self, filters: dict) -> MetadataFilters:
        try:
            if not filters:
                return None

            filter_objects: List[MetadataFilter] = []
            passthrough_filters = {}

            for key, value in filters.items():
                # Handle range filters like {'min': 3, 'max': 7}
                if isinstance(value, dict) and 'min' in value and 'max' in value:
                    filter_objects.append(MetadataFilter(key=key, value=value['min'], operator=FilterOperator.GTE))
                    filter_objects.append(MetadataFilter(key=key, value=value['max'], operator=FilterOperator.LTE))

                # Pass all others to from_dict (string, list, int, etc.)
                else:
                    passthrough_filters[key] = value

            # Add passthrough filters using from_dict
            if passthrough_filters:
                metadata_filters = MetadataFilters.from_dict(passthrough_filters)
                if metadata_filters and metadata_filters.filters:
                    filter_objects.extend(metadata_filters.filters)

            return MetadataFilters(filters=filter_objects) if filter_objects else None

        except Exception as e:
            logging.error(f"Error building metadata filters from dict: {e}")
            return None
    """

    def _build_metadata_filters(self, filters: Union[dict, list]) -> Optional[MetadataFilters]:
        def inject_range_operator(filters: list) -> list:
            count = 0
            for f in filters:
                value = f.get("value")
                if isinstance(value, dict) and ("min" in value or "max" in value):
                    f["operator"] = "range"
                    count += 1
            logging.debug(f"Injected 'range' operator into {count} filters")
            return filters
        try:
            if not filters:
                return None

            filter_objects: List[MetadataFilter] = []

            if isinstance(filters, list):
                filters = inject_range_operator(filters)
                for f in filters:
                    key = f.get("key") or f.get("name")
                    value = f.get("value")
                    operator_str = f.get("operator", "==")
                    must_have = f.get("must_have", False)

                    if not key or value is None:
                        logging.warning(f"Skipping filter with missing key or value: {f}")
                        continue

                    # Try parsing JSON value if it’s a stringified dict or list
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except Exception:
                            pass  # Just keep original string if not JSON

                    # Operator mapping
                    if isinstance(value, list):
                        operator = FilterOperator.IN
                    else:
                        operator = {
                            "==": FilterOperator.EQ,
                            "eq": FilterOperator.EQ,
                            "!=": FilterOperator.NE,
                            "contains": FilterOperator.CONTAINS,
                            "range": None,  # Special case
                        }.get(operator_str.lower(), FilterOperator.EQ)

                    # Handle range filters
                    if operator is None and isinstance(value, dict):
                        min_val = value.get("min")
                        max_val = value.get("max")

                        if min_val is not None:
                            logging.debug(f"[Range] Adding GTE filter: key={key}, value={min_val}")
                            filter_objects.append(MetadataFilter(key=key, value=min_val, operator=FilterOperator.GTE))
                        if max_val is not None:
                            logging.debug(f"[Range] Adding LTE filter: key={key}, value={max_val}")
                            filter_objects.append(MetadataFilter(key=key, value=max_val, operator=FilterOperator.LTE))

                        continue  # Important! Skip direct append below

                    # Skip dict-type values that aren't valid range filters
                    if isinstance(value, dict):
                        logging.warning(f"Skipping invalid dict value for key={key}: {value}")
                        continue

                    try:
                        logging.debug(f"Appending filter: key={key}, value={value} ({type(value)}), operator={operator}")
                        filter_objects.append(MetadataFilter(key=key, value=value, operator=operator))
                    except Exception as e:
                        logging.error(f"Error constructing MetadataFilter for key={key}, value={value}, operator={operator}: {e}")

            elif isinstance(filters, dict):
                passthrough_filters = {}
                for key, value in filters.items():
                    if isinstance(value, dict) and 'min' in value and 'max' in value:
                        logging.debug(f"[Legacy Range] key={key}, min={value['min']}, max={value['max']}")
                        filter_objects.append(MetadataFilter(key=key, value=value['min'], operator=FilterOperator.GTE))
                        filter_objects.append(MetadataFilter(key=key, value=value['max'], operator=FilterOperator.LTE))
                    else:
                        passthrough_filters[key] = value

                if passthrough_filters:
                    metadata_filters = MetadataFilters.from_dict(passthrough_filters)
                    if metadata_filters and metadata_filters.filters:
                        filter_objects.extend(metadata_filters.filters)

            if filter_objects:
                for f in filter_objects:
                    try:
                        dumped = f.model_dump()
                        json.dumps(dumped)  # test serializability
                    except TypeError as e:
                        logging.error(f"Filter not serializable: {f} – Error: {e}")
            return MetadataFilters(filters=filter_objects) if filter_objects else None

        except Exception as e:
            logging.exception("Error building metadata filters from dict.")
            return None


    def _create_retriever(self, vector_index, filters: Optional[MetadataFilters]):
        return VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=10,
            filters=filters
        )

    def _build_query_engine(self, retriever):
        return RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=get_response_synthesizer(),
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=self.similarity_cutoff)]
        )

    def _format_llm_query(self, question: str) -> str:
        return resume_search_prompt(question, self.resume_details_popup_url)

    def _format_response(self, response_text: str) -> str:
        try:
            # Check if response_text is already a dict (or list)
            if isinstance(response_text, dict):
                response_dict = response_text
            elif isinstance(response_text, str):
                # Parse the raw JSON response if it's a string
                response_dict = json.loads(response_text)
            else:
                raise ValueError("Unexpected response format")
            
            # Extract the candidates list from the parsed JSON
            candidates = response_dict.get("candidates", [])
            
            # If no candidates found, return a clear message
            if not candidates:
                return "No relevant candidates found."

            # Format the candidates into a response string
            formatted = []
            for idx, c in enumerate(candidates, 1):
                # Prepare the URL with the resume ID
                resume_id = c.get("resume_id", "")
                url = f"{self.resume_details_popup_url}?ID={resume_id}"
                
                # Format each candidate's information
                parts = [
                    f"**{idx}. [ {c.get('name', 'Unknown')} ]({url})**",  # Hyperlinked name
                    f"- **Job Title**: {c.get('job_title', 'N/A')}",  # Job Title
                    f"- **Years of Experience**: {c.get('years_of_experience', 'N/A')}",  # Years of Experience
                    f"- **Location**: {c.get('location', 'N/A')}",  # Location
                    f"- **Key Technical Skills**: {', '.join(c.get('technical_skills', []))}",  # Technical Skills
                    f"- **Key Leadership Skills**: {', '.join(c.get('leadership_skills', []))}"  # Leadership Skills
                ]
                
                # Add the formatted string for the current candidate
                formatted.append('\n'.join(parts))
            
            # Join all formatted candidate responses with double newlines
            return '\n\n'.join(formatted)

        except json.JSONDecodeError:
            return "⚠️ Error: LLM returned invalid JSON. Please try again."

        except Exception as e:
            return f"⚠️ Unexpected error: {str(e)}"
        
    def _sanitize_llm_response(self, raw_response: str) -> dict | None:
        if not isinstance(raw_response, str):
            logging.warning("LLM response is not a string: %s", type(raw_response))
            return None

        try:
            # Step 1: Try loading directly (best case)
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass  # Fall back to unescape logic

        try:
            # Step 2: Strip double quotes if wrapped
            if raw_response.startswith('"') and raw_response.endswith('"'):
                raw_response = raw_response[1:-1]

            # Step 3: Unescape characters
            unescaped = raw_response.encode('utf-8').decode('unicode_escape')

            # Step 4: Try parsing again
            return json.loads(unescaped)
        except Exception as e:
            logging.exception("Failed to sanitize and parse LLM response")
            return None
            
    """     
    def _sanitize_llm_response(self, raw_response: str) -> dict | None:
        if isinstance(raw_response, str):
            try:
                # Step 1: Unwrap if it's doubly quoted (e.g., entire response is a string)
                if raw_response.startswith('"') and raw_response.endswith('"'):
                    raw_response = raw_response[1:-1]

                # Step 2: Unescape characters
                unescaped = raw_response.encode('utf-8').decode('unicode_escape')

                # Step 3: Try parsing the JSON
                parsed = json.loads(unescaped)
                return parsed
            except Exception as e:
                logging.exception("Failed to sanitize and parse LLM response")
                return None
        else:
            logging.warning("LLM response is not a string, returning as is.")
            return raw_response
 """
