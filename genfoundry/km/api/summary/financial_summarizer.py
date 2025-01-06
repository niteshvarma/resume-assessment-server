import logging
import json
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.embeddings.openai import OpenAIEmbedding

import os

class FinancialSummarizer:
    def __init__(self, openai_api_key, pinecone_api_key, pinecone_index, llm_model):
        self.openai_api_key = openai_api_key
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_index = pinecone_index
        self.llm_model = llm_model
        logging.debug("Initializing FinancialSummarizer with OpenAI and Pinecone settings.")
        self._setup_llm()

    def _setup_llm(self):
        from llama_index.llms.openai import OpenAI
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        from llama_index.core import Settings
        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        Settings.embed_model = embed_model


    def summarize(self, file_id, namespace, question):
        try:
            vector_store = PineconeVectorStore(index_name=self.pinecone_index, 
                                               api_key=self.pinecone_api_key, 
                                               namespace=namespace)
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

            filters = MetadataFilters(filters=[MetadataFilter(key="file_id", value=file_id)])
            retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=20, filters=filters)
            response_synthesizer = get_response_synthesizer()
            postprocessor = SimilarityPostprocessor(similarity_cutoff=0.7)

            query_engine = RetrieverQueryEngine(retriever=retriever, 
                                                response_synthesizer=response_synthesizer, 
                                                node_postprocessors=[postprocessor])
            logging.debug("Running query engine with question.")
            result = query_engine.query(question)
            response_str = json.dumps(result.response).replace("\\n", "\n")
            return response_str
        except Exception as ex:
            logging.error(f"Error in summarization: {str(ex)}")
            raise
