from flask import request, jsonify, g
from flask_restful import Resource, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os
import json
import tempfile
import uuid
from langchain_openai import ChatOpenAI
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser
from genfoundry.km.api.analyze.resume_analyzer import ResumeAnalyzer

logger = logging.getLogger(__name__)

class ResumeAnalyzerRunner(Resource):
    def __init__(self):
        logger.debug("Initializing Resume Analyzer HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        self.analyzer = ResumeAnalyzer(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            langchain_api_key = current_app.config['LANGCHAIN_API_KEY'],
            llm_model = current_app.config['LLM_MODEL'],
        )

        self.parser = PyMuPDFDocumentParser()
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"error": "Tenant ID is required"}), 400

        if 'resume' not in request.files:
            return jsonify({"error": "Resume is required for assessment"}), 400

        # Get uploaded file
        resume_file = request.files['resume']
        resume_filename = resume_file.filename
        resume = None
        try:
            # Save to temporary file
            tmp_dir = tempfile.mkdtemp()
            unique_filename = f"{tenant_id}_{uuid.uuid4().hex}_{resume_filename}"
            tmp_path = os.path.join(tmp_dir, unique_filename)
            resume_file.save(tmp_path)
            resume = self.parser.parse_document(tmp_path)
        except Exception as e:
            logger.error(f"Error saving file to temp directory: {e}")
            return {"error": "Server Error"}, 500

        if not resume:
            logger.error("Failed to parse resume")
            return jsonify({"error": "Failed to parse resume"}), 400
        else:
            return self.analyze_resume(resume)


    def analyze_resume(self, resume):
        try:
            assess_response = self.analyzer.assess(resume)

            if assess_response.startswith("json"):
                assess_response = assess_response[4:].strip()
            
            if not assess_response or not assess_response.strip():
                logger.error("Empty response received")
                return jsonify({"error": "Empty response from assessment tool"}), 500

            # If the response is a JSON string, parse it
            if isinstance(assess_response, str):
                parsed_response = json.loads(assess_response)

            # Return the parsed JSON as the HTTP response
            return parsed_response
        except Exception as e:
            logger.error(f"Assessment failed: {e}")
            return "Server Error", 500

   
