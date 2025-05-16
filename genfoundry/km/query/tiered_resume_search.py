import logging
import os
import re
import json
from typing import Optional, Dict, Any, List, Union
from fuzzywuzzy import fuzz

from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters, FilterOperator

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

from genfoundry.km.query.helper.filter_normalizer import FilterNormalizer
#from genfoundry.km.query.helper.metadata_filter import MetadataFilter  
from genfoundry.km.query.helper.llm_prompt_templates import resume_search_prompt


class TieredResumeSearcher:
    def __init__(self, similarity_cutoff: float = 0.5):
        logging.debug("Initializing TieredResumeSearch with OpenAI and Pinecone settings.")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX")
        self.llm_model = os.getenv("LLM_MODEL")
        self.resume_details_popup_url = os.getenv("RESUME_DETAILS_POPUP_URL")
        #os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        self.similarity_cutoff = similarity_cutoff
        #self.strict_filter_fields = ['location', 'years_of_experience', 'career_domain']
        self.strict_filter_fields = ['location', 'career_domain']

    """
    def search(self, tenant_id: str, question: str, filter_dict: Dict[str, Any]):
        logging.debug(f"Running tiered search for tenant: {tenant_id}")
        try:
            vector_index = self._init_vector_index(tenant_id)

            # Step 1: Split filters
            strict_filters, soft_filters = self._split_filter_dict(filter_dict)

            # Step 2: Build metadata filters (strict only)
            metadata_filters = self._build_metadata_filters(strict_filters)

            # Step 3: Tier 1 - Strict + Semantic
            logging.info("Tier 1: Trying strict filters with semantic search")
            retriever = self._create_retriever(vector_index, metadata_filters)
            query_engine = self._build_query_engine(retriever)
            llm_question = self._format_llm_query(question)
            result = query_engine.query(llm_question)
            top_documents = result.source_nodes

            # Tier 1 success
            if top_documents:
                logging.info("Tier 1 succeeded")
                scored_resumes = self._score_soft_filters(top_documents, soft_filters)
                top_n = sorted(scored_resumes, key=lambda x: x["score"], reverse=True)[:20]
                return {"matches": top_n, "tier": "Tier 1"}

            # Tier 2 - Semantic only, score with soft filters
            logging.info("Tier 1 failed, falling back to Tier 2: No strict filters")
            retriever = self._create_retriever(vector_index, metadata_filters=None)
            query_engine = self._build_query_engine(retriever)
            result = query_engine.query(llm_question)
            top_documents = result.source_nodes

            if top_documents:
                logging.info("Tier 2 succeeded")
                scored_resumes = self._score_soft_filters(top_documents, soft_filters)
                top_n = sorted(scored_resumes, key=lambda x: x["score"], reverse=True)[:20]

                # Log the top scored candidates (only ID + score to avoid PII/noise)
                for i, candidate in enumerate(top_n[:5], start=1):  # top 5 for brevity
                    logging.info(f"Top candidate {i}: ID={candidate['resume_id']}, Score={candidate['score']}")

                return {"matches": top_n, "tier": "Tier 2"}

            # Tier 3 - Pure semantic fallback
            logging.info("Tier 2 failed, falling back to Tier 3: Unfiltered semantic search")
            retriever = self._create_retriever(vector_index)
            query_engine = self._build_query_engine(retriever)
            result = query_engine.query(llm_question)
            top_documents = result.source_nodes

            if top_documents:
                logging.info("Tier 3 succeeded")
                scored_resumes = self._score_soft_filters(top_documents, soft_filters)
                top_n = sorted(scored_resumes, key=lambda x: x["score"], reverse=True)[:20]
                return {"matches": top_n, "tier": "Tier 3"}

            # Nothing matched
            logging.warning("All tiers failed: No results")
            return {"matches": [], "message": "No results found", "tier": "None"}

        except Exception as ex:
            logging.error(f"Error in filtered search: {str(ex)}")
            raise
    """

    def search(self, tenant_id: str, question: str, filter_dict: Dict[str, Any]):
        logging.debug(f"Running tiered search for tenant: {tenant_id}")
        logging.debug("Filters provided in search(): %s", filter_dict)
        try:
            vector_index = self._init_vector_index(tenant_id)

            # Step 1: Split filters
            strict_filters, soft_filters = self._split_filter_dict(filter_dict)

            # Step 2: Build metadata filters (strict only)
            normalized_filters = FilterNormalizer.normalize(strict_filters)
            logging.debug("Normalized filters: %s", normalized_filters)
            metadata_filters = self._build_metadata_filters(normalized_filters)
            logging.debug("Metadata filters: %s", metadata_filters)
            # Step 3: Tiered Search Logic
            for tier_name, filters in [
                ("Tier 1", metadata_filters),
                ("Tier 2", None),
                ("Tier 3", None)  # Tier 3 is fallback; semantic only
            ]:
                logging.info(f"{tier_name}: {'Using strict filters' if filters else 'Unfiltered semantic search'}")
                retriever = self._create_retriever(vector_index, filters)
                query_engine = self._build_query_engine(retriever)
                llm_question = self._format_llm_query(question)
                result = query_engine.query(llm_question)
                top_documents = result.source_nodes

                if top_documents:
                    logging.info(f"{tier_name} succeeded")

                    # ✅ Deduplicate by resume_id / doc_id and keep best score per resume
                    resume_map = {}
                    for doc in top_documents:
                        doc_id = doc.metadata.get("doc_id")
                        if doc_id not in resume_map or doc.score > resume_map[doc_id]["score"]:
                            resume_map[doc_id] = {
                                "resume_id": doc_id,
                                "resume_text": doc.text,
                                "metadata": doc.metadata,
                                "score": doc.score or 0
                            }

                    # ✅ Score soft filters on top of best matches
                    logging.debug(f"Soft filters before scoring: {json.dumps(soft_filters, indent=2)}")
                    scored_resumes = self._score_soft_filters(list(resume_map.values()), soft_filters, use_fuzzy=True)

                    # ✅ Top N (avoid ties messing up sort)
                    top_n = sorted(scored_resumes, key=lambda x: x["score"], reverse=True)[:20]

                    # Logging top 5 resume_ids for traceability
                    for i, candidate in enumerate(top_n[:5], start=1):
                        logging.info(f"Top candidate {i}: ID={candidate['resume_id']}, Score={candidate['score']}")

                    return {"matches": top_n, "tier": tier_name}

            # All Tiers failed
            logging.warning("All tiers failed: No results")
            return {"matches": [], "message": "No results found", "tier": "None"}

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
                    operator_str = f.get("operator", "==")  # Default to equality if no operator is provided
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
                            if not isinstance(min_val, (int, float)):
                                logging.warning(f"Invalid 'min' value for range filter: {min_val}. Skipping filter.")
                                continue
                            logging.debug(f"[Range] Adding GTE filter: key={key}, value={min_val}")
                            filter_objects.append(MetadataFilter(key=key, value=min_val, operator=FilterOperator.GTE))

                        if max_val is not None:
                            if not isinstance(max_val, (int, float)):
                                logging.warning(f"Invalid 'max' value for range filter: {max_val}. Skipping filter.")
                                continue
                            logging.debug(f"[Range] Adding LTE filter: key={key}, value={max_val}")
                            filter_objects.append(MetadataFilter(key=key, value=max_val, operator=FilterOperator.LTE))

                        continue  # Skip direct append below

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
                        min_val = value.get("min")
                        max_val = value.get("max")

                        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
                            logging.warning(f"Invalid range values for key={key}: min={min_val}, max={max_val}. Skipping filter.")
                            continue

                        logging.debug(f"[Legacy Range] key={key}, min={min_val}, max={max_val}")
                        filter_objects.append(MetadataFilter(key=key, value=min_val, operator=FilterOperator.GTE))
                        filter_objects.append(MetadataFilter(key=key, value=max_val, operator=FilterOperator.LTE))
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
    """

    # def _build_metadata_filters(self, filters: Union[dict, list]) -> Optional[MetadataFilters]:
    #     filter_list = []
        
    #     # Handle case where filters is a dictionary
    #     if isinstance(filters, dict):
    #         for key, value in filters.items():
    #             if isinstance(value, list):
    #                 # Handle list (IN) filters
    #                 filter_list.append(MetadataFilter(key=key, value=value, operator=FilterOperator.IN))
    #             elif isinstance(value, dict) and 'min' in value and 'max' in value:
    #                 # Handle range filters (GTE, LTE)
    #                 min_value = value['min']
    #                 max_value = value['max']
                    
    #                 if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
    #                     filter_list.append(MetadataFilter(key=key, value=min_value, operator=FilterOperator.GTE))
    #                     filter_list.append(MetadataFilter(key=key, value=max_value, operator=FilterOperator.LTE))
    #                 else:
    #                     logging.warning(f"Invalid range filter for key {key}: min and max values must be numeric.")
    #             else:
    #                 # Handle single value filters (EQ)
    #                 filter_list.append(MetadataFilter(key=key, value=value, operator=FilterOperator.EQ))
        
    #     # Handle case where filters is a list (IN filters for multiple values)
    #     elif isinstance(filters, list):
    #         for value in filters:
    #             filter_list.append(MetadataFilter(key='generic_key', value=value, operator=FilterOperator.IN))
        
    #     # If no filters, return None
    #     if not filter_list:
    #         return None
        
    #     # Return metadata filters
    #     return MetadataFilters(filters=filter_list)


    def _build_metadata_filters(self, filters: Union[dict, list]) -> Optional[MetadataFilters]:
        filter_list = []

        if isinstance(filters, dict):
            for key, value in filters.items():
                # ✅ First, check for range format
                if isinstance(value, dict) and "min" in value and "max" in value:
                    min_value = value["min"]
                    max_value = value["max"]
                    if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
                        filter_list.append(MetadataFilter(key=key, value=min_value, operator=FilterOperator.GTE))
                        filter_list.append(MetadataFilter(key=key, value=max_value, operator=FilterOperator.LTE))
                    else:
                        logging.warning(f"Invalid range filter for key '{key}': min/max must be numeric.")
                # ✅ Second, handle list values (IN operator)
                elif isinstance(value, list):
                    filter_list.append(MetadataFilter(key=key, value=value, operator=FilterOperator.IN))
                # ✅ Third, simple EQ filter
                else:
                    filter_list.append(MetadataFilter(key=key, value=value, operator=FilterOperator.EQ))

        elif isinstance(filters, list):
            # Optional: handle list input
            for value in filters:
                filter_list.append(MetadataFilter(key='generic_key', value=value, operator=FilterOperator.IN))

        return MetadataFilters(filters=filter_list) if filter_list else None


    def _create_retriever(
        self,
        vector_index,
        metadata_filters: Optional[MetadataFilters] = None,
        top_k: int = 100
    ) -> VectorIndexRetriever:
        """
        Create a retriever from a vector index with optional metadata filters.

        Args:
            vector_index: The vector index to search against.
            metadata_filters: Optional metadata filters to restrict search results.
            top_k: Number of top similar documents to retrieve.

        Returns:
            Configured VectorIndexRetriever instance.
        """
        logging.debug(f"Creating retriever: top_k={top_k}, filters={metadata_filters}")

        return VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=top_k,
            filters=metadata_filters
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
            
    def _split_filter_dict(self, filter_list: List[Dict[str, Any]]):
        strict_filters = {}
        soft_filters = {}

        multi_valued_fields = {"job_title", "technical_skills", "location"}
        logging.debug("[Splitter] Starting filter split")

        for f in filter_list:
            key = f.get("name") or f.get("key")
            value = f.get("value")

            if not key:
                logging.warning("[Splitter] Skipping filter with missing key: %s", f)
                continue

            logging.debug("[Splitter] Processing filter: key=%s, value=%s", key, value)

            # Extract actual value if nested
            if isinstance(value, dict) and "value" in value:
                value = value["value"]
                logging.debug("[Splitter] Extracted nested 'value' for %s: %s", key, value)

            # Try to parse stringified JSON
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, (list, dict)):
                        value = parsed
                        logging.debug("[Splitter] Parsed JSON for key=%s: %s", key, value)
                except json.JSONDecodeError:
                    logging.debug("[Splitter] Value for key=%s is not JSON parseable", key)

            # Wrap scalar values for expected lists
            if key in multi_valued_fields and not isinstance(value, list):
                value = [value]
                logging.debug("[Splitter] Wrapped scalar value into list for %s: %s", key, value)

            # Split based strictly on config list
            if key in self.strict_filter_fields:
                strict_filters[key] = value
                logging.debug("[Splitter] Added to strict_filters: %s = %s", key, value)
            else:
                soft_filters[key] = value
                logging.debug("[Splitter] Added to soft_filters: %s = %s", key, value)

        logging.debug("[Splitter] Final strict_filters: %s", strict_filters)
        logging.debug("[Splitter] Final soft_filters: %s", soft_filters)

        return strict_filters, soft_filters


    def _score_soft_filters(self, documents, soft_filters, use_fuzzy=False, threshold=80):
        """
        Scores resumes based on how many soft filter items match.
        Supports fuzzy matching and 'range' operator for numeric fields.
        Returns a list of dicts with score, metadata, and basic candidate info.
        """
        logging.debug(f"Soft filters passed: {soft_filters}")
        scored = []

        KEY_ALIASES = {
            "job_title": ["latest_job_title", "other_job_titles"],
        }

        for doc in documents:
            metadata = doc.get("metadata", {}) if isinstance(doc, dict) else getattr(doc, "metadata", {})
            doc_id = metadata.get("doc_id", "unknown")

            logging.debug(f"Scoring doc_id={doc_id}, metadata keys: {list(metadata.keys())}")
            score = 0
            total_possible = 0

            for key, filter_spec in soft_filters.items():
                logging.debug(f"Evaluating filter for key: {key}, filter_spec: {filter_spec}")

                # Handle key aliases    
                candidate_value = None
                if key in KEY_ALIASES:
                    for alias_key in KEY_ALIASES[key]:
                        if alias_key in metadata and metadata[alias_key]:
                            candidate_value = metadata[alias_key]
                            logging.debug(f"Using alias '{alias_key}' for key '{key}': {candidate_value}")
                            break
                if candidate_value is None:
                    candidate_value = metadata.get(key)
                    logging.debug(f"Using direct key '{key}': {candidate_value}")                
                logging.debug(f"Candidate value for '{key}': {candidate_value}")

                # Backward-compatible list filter (e.g., skills or locations)
                if isinstance(filter_spec, list):
                    required_values = [v.lower() for v in filter_spec]
                    candidate_values = candidate_value or []
                    if not isinstance(candidate_values, list):
                        candidate_values = [str(candidate_value)]
                    candidate_values = [v.lower() for v in candidate_values]

                    matched_score = 0
                    for req in required_values:
                        best_score = 0
                        for cand in candidate_values:
                            if use_fuzzy:
                                score = fuzz.token_set_ratio(req, cand)
                                best_score = max(best_score, score)
                            else:
                                if req == cand:
                                    best_score = 100
                                    break
                        matched_score += best_score / 100.0  # normalize to 0–1

                    score += matched_score
                    total_possible += len(required_values)

                # Dict-based filter (supports operator like "range")
                elif isinstance(filter_spec, dict):
                    operator = filter_spec.get("operator")
                    value = filter_spec.get("value")

                    if operator == "range" and isinstance(value, dict):
                        try:
                            min_val = value.get("min", float("-inf"))
                            max_val = value.get("max", float("inf"))
                            candidate_num = float(candidate_value)
                            if min_val <= candidate_num <= max_val:
                                score += 1
                            total_possible += 1
                        except (TypeError, ValueError):
                            total_possible += 1  # Counted but not matched

            normalized_score = score / total_possible if total_possible else 0

            scored.append({
                "resume_id": doc_id,
                "name": metadata.get("candidate_name"),
                "job_title": metadata.get("latest_job_title"),
                "career_domain": metadata.get("career_domain"),
                "years_of_experience": metadata.get("years_of_experience"),
                "location": metadata.get("location"),
                "technical_skills": metadata.get("technical_skills", []),
                "leadership_skills": metadata.get("leadership_skills", []),
                "education": metadata.get("highest_education_level"),
                "resume_link": f"{self.resume_details_popup_url}?ID={doc_id}",
                "score": round(normalized_score, 2),
                "matched_count": score,
                "total_required": total_possible
            })

        return scored
    
    # def build_pinecone_filter(self, metadata_filters: MetadataFilters, condition: str = "$and") -> Dict[str, Any]:
    #     if not metadata_filters or not metadata_filters.filters:
    #         return {}

    #     # Check if we have one filter or multiple
    #     if len(metadata_filters.filters) == 1:
    #         return self._convert_to_pinecone_filter(metadata_filters.filters[0])

    #     return {
    #         condition: [self._convert_to_pinecone_filter(f) for f in metadata_filters.filters]
    #     }

    # def _convert_to_pinecone_filter(self, metadata_filter: MetadataFilter) -> Dict[str, Any]:
    #     """
    #     Convert a MetadataFilter object to a Pinecone-compatible filter format.
    #     """
    #     if metadata_filter.operator == FilterOperator.EQ:
    #         return {metadata_filter.key: {"$eq": metadata_filter.value}}
    #     elif metadata_filter.operator == FilterOperator.IN:
    #         return {metadata_filter.key: {"$in": metadata_filter.value}}
    #     elif metadata_filter.operator == FilterOperator.GTE:
    #         return {metadata_filter.key: {"$gte": metadata_filter.value}}
    #     elif metadata_filter.operator == FilterOperator.LTE:
    #         return {metadata_filter.key: {"$lte": metadata_filter.value}}
    #     else:
    #         raise ValueError(f"Unsupported operator: {metadata_filter.operator}")
