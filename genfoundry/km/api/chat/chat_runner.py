from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

from flask_restful import Resource, current_app
from flask import request, jsonify, Response
import logging
import os
from genfoundry.km.query.search import ResumeSearcher


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
 
    def post(self):
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
            logging.debug("Running search with question.")
            logging.debug(f"Question: {question}")
            logging.debug(f"Namespace: {os.getenv('PINECONE_NAMESPACE')}")
            ai_response = searcher.search(os.getenv("PINECONE_NAMESPACE"), question)
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
