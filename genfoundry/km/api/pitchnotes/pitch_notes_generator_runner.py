from flask import request, jsonify, g
from flask_restful import Resource, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from langchain_openai import ChatOpenAI
from .pitch_notes_generator_tool import PitchNotesGenerator
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser
import os
import json
import re
import tempfile
import uuid
import unicodedata

class PitchNotesGeneratorRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Pitch Notes Generator HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))
                
        system_message = "You are a helpful recruitment assistant. Please assess the resume and recruiter notes against the  criteria. You may use the tools provided to assist you. The final answer should combine the results of individual tools that are called."
        
        self.parser = PyMuPDFDocumentParser()
        self.pitch_note_generator = PitchNotesGenerator()
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))


    @jwt_required()  # Ensure the user is authenticated via JWT token
    def post(self):        
        user_id = get_jwt_identity()
        logging.debug(f"JWT identity (user_id): {user_id}")
        if not user_id:
            logging.warning("Unauthorized access attempt – no user_id in JWT.")
            return jsonify({"error": "Unauthorized"}), 401

        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"error": "Tenant ID is required"}), 400

       # if 'criteria' not in request.files or 'resume' not in request.files or 'recruiterNotes' not in request.files:
        #     return jsonify({"error": "Resume, recruiter's note and criteria files are required"}), 400

        if 'resume' not in request.files or not request.form.get('criteriaText'):
            return {"error": "Resume (file) and criteria (text) are required"}, 400

        criteria = request.form.get('criteriaText')

        recruiter_notes = request.form.get('recruiterNotesText')
        if not recruiter_notes:
            recruiter_notes = ""
        else:
            recruiter_notes = self.clean_pasted_text(recruiter_notes)

        # Get uploaded files
        #recruiter_note_file = request.files['recruiterNotes']
        resume_file = request.files['resume']
        resume_filename = resume_file.filename

        criteria = request.form.get('criteriaText')
        criteria = self.clean_pasted_text(criteria)
        try:
            tmp_dir = tempfile.mkdtemp()
            unique_filename = f"{tenant_id}_{uuid.uuid4().hex}_{resume_filename}"
            tmp_path = os.path.join(tmp_dir, unique_filename)
            resume_file.save(tmp_path) 
            resume = self.parser.parse_document(tmp_path)
        except Exception as e:
            logging.error(f"Document parsing failed: {e}")
            return jsonify({"error": "Failed to parse uploaded files"}), 500
                
        try:
            question = "Please assess the candidate's information provided in the resume and recruiter's note against the criteria. You may use the tools provided to assist you. The final answer should combine the results of the tools."

            pitch_note_response = self.pitch_note_generator.assess(resume, recruiter_notes, criteria, question)
            if pitch_note_response.startswith("json"):
                pitch_note_response = pitch_note_response[4:].strip()

            # If the response is a JSON string, parse it
            try:
                if isinstance(pitch_note_response, str):
                    pitch_note_response = json.loads(pitch_note_response)
            except json.JSONDecodeError:
                logging.warning("Agent response is not valid JSON. Returning raw response.")

            # Return the parsed JSON as the HTTP response
            return jsonify({"AIResponse": pitch_note_response})
        except Exception as e:
            logging.error(f"Assessment failed: {e}")
            return "Server Error", 500
        

    def clean_pasted_text(self, text: str) -> str:
    # Normalize unicode (e.g., smart quotes to plain quotes)
        text = unicodedata.normalize("NFKD", text)

        # Replace smart quotes and dashes
        replacements = {
            '\u2018': "'", '\u2019': "'",   # Single quotes
            '\u201c': '"', '\u201d': '"',   # Double quotes
            '\u2013': '-', '\u2014': '-',   # Dashes
            '\u00a0': ' ',                  # Non-breaking space
        }

        for bad, good in replacements.items():
            text = text.replace(bad, good)

        # Remove any other non-ASCII characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)

        return text.strip()