# genfoundry/config.py

import os

class Config:
    LANGCHAIN_TRACING_V2 = "true"
    LANGCHAIN_ENDPOINT = 'https://api.smith.langchain.com'
    LANGCHAIN_API_KEY = ""
    OPENAI_API_KEY = "sk-"
    TAVILY_API_KEY = "tvly-"
    PINECONE_API_KEY = ""
    ANTHROPIC_API_KEY = ""
    project_name = "pt-virtual-sparrow-50"
    PINECONE_INDEX = "default"
    PINECONE_NAMESPACE = "genfoundry_resume_ai"

    #LLM_MODEL = "gpt-3.5-turbo"
    #LLM_MODEL ="gpt-3.5-turbo-16k-0613"
    LLM_MODEL =  "gpt-4o-mini"
    #LLM_MODEL = "gpt-4o"
    CHUNK_SIZE = "700"
    CHUNK_OVERLAP = "50"

    TEXT_EMBEDDING_MODEL = "text-embedding-ada-002"

    MONGO_DB_PASSWORD = ""
    MONGO_URI = ""
    MONGO_DB = "DocumentTracker"
    MONGO_COLLECTION = "Resumes"
    MONGO_TENANT_COLLECTION = "Tenants"

    REDIS_HOST = "deep-possum-14201.upstash.io"
    REDIS_PORT = 6379
    REDIS_PASSWORD = ""
    REDIS_SSL = True
    ssl_cert_reqs = 'required'  # Ensure SSL certificate validation
    ssl_ca_certs = None  # If you need a CA certificate, add it here


    FIREBASE_API_KEY = ""

    LLAMA_CLOUD_API_KEY = "llx-"

    CORS_ALLOWED_ORIGIN = "https://recruitr.genfoundry.ca"
    
    #RESUME_DETAILS_POPUP_URL = "https://api.recruitr.genfoundry.ca/resumedetails"
    RESUME_DETAILS_POPUP_URL = "http://localhost:5001/resumedetails"

    JWT_SECRET_KEY = ""

    JWT_ALGORITHM = "HS256"

    SIMILARITY_CUTOFF = 0.7

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# You can add more specific environment configurations if needed

# Dictionary to map environment names to configuration classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}

def get_redis_config_dict():
    """Returns redis config as a dictionary."""
    return {
        'REDIS_HOST': Config.REDIS_HOST,
        'REDIS_PORT': Config.REDIS_PORT,
        'REDIS_PASSWORD': Config.REDIS_PASSWORD,
        'REDIS_SSL': Config.REDIS_SSL,
        'REDIS_SSL_CERT_REQS': Config.ssl_cert_reqs,
        'REDIS_SSL_CA_CERTS': Config.ssl_ca_certs
    }

def get_api_key_config():
    """Returns the configuration for API Keys."""
    return {
        'LANGCHAIN_API_KEY': Config.LANGCHAIN_API_KEY,
        'OPENAI_API_KEY': Config.OPENAI_API_KEY,
        'TAVILY_API_KEY': Config.TAVILY_API_KEY,
        'PINECONE_API_KEY': Config.PINECONE_API_KEY
    }

def get_mongo_config():
    """Returns MongoDB config as a dictionary."""
    return {
        'MONGO_URI': Config.MONGO_URI,
        'MONGO_DB': Config.MONGO_DB,
        'MONGO_COLLECTION': Config.MONGO_COLLECTION,
        'MONGO_TENANT_COLLECTION': Config.MONGO_TENANT_COLLECTION
    }

def get_llm_config():
    """Returns LLM config as a dictionary."""
    return {
        'LLM_MODEL': Config.LLM_MODEL,
        'CHUNK_SIZE': Config.CHUNK_SIZE,
        'CHUNK_OVERLAP': Config.CHUNK_OVERLAP
    }
