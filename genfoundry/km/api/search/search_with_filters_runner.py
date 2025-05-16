from flask import request, jsonify, g, make_response
from flask_restful import Resource, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import os
import json

from genfoundry.km.query.tiered_resume_search import TieredResumeSearcher

class ResumeSearchWithFilterRunner(Resource):

    def __init__(self) -> None:
        logging.debug("Inside ResumeQuery instance init")
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["PINECONE_API_KEY"] = current_app.config['PINECONE_API_KEY']
        os.environ["PINECONE_INDEX"] = current_app.config['PINECONE_INDEX']
        os.environ["PINECONE_NAMESPACE"] = current_app.config['PINECONE_NAMESPACE']
        os.environ["RESUME_DETAILS_POPUP_URL"] = current_app.config['RESUME_DETAILS_POPUP_URL']

        self.similarity_cutoff = float(current_app.config['SIMILARITY_CUTOFF'])

    @jwt_required()  # Ensure the user is authenticated via JWT token
    def post(self):
        user_id = get_jwt_identity()
        logging.debug(f"JWT identity (user_id): {user_id}")
        if not user_id:
            logging.warning("Unauthorized access attempt – no user_id in JWT.")
            return jsonify({"error": "Unauthorized"}), 401

        tenant_id = g.get("tenant_id")
        logging.debug(f"Tenant ID from context: {tenant_id}")
        if not tenant_id:
            logging.error("Missing tenant_id in request context.")
            return jsonify({"error": "Tenant ID is required"}), 400

        try:
            data = request.get_json(force=True)
            logging.debug(f"Request JSON payload: {data}")

            question = data.get("question")
            raw_filters = data.get("filters", [])
            logging.debug(f"Received filters: {raw_filters}")

            if not question:
                logging.warning("Search request missing 'question' field.")
                return jsonify({"error": "Missing required field: 'question'"}), 400

            logging.debug(f"Original filters: {raw_filters}")
            #filters = FilterNormalizer.normalize(raw_filters)
            #logging.debug(f"Normalized filters: {filters}")
            filters = raw_filters
            
            # ✅ Clean up filters before calling search()
            for f in filters:
                if f["name"] == "total_years_of_experience":
                    try:
                        # If it's a string that looks like JSON, parse it
                        if isinstance(f["value"], str):
                            f["value"] = json.loads(f["value"])
                    except json.JSONDecodeError as e:
                        logging.warning(f"Failed to parse range filter: {f['value']} — {e}")

            searcher = TieredResumeSearcher(self.similarity_cutoff)
            logging.debug("Initialized ResumeFilterSemanticSearcher.")
            results = searcher.search(tenant_id=tenant_id, question=question, filter_dict=filters)
            json.dumps({"results": results})
            logging.debug("Search Result:  + %s", json.dumps(results, indent=2))

            response = make_response(jsonify({"results": results}))
            response.headers["Content-Type"] = "application/json"
            return response

        except Exception as e:
            logging.exception("Unexpected error occurred during resume search.")
            return jsonify({"error": str(e)}), 500