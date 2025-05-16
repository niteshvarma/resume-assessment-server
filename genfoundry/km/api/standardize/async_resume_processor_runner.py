from flask import request, jsonify, g
from flask_restful import Resource, current_app
from flask_jwt_extended import jwt_required
import logging
import os
import tempfile
import uuid
from celery.result import AsyncResult
from genfoundry.config import get_api_key_config, get_llm_config


from genfoundry.km.api.standardize.celery_resume_processor_task import process_resume  # Import the Celery task

class AsyncResumeStandardizerRunner(Resource):
    def __init__(self):
        logging.debug("Initializing AsyncResumeStandardizerRunner HTTP handler")
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


    @jwt_required()
    def post(self):
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"error": "Tenant ID is required"}), 400

        if 'resume' not in request.files:
            return jsonify({"error": "Resume file is required"}), 400

        resume_file = request.files['resume']
        resume_filename = resume_file.filename

        try:
            # Save to temporary file
            tmp_dir = tempfile.mkdtemp()
            unique_filename = f"{tenant_id}_{uuid.uuid4().hex}_{resume_filename}"
            tmp_path = os.path.join(tmp_dir, unique_filename)

            resume_file.save(tmp_path)

            # Submit async Celery task
            task = process_resume.apply_async(
                args=[tmp_path, tenant_id]
            )

            logging.info(f"Submitted resume processing task. Task ID: {task.id}")

            return {'message': 'Resume submitted successfully.', 'task_id': task.id}, 200

        except Exception as e:
            logging.error(f"Error submitting resume processing task: {e}")
            return {"error": "Server Error"}, 500

    @jwt_required()
    def get(self):
        task_id = request.args.get("task_id")
        if not task_id:
            return {"error": "Task ID is required"}, 400

        try:
            async_result = AsyncResult(task_id)
            logging.info(f"Checking Task ID: {task_id}, State: {async_result.state}, Info: {async_result.info}")

            if async_result.state in ['PENDING', 'STARTED', 'RETRY']:
                return {"status": "processing"}, 202

            elif async_result.state == 'SUCCESS':
                try:
                    result = async_result.result  # Now directly contains resume_id, standardized_resume, etc.
                    logging.debug(f"Standardized Resume: {result.get('standardized_resume')}")

                    return {
                        "status": "completed",
                        "resume_id": result.get("resume_id"),
                        "message": result.get("message"),
                        "standardized_resume": result.get("standardized_resume"),
                        "metadata": result.get("metadata")
                    }, 200

                except Exception as e:
                    logging.error(f"Error accessing task result for {task_id}: {e}")
                    return {
                        "status": "failed",
                        "error": "Error retrieving task result"
                    }, 500

            elif async_result.state == 'FAILURE':
                return {
                    "status": "failed",
                    "error": str(async_result.info)
                }, 500

            else:
                return {"status": "unknown"}, 500

        except Exception as e:
            logging.error(f"Error fetching task result for {task_id}: {e}")
            return {"error": "Server Error"}, 500
