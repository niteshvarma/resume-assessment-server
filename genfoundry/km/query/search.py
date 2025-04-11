import logging
import json
import os
import re
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from langchain.agents import initialize_agent, AgentType
from langchain.agents import Tool
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from genfoundry.km.query.tools.extract_filters import ExtractFiltersTool
from tools.utils import FilterNormalizer

class ResumeSearcher:
    def __init__(self):
        logging.debug("Initializing ResumeSearcher with OpenAI and Pinecone settings.")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX")
        self.llm_model = os.getenv("LLM_MODEL")
        self.resume_details_popup_url = os.getenv("RESUME_DETASILS_POPUP_URL")
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

    def search(self, namespace, question):
        logging.debug("Inside search method")
        try:
            vector_index = self._init_vector_index(namespace)
            agent = self._initialize_agent()
            raw_filters = self._extract_filters(agent, question)
            normalized_filters = FilterNormalizer.normalize(raw_filters)
            metadata_filters = self._build_metadata_filters(normalized_filters)

            retriever = self._create_retriever(vector_index, metadata_filters)
            query_engine = self._build_query_engine(retriever)

            llm_question = self._format_llm_query(question)
            result = query_engine.query(llm_question)
            logging.debug(f"Query Engine result: {result.response}")            
            return self._format_response(result.response)
        except KeyError as ex:
          logging.error(f"Key error during search: {str(ex)}")
          raise
        except Exception as ex:
            logging.error(f"Error in search: {str(ex)}")
            raise

    def _init_vector_index(self, namespace):
        logging.debug(f"Initializing vector index for namespace: {namespace}")
        vector_store = self._get_tenant_vectorestore(namespace)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)

    def _initialize_agent(self):
        logging.debug("Initializing agent with ExtractFiltersTool")
        extract_filters_tool = ExtractFiltersTool()
        tools = [
            Tool(
                name="ExtractFiltersTool",
                func=extract_filters_tool.run,
                description="Extracts filters such as role, location, and experience from a query."
            )
        ]
        return initialize_agent(tools, OpenAI(model=self.llm_model, temperature=0.0), agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    def _extract_filters(self, agent, question):
        logging.debug("Running agent to extract filters")
        result = agent.run(f"Extract filters from this query: {question}")
        logging.debug(f"Extracted filters: {result}")
        return result  # No need to load JSON if it's already a dictionary

    def _build_metadata_filters(self, filters_dict):
        logging.debug("Building MetadataFilters from normalized filter dictionary")
        metadata_filters = []
        for key, value in filters_dict.items():
            key = str(key)  # Ensure the key is a string (if it's not already)
            if isinstance(value, list):
                metadata_filters.extend([MetadataFilter(key=key, value=v) for v in value])
            else:
                metadata_filters.append(MetadataFilter(key=key, value=value))
        return MetadataFilters(filters=metadata_filters) if metadata_filters else None
    
    def _create_retriever(self, vector_index, filters):
        return VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=10,
            filters=filters
        )

    def _build_query_engine(self, retriever):
        return RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=get_response_synthesizer(),
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.78)]
        )

    def _format_llm_query(self, question):
        return f"""
  You are an expert talent acquisition professional analyzing a vector database of resumes. Your task is to return only the **most relevant candidates** based on the user’s natural language query.

  ### **CRITICAL INSTRUCTIONS**:

  - **STRICT RELEVANCE ONLY**:
    - Candidates must have **clear, significant, and recent** experience in the requested role, field, or technology.
    - **Exclude** candidates who are only **marginally or historically** connected to the field.
    - If a candidate is **overqualified** (e.g., 20+ years of experience for a 2–5 year role), **exclude them**, unless the query explicitly permits or requests senior profiles.

  - **FILTER BY DOMAIN / FUNCTION**:
    - Determine the **professional domain or industry** based on the query (e.g., healthcare, software development, education).
    - Only include candidates whose **work experience and skills** are directly aligned with this domain.

  - **MATCH LEVEL OF EXPERIENCE**:
    - Infer the **seniority level** (e.g., entry-level, mid-level, senior) based on phrases like “around 5 years,” “minimum 2 years,” or “senior developer”.
    - Exclude:
      - Underqualified candidates with **less than the minimum experience**.
      - Overqualified candidates with **significantly more experience** (unless the query allows).
      - Candidates whose **experience is too old or outdated**.

  - **MATCH FUNCTIONAL RESPONSIBILITIES (NOT JUST TITLES)**:
    - Prioritize **functional relevance** over just job titles. Candidates must have actually **performed tasks** aligned with the role.
    - Example: For “DevOps,” only include those with **hands-on automation, CI/CD, container orchestration**, etc. Not someone with a vague title like "IT Manager" without relevant task description.

  - **FORMAT RESPONSE IN MARKDOWN**:
    - List candidates in a **numbered format**.
    - Display the **candidate's name as a hyperlink**: `{self.resume_details_popup_url}?ID={{resume_id}}`, for example: "https://api.recruitr.genfoundry.ca/resumedetails?ID=Doc:1234".
    - Include:
      - **Latest job title**
      - **Years of experience**
      - **Brief career summary taken from resume text** (no more than 5 lines)

  - **AVOID DUPLICATES**:
    - Ensure no repetition by checking for same name or {{resume_id}}.

  - **STRICT FACTUAL ACCURACY**:
    - Use only information **explicitly available** in the resume.
    - **Do NOT assume** qualifications or roles.

  ### DO NOT:
  - Do not include candidates who only match **buzzwords** without substance.
  - Do not justify irrelevant or overqualified candidates.
  - Do not return candidates from unrelated industries.
  - Do not generate explanations or summary text outside of the candidate list.

  ---

  ### **Answer the following query:**  
  {question}
  """

    def _format_response(self, raw_response):
        try:
            response_str = json.dumps(raw_response).replace("\\n", "\n").strip().strip('"').strip("'")
            response_str = re.sub(r"^-\s*", "", response_str)
            logging.debug(f"Formatted search response: {response_str}")
            return response_str
        except Exception as e:
            logging.error(f"Failed to format response: {str(e)}")
            return str(raw_response)

    def _get_tenant_vectorestore(self, tenant_id):
        logging.debug(f"Fetching vector store for tenant: {tenant_id}")
        pinecone_namespace = f"{tenant_id}_Resumes_NS"
        return PineconeVectorStore(
            index_name=self.pinecone_index,
            api_key=self.pinecone_api_key,
            namespace=pinecone_namespace
        )
