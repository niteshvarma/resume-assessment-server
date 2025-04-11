# Description: This file contains the implementation of the ResumeRetrieverRunner class which is responsible for retrieving the resume from the database. The class inherits from the Resource class of the Flask-RESTful library and implements the get method to handle HTTP GET requests. The get method retrieves the resume ID from the query parameters, checks if the resume ID is provided, and then calls the rag_query function to retrieve the resume from the database. If successful, the method returns the retrieved resume as a JSON response. If an error occurs during the retrieval process, the method returns an error message with the corresponding HTTP status code.
from flask import request, jsonify, g
from flask_restful import Resource, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os
import re

from genfoundry.km.persist.mongo_proxy import MongoProxy

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class ResumeRetrieverRunner(Resource):

    def __init__(self) -> None:
      logging.debug("Inside ResumeRetrieverRunner instance init")
      os.environ["MONGO_URI"] = current_app.config['MONGO_URI']
      os.environ["MONGO_DB"] = current_app.config['MONGO_DB']
      os.environ["MONGO_COLLECTION"] = current_app.config['MONGO_COLLECTION']
      self.mongo_proxy = MongoProxy()

      # Initialize MongoProxy

    @jwt_required()  # Ensure the user is authenticated via JWT token
    def get(self):
        # Get the current user identity from the JWT token
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"error": "Tenant ID is required"}), 400
        
        logging.debug("Inside Summarizer get method")
        # Retrieve query parameters
        resume_id = request.args.get('ID')
        logging.debug("resume_id = " + resume_id)
         #question = request.args.get('question')

        # Check if both file_id and question are provided
        if not resume_id:
            return jsonify({"error": "file_id parameter is required"}), 400


        # retrieve resume from database
        try:
            answer = self.mongo_proxy.get_resume(tenant_id, resume_id)
            answer = self.clean_markdown_content(answer)
            logging.debug("Answer: " + answer)
            return jsonify({"AIResponse": answer})
        except Exception as e:
            logging.error(f"ResumeRetrieverRunner.get(): Error retrieving resume: {str(e)}")
            return jsonify({"error": str(e)}), 500
        

    def clean_markdown_content(self, md_content: str) -> str:
        """Sanitize and clean markdown content before sending to frontend."""
        if not md_content:
            return "No details available."

        # Remove surrounding quotes if present
        md_content = md_content.strip().strip('"')

        # Convert escaped newlines into actual newlines
        md_content = md_content.replace('\\n', '\n')

        # Convert escaped double quotes
        md_content = md_content.replace('\\"', '"')

        # Handle Unicode escape sequences (like emojis)
        md_content = md_content.encode().decode('unicode_escape')

        return md_content

