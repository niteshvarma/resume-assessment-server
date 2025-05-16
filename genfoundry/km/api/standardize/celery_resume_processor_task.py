# resume_tasks.py
from genfoundry.celery_app import celery_app
from genfoundry.km.api.standardize.resume_processing_task import ResumeTaskProcessor
import logging
from genfoundry.config import Config

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_resume(self, resume_filepath, tenant_id):
    logger.debug(f"Processing resume file: {resume_filepath} for tenant: {tenant_id}")
    openai_api_key = Config.OPENAI_API_KEY
    llm_model = Config.LLM_MODEL
    langchain_api_key = Config.LANGCHAIN_API_KEY
    pinecone_api_key = Config.PINECONE_API_KEY
    processor = ResumeTaskProcessor(llm_model=llm_model, openai_api_key=openai_api_key, langchain_api_key=langchain_api_key, pinecone_api_key=pinecone_api_key)
    
    try:
        logger.debug(f"Starting task for tenant: {tenant_id}")
        self.update_state(state='STARTED', meta={'status': 'Task started, processing resume.'})

        self.update_state(state='PROCESSING', meta={'status': 'Processing resume content.'})
        result = processor.process_task(resume_filepath, tenant_id)

        # Flatten result with top-level status and message
        result["status"] = "success"
        result["message"] = result.get("message", "Resume processed successfully")

        self.update_state(state='SUCCESS', meta=result)
        return result

    except Exception as e:
        logger.error(f"Error processing resume for tenant {tenant_id}: {e}")
        self.update_state(state='FAILURE', meta={'status': 'Error during task processing', 'exc': str(e)})
        raise









