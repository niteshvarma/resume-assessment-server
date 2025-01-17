from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from genfoundry.km.preprocess.resume_transformer import ResumeStandardizer
from genfoundry.km.persist.vector_db_proxy import PineconeVectorizer

import os
import json
import uuid

class ResumeDeleteRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Resume Standardizer HTTP handler")
        os.environ["PINECONE_API_KEY"] = current_app.config['PINECONE_API_KEY']
        os.environ["PINECONE_INDEX"] = current_app.config['PINECONE_INDEX']
        os.environ["PINECONE_NAMESPACE"] = current_app.config['PINECONE_NAMESPACE']

        self.vectorizer = PineconeVectorizer()
        
def delete(self, resume_id):
    try:
        # Delete the resume from Pinecone
        self.vectorizer.delete_resume(resume_id)
        logging.debug(f"Resume {resume_id} deleted from Pinecone")
        return jsonify({"message": "Resume deleted successfully"}) 
    except Exception as e:
        logging.error(f"Error deleting resume: {e}")
        return jsonify({"error": "Server Error"}), 500