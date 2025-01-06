from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import VectorStoreIndex, get_response_synthesizer, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
import openai
from llama_index.llms.openai import OpenAI
from llama_index.core.prompts import PromptTemplate, Prompt

from flask import request, jsonify, Response
from flask_restful import Resource, current_app
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class SummarizerOld(Resource):

    def __init__(self) -> None:
      logging.debug("Inside Summarizer instance init")
      #self.vectordb = None
      self.collection = None
      self.openai_api_key = current_app.config['OPENAI_API_KEY']
      self.pinecone_api_key = current_app.config['PINECONE_API_KEY']
      self.pinecone_index = current_app.config['PINECONE_INDEX']
      self.llm_model = current_app.config['LLM_MODEL']
      os.environ["OPENAI_API_KEY"] = self.openai_api_key
      Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)

      # Initialize Pinecone and OpenAI
      #pinecone.init(api_key=current_app.config['PINECONE_API_KEY'])

    def get(self):
        logging.debug("Inside Summarizer get method")
        # Retrieve query parameters
        file_id = request.args.get('file_id')
        namespace = request.args.get('namespace')
        logging.debug("file_id = " + file_id)
        logging.debug("namespace = " + namespace)
         #question = request.args.get('question')

        # Check if both file_id and question are provided
        if not file_id:
            return jsonify({"error": "file_id parameter is required"}), 400

        if not namespace:
            return jsonify({"error": "namespace parameter is required"}), 400

        question = "Summarize key aspects of the financial report. Include overall business strategy, and highlights from earnings, cashflow and balance sheet."

        # Run the RAG query function
        try:
            answer = self.rag_query(file_id, namespace, question)
            return jsonify({"AIResponse": answer})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    # Define the RAG function
    def rag_query(self, file_id, namespace, question):
        logging.debug("Inside Summarizer rag_query method")
        try: 

            # Set up Pinecone vector store and storage context
            vector_store = PineconeVectorStore(index_name=self.pinecone_index,
                                        api_key=self.pinecone_api_key,
                                        namespace=namespace)
            logging.debug("Pinecone Vector Store initialized")

            # Instantiate VectorStoreIndex object from your vector_store object
            logging.debug("Instantiating VectorStoreIndex ...")
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            logging.debug("VectorStoreIndex object instantiated")

            # Grab 5 search results
            logging.debug("Instantiating VectorIndexRetriever ...")

            # configure filters
            filters = MetadataFilters(filters=[MetadataFilter(key="file_id", value=file_id)])
            retriever = VectorIndexRetriever(index=vector_index, 
                                             similarity_top_k=20,
                                             filters=filters)
            logging.debug("VectorIndexRetriever object instantiated")

            # configure response synthesizer
            response_synthesizer = get_response_synthesizer()

            # configure post processor
            postprocessor = SimilarityPostprocessor(similarity_cutoff=0.7)

            # Define few-shot examples
            examples = [
                {
                    "question": "What is the company background?", 
                    "answer": "SoFi (NASDAQ: SOFI) is a member-centric, one-stop shop for digital financial services on a mission to help people achieve financial independence to realize their ambitions. The company’s full suite of financial products and services helps its nearly 9.4 million SoFi members borrow, save, spend, invest, and protect their money better by giving them fast access to the tools they need to get their money right, all in one app. SoFi also equips members with the resources they need to get ahead – like credentialed financial planners, exclusive experiences and events, and a thriving community – on their path to financial independence."
                },
                {
                    "question": "What is the company's product line?", 
                    "answer": "The company's  product include: \n - SoFi Money \n - SoFi Invest\n - SoFi Credit Card\n -Loan Platform Business"
                },
                {
                        "question": "What is the company's consolidated result?", 
                        "answer": "SoFi reported a number of key financial achievements in the third quarter of 2024, including total GAAP net revenue of $697.1 million, which increased 30 percent relative to the prior-year period's $537.2 million. Third quarter record adjusted net revenue of $689.4 million grew 30 percent from the corresponding prior-year period of $530.7 million. Third quarter record adjusted EBITDA of $186.2 million, a 27percent adjusted EBITDA margin, increased 90percent from the same prior year period's $98.0 million. All three segments achieved record contribution profit in the quarter."
                },
                {
                    "question": "What is the company's net income?", 
                    "answer": "Net income (loss) in thousands for the quarter ending September 2024 was $ 60,745"
                },
            ]

            # Create a custom prompt template with placeholders for dynamic input
            custom_prompt_template = """
            You are an expert financial analyst. Below are some examples of how to respond:

            Example 1:
            Question: {examples[0]['question']}
            Answer: {examples[0]['answer']}

            Example 2:
            Question: {examples[1]['question']}
            Answer: {examples[1]['answer']}

            Example 3:
            Question: {examples[2]['question']}
            Answer: {examples[2]['answer']}

            Example 4:
            Question: {examples[3]['question']}
            Answer: {examples[3]['answer']}

            Now, respond to the following query:

            {query}
            """

            #custom_prompt = PromptTemplate(custom_prompt_template)

            #result = query_engine.query("You are an expert financial analyst. You are analyzing financial report of a publicly listed company. Start with the name of the company.Provide a summary of the company's background, summary of its financial statement including its consolidated results, revenue, net income, total assets and liability. Provide the response in markdown format.")
            
            #response_synthesizer = get_response_synthesizer(prompt=custom_prompt)            
            # Pass in your retriever from above, which is configured to return the top 5 results
            query_engine = RetrieverQueryEngine(retriever=retriever,
                                                response_synthesizer=response_synthesizer,
                                                node_postprocessors=[postprocessor])
            logging.debug("Summarizer.rag_query: query_engine is ready")

            #query_engine.update_prompts( {"response_synthesizer:text_qa_template": custom_prompt} )
            
            result = query_engine.query("You are an expert financial analyst. You are analyzing financial report of a publicly listed company. Provide the company's summary by answering the following questions: (1) What is the name of the company? (2) What is the company's background? (3) What are its products? (4) What was its consolidated result? (5) What is the company's guidance and outlook? (6) What were ist financial results including Total Revenue, EBITDA, Net Income (Loss), Total Assets, Total Liability, Cash and cash equivalent. Make sure that the financial results include the units, e.g., thousands or millions. Provide the response in markdown format.")

            #result = query_engine.query("Summarize the financial statement of the company in the given context")
            #logging.debug(f"Summarizer.rag_query: response:\n{result}")
            logging.debug(f"Response text: {str(result.response)}")
            #logging.debug(f"Node content: {result.get_content()}")
            #response_content = result if isinstance(query.response, str) else str(query.response)
            # Filter and concatenate text from retrieved documents based on file_id
            #context = "\n".join(doc.text for doc in retrieved_documents if doc.metadata.get("file_id") == file_id)

            # Step 3: Construct prompt with context and question
            #prompt = f"You are an expert financial analyst. You are analyzing financial report of a publicly listed company. \n\nContext:\n{context}\n\nQuestion: {question}"

            response_str = json.dumps(result.response)
            response_str = response_str.replace("\\n", "\n")  # Replace escaped newlines
            return response_str
            # Return as a JSON response
            #return Response(response_str, mimetype='application/json')
            
        except Exception as ex:
            logging.debug(f"======> Error in rag_query: {str(ex)}")
