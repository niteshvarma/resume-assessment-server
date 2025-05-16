import os
import uuid
import logging
import shutil

from genfoundry.km.preprocess.resume_transformer import ResumeStandardizer
from genfoundry.km.preprocess.pymupdf_doc_parser import PyMuPDFDocumentParser
from genfoundry.km.persist.vector_db_proxy import PineconeVectorizer
from genfoundry.km.persist.mongo_proxy import MongoProxy
from langchain_openai import ChatOpenAI
from genfoundry.config import Config



"""
 ┌────────────────────────────────────────────┐
 │                 config.py                   │
 │  - get_redis_config_dict()                  │
 │  - Defines Redis settings                   │
 └────────────────────────────────────────────┘
                ↓                ↓
    (called from)          (called from)
                ↓                ↓
 ┌────────────────────────┐    ┌──────────────────────────────┐
 │      celery_app.py      │   │   ResumeTaskProcessor class  │
 │  - make_celery()        │   │  - Initializes Redis client  │
 │  - celery_app = make... │   │  - Uses get_redis_config_dict│
 └────────────────────────┘    └──────────────────────────────┘
                ↓
        (Celery Worker runs)
                ↓
 ┌──────────────────────────────────────────────┐
 │               Redis Server                    │
 │  - Message broker for Celery                  │
 │  - Cache for ResumeTaskProcessor              │
 └──────────────────────────────────────────────┘
                ↓
       (background tasks processed)

"""
logger = logging.getLogger(__name__)

class ResumeTaskProcessor:
    def __init__(self, llm_model=None, openai_api_key=None, langchain_api_key=None, pinecone_api_key=None):
        logging.debug("Initializing ResumeTaskProcessor...")

        #redis_config_dict = get_redis_config_dict()
        #api_config_key_dict = get_api_key_config()
        #llm_config_dict = get_llm_config()
        
        # self.redis_client = redis.Redis(
        #     host=redis_config_dict['REDIS_HOST'],
        #     port=int(redis_config_dict['REDIS_PORT']),
        #     password=redis_config_dict.get('REDIS_PASSWORD'),
        #     ssl=redis_config_dict.get('REDIS_SSL', True),
        #     decode_responses=True  # (optional, but often useful if you want str instead of bytes)
        # )
        if not llm_model:
            llm_model = Config.LLM_MODEL
        else:
            llm_model = llm_model

        if not openai_api_key:
            openai_api_key = Config.OPENAI_API_KEY
        else:
            openai_api_key = openai_api_key
        
        if not langchain_api_key:
            langchain_api_key = Config.LANGCHAIN_API_KEY
        else:
            langchain_api_key = langchain_api_key
        
        if not pinecone_api_key:
            pinecone_api_key = Config.PINECONE_API_KEY
        else:
            pinecone_api_key = pinecone_api_key


        self.standardizer = ResumeStandardizer(
            openai_api_key=openai_api_key,
            langchain_api_key=langchain_api_key,
            llm_model=llm_model
        )
        self.doc_parser = PyMuPDFDocumentParser()
        self.vectorizer = PineconeVectorizer()
        self.mongo_proxy = MongoProxy()

        self.llm = ChatOpenAI(
            model_name=llm_model,
            temperature=0,
            api_key=openai_api_key
        )

    def process_task(self, resume_filepath, tenant_id):
        tmp_dir = None
        try:
            logger.debug(f"Processing resume for tenant: {tenant_id}")
            
            # Parse the uploaded document
            resume_string = self.doc_parser.parse_document(resume_filepath)

            response = self.standardizer.standardize(resume_string, "markdown")
            if not response or "error" in response:
                raise Exception(response.get("error", "Unknown error during standardization"))

            resume_id = f"Doc:{uuid.uuid4()}"
            standardized_resume = response.get("standardized_resume", {})
            #logger.debug(f"====>ResumeTaskProcessor: Standardized Resume: \n{standardized_resume}")
            metadata = response.get("metadata", {})

            # Save into MongoDB
            self.mongo_proxy.insert_resume(resume_id, standardized_resume, tenant_id)

            # Save into Vector DB
            self.vectorizer.vectorize_and_store_text_resume(resume_id, resume_string, metadata, tenant_id)

            return {
                "resume_id": resume_id,
                "message": "Resume processed successfully",
                "standardized_resume": standardized_resume,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"Error in ResumeTaskProcessor: {e}")
            return {"error": str(e)}

        finally:
            # Clean up the uploaded file
            if resume_filepath and os.path.exists(resume_filepath):
                try:
                    os.remove(resume_filepath)
                    logger.debug(f"Temporary file {resume_filepath} deleted.")
                    
                    # Clean the temp dir if empty
                    tmp_dir = os.path.dirname(resume_filepath)
                    if tmp_dir and os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
                        shutil.rmtree(tmp_dir)
                        logger.debug(f"Temporary directory {tmp_dir} deleted.")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary files: {cleanup_error}")
