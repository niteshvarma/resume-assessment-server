from langchain_openai import ChatOpenAI
from flask_restful import Resource, current_app
from flask import request, jsonify, Response, g
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os
from genfoundry.km.query.helper.filter_extractor import FilterExtractor
from genfoundry.km.query.processors.processor_pipeline import FilterProcessorPipeline
from genfoundry.km.query.processors.processor_registry import build_processor_pipeline

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class FilterExtractorRunner(Resource):

    def __init__(self, llm=None) -> None:
        logging.debug("Inside FilterExtractorRunner.__init__()")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        #if llm is None:
        #    llm = ChatOpenAI(
        #        model_name=current_app.config['LLM_MODEL'], 
        #        temperature=0, 
        #        api_key=current_app.config['OPENAI_API_KEY']
        #    )
        #self.filter_extractor = FilterExtractor(llm=llm)
        PROCESSORS = ["BaseFilterProcessor", "GeoExpansionProcessor"]
        self.filter_processor_pipeline = build_processor_pipeline(PROCESSORS)
 
    @jwt_required()  # Ensure the user is authenticated via JWT token
    def post(self):
        user_id = get_jwt_identity()
        if not user_id:
            return {"error": "Unauthorized"}, 401

        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return {"error": "The 'question' field is required."}, 400

        try:
            logging.debug(f"[User {user_id}] Extracting filters for question: {question}")
            #extracted_filters = self.filter_extractor.extract(question)
            extracted_filters = self.filter_processor_pipeline.run(question)
            extracted_filters.pop("question", None)  # remove question if present
            final_filters = extracted_filters.get("filters", {})
            logging.debug(f"[FilterExtractorRunner] Final extracted filters: {final_filters}")

            if not final_filters:
                logging.info(f"[User {user_id}] No filters extracted from question.")
                return {}, 204  # No Content

            logging.debug(f"Type of extracted_filters: {type(final_filters)}")
            return final_filters, 200

        except Exception as e:
            logging.exception(f"[User {user_id}] Unexpected error during filter extraction.")
            return {"error": "Internal server error"}, 500
