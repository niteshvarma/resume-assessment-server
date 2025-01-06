import logging, json
from langchain.tools import BaseTool
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

import os

ROACalculatorToolDesc = (
    """
    Use this tool when you need to calculate the Return on Asset (ROA) from a given financial statement.
    """
    )

roa_question = (
    """
    You are an expert financial analyst. You are analyzing financial report of a publicly listed company. \n
    Find the following: 1. Units (e.g., $ in thousands or $ in millions), 2. Net Income (Loss) based on GAAP, 3. Total Assets, 4. Previously reported Total Assets. \n
    
    Ensure all figures are of consistent units (for example, all figures should be in thousands or millions). \n
    
    Net Income is reported within Income Statement table (also known as Statement of Comprehensive Income). \n
    
    Assets values can be found in Balance Sheets. Look under Assets heading.\n

    Return as a json string with values for 'units', 'income', 'current_asset', 'previous_asset'. Here is an example:
    {
        "units": "$ in thousands",
        "net_income": 600000,
        "current_assets": 3000000,
        "previous_assets": 250000
    }
    """
)

class ROACalculatorTool(BaseTool):
    logging.debug("====> Inside ROACalculatorTool")
    name = "ROA Calculator"
    description = ROACalculatorToolDesc

    """
    def __init__(self, openai_api_key, 
                 pinecone_api_key, 
                 pinecone_index, 
                 llm_model):
        self.openai_api_key = openai_api_key
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_index = pinecone_index
        self.llm_model = llm_model
        self._setup_llm()
        self.logging.debug("Initialized ROACalculatorTool with OpenAI,  Pinecone and LLM settings.")
        self.description = ROACalculatorToolDesc

    def _setup_llm(self):
        from llama_index.llms.openai import OpenAI
        os.environ["openai_api_key"] = self.openai_api_key
        from llama_index.core import Settings
        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
    """
    def __init__(self):
        from llama_index.embeddings.openai import OpenAIEmbedding
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

        llm_model = os.getenv("llm_model")
        logging.debug(f"====> LLM Model: {llm_model}")
        Settings.llm = OpenAI(model=llm_model, temperature=0.0)
        Settings.embed_model = embed_model

    def _run(self, file_id: str, namespace: str):
        logging.debug("====> Inside ROACalculatorTool.run()")
        data = self.calculate_roa(file_id, namespace)
        logging.debug(f"====> run(): calculate_roa result: {data}")
        #json_data = json.dumps(str(data))
        # Extract values
        #income = float(json_data.get('income'))
        #logging.debug(f"Income = {income}")
        #current_asset = float(json_data.get('current_asset'))
        #logging.debug(f"Current Asset = {current_asset}")
        #previous_asset = float(json_data.get('previous_asset'))
        #logging.debug(f"Previous Quarter Asset = {previous_asset}")
        #avg_asset = (current_asset+previous_asset)/2
        #roa = income/avg_asset
        #return roa 
        return "ROA Calculated"

    def _arun(self, file_id: str, namespace: str):
        raise NotImplementedError("This tool does not support async")

    def calculate_roa(self, file_id, namespace):
        logging.debug("====> Inside ROACalculatorTool.calculate_roa()")
        try:
            index_name = os.getenv("pinecone_index")
            api_key = os.getenv("pinecone_api_key")
            logging.debug(f"====> Initializing PineconeVectorStore with index: {index_name} and Pinecone API Key: {api_key}")
            vector_store = PineconeVectorStore(
                index_name=index_name, 
                api_key=api_key, 
                namespace=namespace
                )
            logging.debug("====> Vector Store initialized")
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            logging.debug("====> Vector Store Index initialized")

            filters = MetadataFilters(
                filters=[MetadataFilter(key="file_id", value=file_id)]
                )
            retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=5, filters=filters)
            response_synthesizer = get_response_synthesizer()
            similarity_pp = SimilarityPostprocessor(similarity_cutoff=0.7)
            reranker_pp = cohere_rerank = CohereRerank(top_n=10)
            query_engine = RetrieverQueryEngine(
                retriever=retriever, 
                response_synthesizer=response_synthesizer, 
                node_postprocessors=[similarity_pp, reranker_pp])
            logging.debug("====> Running query engine with question.")
            result = query_engine.query(roa_question)
            logging.debug(f"====> Result = {result}")
            #response_str = json.dumps(result.response).replace("\\n", "\n")
            return result
        except Exception as ex:
            logging.error(f"Error in ROA calculation: {str(ex)}")
            raise
