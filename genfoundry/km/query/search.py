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
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings


class ResumeSearcher:
    def __init__(self):
        logging.debug("Initializing ResumeSearch with OpenAI and Pinecone settings.")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX")
        self.llm_model = os.getenv("LLM_MODEL")
        self.resume_details_popup_url = os.getenv("RESUME_DETASILS_POPUP_URL")
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        logging.debug("LLM model: " + self.llm_model)
        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        Settings.embed_model = embed_model
        logging.debug("ResumeSearch initialized.")

    def search(self, namespace, question):
        logging.debug("Inside search method")
        try:
            #vector_store = PineconeVectorStore(
            #    index_name=self.pinecone_index, 
            #    api_key=self.pinecone_api_key, 
            #    namespace=namespace)
            vector_store = self.get_tenant_vectorestore(namespace)
            logging.debug(f"Vector store initialized with namespace: {namespace}")
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

            retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=10)
            response_synthesizer = get_response_synthesizer()
            postprocessor = SimilarityPostprocessor(similarity_cutoff=0.75)

            # To set the threshold, set it in vector_store_kwargs       
            query_engine = RetrieverQueryEngine(
                retriever=retriever, response_synthesizer=response_synthesizer, node_postprocessors=[postprocessor])
            logging.debug("Running query engine with question.")
            
            # To set the threshold, set it in vector_store_kwargs
            #query_engine = vector_index.as_query_engine(
            #    vector_store_query_mode="mmr", 
            #    vector_store_kwargs={"mmr_threshold": 0.5}
            #)

            llm_question = f"""
You are an expert talent acquisition professional analyzing a vector database of resumes. Your task is to find **highly relevant candidates** who align with the requirements provided in the user’s query.

### **Instructions:**
- **ENSURE STRONG RELEVANCE**: Candidates **must have substantial experience** in the requested domain. If a candidate’s background is **only tangentially related**, **exclude them**.
- **FILTER BY INDUSTRY/DOMAIN**: Infer the most relevant industry or professional field **based on the query**. Candidates **must belong to this inferred industry**.  
  - Example: If the query is about *Cloud Security*, candidates should have **cybersecurity or cloud computing experience**.  
  - If the query is about *Pediatrics*, candidates should be from **medical or healthcare backgrounds**.  
  - **Exclude candidates from unrelated fields** (e.g., a software engineer for a nursing role).
- **FOCUS ON MEANING, NOT JUST KEYWORDS**: Candidates **do not need to match exact wording** but must have **skills, roles, and experience** that align **semantically** with the query.  
  - Example: If searching for *Enterprise Architecture*, also consider candidates with **"IT Strategy," "Cloud Architecture," "Solution Architecture," or "Digital Transformation"** experience.  
  - However, DO NOT include candidates who **only have general leadership roles** without architectural responsibilities.
- **FORMAT THE RESPONSE AS MARKDOWN**:
  - Present results as a **numbered list**.
  - Include **candidate's name as a hyperlink** (`{self.resume_details_popup_url}?ID={{resume_id}}`), for example: "https://api.recruitr.genfoundry.ca/resumedetails?ID=Doc:1234".
  - Provide **latest job title, years of experience, and a brief executive summary**.
- **ENSURE UNIQUE CANDIDATES**: DO NOT present the same candidate multiple times (look at candidate's name and {{resume_id}}).
- **DO NOT invent details** or infer qualifications that are not present.
- **DO NOT wrap the response** in quotes (`""` or `''`).
- **DO NOT attempt to justify including unrelated candidates**.
---

### **Answer the following query:**  
{question}
"""
            
            result = query_engine.query(llm_question)

            response_str = json.dumps(result.response)
            response_str = response_str.replace("\\n", "\n")  # Replace escaped newlines
            # Clean up leading/ending quotes and leading hyphen
            response_str = response_str.strip().strip('"').strip("'")  # Remove leading/trailing quotes
            response_str = re.sub(r"^-\s*", "", response_str)  # Remove leading hyphen with optional space
            logging.debug(f"Search response: {response_str}")
            return response_str
        except Exception as ex:
            logging.error(f"Error in search: {str(ex)}")
            raise

    def get_tenant_vectorestore(self, tenant_id):
        """Returns the Pinecone namespace for the tenant."""
        pinecone_namespace = f"{tenant_id}_Resumes_NS"  # Per-tenant namespace
        vector_store = PineconeVectorStore(
            index_name=self.pinecone_index,
            api_key=self.pinecone_api_key,
            namespace=pinecone_namespace
        )
        return vector_store
