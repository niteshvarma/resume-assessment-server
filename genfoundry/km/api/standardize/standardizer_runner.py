from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from genfoundry.km.preprocess.resume_transformer import ResumeStandardizer
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser
from genfoundry.km.persist.vector_db_proxy import PineconeVectorizer
from genfoundry.km.query.search import ResumeSearcher

import os
import json
import uuid

test_prompt = """
            Analyze the document and extract the following details:
            - Name
            - Career Domain (e.g., tech, medical, sales, education)
            - Total Years of Experience
            - Highest Education Level
            - Current Location (City/State/Country if available)
            
            Question:
            {question}
            """

class ResumeStandardizerRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Resume Standardizer HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        os.environ["PINECONE_API_KEY"] = current_app.config['PINECONE_API_KEY']
        os.environ["PINECONE_INDEX"] = current_app.config['PINECONE_INDEX']
        os.environ["PINECONE_NAMESPACE"] = current_app.config['PINECONE_NAMESPACE']

        self.standardizer = ResumeStandardizer(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            langchain_api_key = current_app.config['LANGCHAIN_API_KEY'],
            llm_model = current_app.config['LLM_MODEL'],
        )

        self.doc_parser = PyMuPDFDocumentParser()
        self.vectorizer = PineconeVectorizer()
        
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))

 
    def post(self):
        if 'resume' not in request.files:
            return jsonify({"error": "Resume file is required"}), 400

        # Get uploaded file
        resume_file = request.files['resume']
        resume_string = self.doc_parser.parse_document(resume_file)

        try:
            # Standardize the resume and extract metadata
            response = self.standardizer.standardize(resume_string)
            logging.debug(f"Standardized Response: {response}")

            # Check if response is valid and contains the expected structure
            if not response or "error" in response:
                logging.error("Error in standardization or metadata extraction")
                return jsonify({"error": response.get("error", "Unknown error occurred")}), 500
        
            resume_id = f"Doc:{uuid.uuid4()}"
            logging.debug(f"Processing resume with ID: {resume_id}")
            # Parse the standardized resume and metadata
            standardized_resume = response.get("standardized_resume", {})
            metadata = response.get("metadata", {})

            # Vectorize and store the resume in Pinecone
            #self.vectorizer.vectorize_and_store_resume(resume_id, standardized_resume, metadata)
            self.vectorizer.vectorize_and_store_text_resume(resume_id, resume_string, metadata)
            logging.debug(f"Resume {resume_id} vectorized and stored in Pinecone")
            self.test()

            # Return both standardized resume and metadata as the API response
            return jsonify({
                "AIResponse": {
                    "standardized_resume": standardized_resume,
                    "metadata": metadata
                }
            })
        except Exception as e:
            logging.error(f"Error processing resume: {e}")
            return jsonify({"error": "Server Error"}), 500
        
    def test(self):
        logging.debug("Testing ...")
        try:
            question = "Find me the name of candidates with Kafka and Cloud experience. Also provide a brief career profile of the candidates."
            searcher = ResumeSearcher()
            response = searcher.search(os.getenv("PINECONE_NAMESPACE"), question)
            return response
        except Exception as e:
            logging.error(f"Error in test: {str(e)}")
            raise
