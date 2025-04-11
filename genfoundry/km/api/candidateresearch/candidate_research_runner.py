from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from genfoundry.km.preprocess.candidate_research import CandidateResearcher
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser

import os
import json
import uuid

class CandidateResearchRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Candidate Research HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        os.environ["PINECONE_API_KEY"] = current_app.config['PINECONE_API_KEY']
        os.environ["PINECONE_INDEX"] = current_app.config['PINECONE_INDEX']
        os.environ["PINECONE_NAMESPACE"] = current_app.config['PINECONE_NAMESPACE']
        os.environ["MONGO_URI"] = current_app.config['MONGO_URI']
        os.environ["MONGO_DB"] = current_app.config['MONGO_DB']
        os.environ["MONGO_COLLECTION"] = current_app.config['MONGO_COLLECTION']
        os.environ["RESUME_DETAILS_POPUP_URL"] = current_app.config['RESUME_DETAILS_POPUP_URL']

        self.researcher = CandidateResearcher(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            langchain_api_key = current_app.config['LANGCHAIN_API_KEY'],
            llm_model = current_app.config['LLM_MODEL'],
        )

        self.doc_parser = PyMuPDFDocumentParser()
        
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
            # Perform resume research
            response = self.researcher.research(resume_string)
            logging.debug(f"Research Response: {response}")

            # Check if response is valid and contains the expected structure
            if not response or "error" in response:
                logging.error("Error in standardization or metadata extraction")
                return jsonify({"error": response.get("error", "Unknown error occurred")}), 500
                    
            # Return research response as the API response
            return jsonify({
                "AIResponse": {
                    "base_research": response
                }
            })
        except Exception as e:
            logging.error(f"Error processing resume: {e}")
            return jsonify({"error": "Server Error"}), 500
