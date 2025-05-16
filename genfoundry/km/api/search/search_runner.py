from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

from flask_restful import Resource, current_app
from flask import request, jsonify, Response, g
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os
from genfoundry.km.query.search import ResumeSearcher
#from genfoundry.km.query.fusion_search import FusionRetrieverSearcher


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class ResumeQuery(Resource):

    def __init__(self) -> None:
        logging.debug("Inside ResumeQuery instance init")
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["PINECONE_API_KEY"] = current_app.config['PINECONE_API_KEY']
        os.environ["PINECONE_INDEX"] = current_app.config['PINECONE_INDEX']
        os.environ["PINECONE_NAMESPACE"] = current_app.config['PINECONE_NAMESPACE']
        os.environ["RESUME_DETAILS_POPUP_URL"] = current_app.config['RESUME_DETAILS_POPUP_URL']
 
    @jwt_required()  # Ensure the user is authenticated via JWT token
    def post(self):
        # Get the current user identity from the JWT token
        user_id = get_jwt_identity()

        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"error": "Tenant ID is required"}), 400
        
        # Parse JSON data from the request
        data = request.get_json()
        question = data.get('question', '').strip()

        # Validate input
        if not question:
            return jsonify({
                "error": "The 'question' field is required."
            }), 400
        
        try:
            searcher = ResumeSearcher()
            #searcher = FusionRetrieverSearcher()
            logging.debug("Running search with question.")
            logging.debug(f"Question: {question}")
            logging.debug(f"Namespace: {os.getenv('PINECONE_NAMESPACE')}")
            ai_response = searcher.search(tenant_id, question)
            #logging.debug(f"AI Response: {ai_response}")
            # Extract only the text attribute
            """
            answer_text = ""
            if isinstance(ai_response, list):
                ai_response = [node.node.text for node in ai_response]
                logging.debug(f"AI Response: {ai_response}")
                answer_text = " ".join(ai_response)
            logging.debug(f"Answer: {answer_text}")
            return jsonify({"question": question, "answer": answer_text}), 200
            """
            #return Response(ai_response, status=200, mimetype='text/plain')
            logging.debug(f"AI Response: {ai_response}")
            return ai_response
        except Exception as e:
            logging.error(f"Error in ResumeQuery.post(): {str(e)}")
            raise