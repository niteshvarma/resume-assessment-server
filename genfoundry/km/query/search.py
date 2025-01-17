import logging
import json
import os
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
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        logging.debug("LLM model: " + self.llm_model)
        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        Settings.embed_model = embed_model
        logging.debug("ResumeSearch initialized.")

    def search(self, namespace, question):
        logging.debug("Inside search method")
        try:
            vector_store = PineconeVectorStore(
                index_name=self.pinecone_index, 
                api_key=self.pinecone_api_key, 
                namespace=namespace)
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

            retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=5)
            response_synthesizer = get_response_synthesizer()
            postprocessor = SimilarityPostprocessor(similarity_cutoff=0.5)

            query_engine = RetrieverQueryEngine(retriever=retriever, 
                                                response_synthesizer=response_synthesizer, 
                                                node_postprocessors=[postprocessor])
            logging.debug("Running query engine with question.")
            
            llm_question = f"""You are an expert talent acquisition personnel. You are analyzing candidates' background from a database of resumes. 
            Instructions:
            - Provide the response in markdown format.
            - Do not wrap the response in any way, e.g., quotes, prefix, suffix)
            Answer the following question: {question}"""
            
            result = query_engine.query(llm_question)
            response_str = json.dumps(result.response)
            response_str = response_str.replace("\\n", "\n")  # Replace escaped newlines
            return response_str
        except Exception as ex:
            logging.error(f"Error in search: {str(ex)}")
            raise
