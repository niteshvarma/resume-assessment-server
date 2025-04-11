from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from langchain_openai import ChatOpenAI
from .pitch_notes_generator_tool import PitchNotesGenerator
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser
import os
import json

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


    def post(self):        
        if 'criteria' not in request.files or 'resume' not in request.files or 'recruiterNotes' not in request.files:
            return jsonify({"error": "Resume, recruiter's note and criteria files are required"}), 400

        # Get uploaded files
        recruiter_note_file = request.files['recruiterNotes']
        resume_file = request.files['resume']
        criteria_file = request.files['criteria']

        try:
            recruiter_note = self.parser.parse_document(recruiter_note_file)
            resume = self.parser.parse_document(resume_file)
            criteria = self.parser.parse_document(criteria_file)

            if not recruiter_note or not resume or not criteria:
                return jsonify({"error": "Parsed content cannot be empty"}), 400
        except Exception as e:
            logging.error(f"Document parsing failed: {e}")
            return jsonify({"error": "Failed to parse uploaded files"}), 500
                
        try:
            question = "Please assess the candidate's information provided in the resume and recruiter's note against the criteria. You may use the tools provided to assist you. The final answer should combine the results of the tools."

            pitch_note_response = self.pitch_note_generator.assess(resume, recruiter_note, criteria, question)
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
        

