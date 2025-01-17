# genfoundry/config.py

import os

class Config:
    LANGCHAIN_TRACING_V2 = "true"
    LANGCHAIN_ENDPOINT = 'https://api.smith.langchain.com'
    LANGCHAIN_API_KEY = "ls__6399eb5bb18e49a69f243e9d022f9890"
    OPENAI_API_KEY = "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"
    TAVILY_API_KEY = "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"
    PINECONE_API_KEY = "257c8fda-70fd-4435-ac9f-5a03027a2846"
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

    MONGO_DB_PASSWORD = "pvvrCbW8A7BIW8AS"
    # MongoDB URI template: "mongodb+srv://admin:<db_password>@genfoundrycluster.qjygr.mongodb.net/?retryWrites=true&w=majority&appName=GenFoundryCluster"
    MONGO_URI = "mongodb+srv://admin:pvvrCbW8A7BIW8AS@genfoundrycluster.qjygr.mongodb.net/?retryWrites=true&w=majority&appName=GenFoundryCluster&tls=true&connectTimeoutMS=30000&socketTimeoutMS=30000"
    MONGO_DB = "DocumentTracker"
    MONGO_COLL = "UploadedDocs"

    LLAMA_CLOUD_API_KEY = "llx-le3jKayUMdnLTwBu1WPZ1RiNIIxueP7aeLEMKQ7CJabtNwfn"

    CORS_ALLOWED_ORIGIN = "http://ec2-3-84-54-171.compute-1.amazonaws.com"
    
    RISK_EXPERT_ANSWER_TEMPLATE = (
        "You are a Risk Audit expert and are advising other auditors. \n"
        "You should use a professional tone and provide comprehensive answers and do not leave out relevant points.\n"
        "Answer the question based only on the given context. If you do not know the answer, say that you do not know.\n"
        "Step 1. Find the relevant answer based on the DOCUMENT \n"
        "Step 2. Format in a readable, user-friendly markdown format.\n"
        "\n"
        "DOCUMENT:\n"
        "--------\n"
        "{context}\n"
        "\n"
        "Question:\n"
        "---------\n"
        "{question}"
    )

    GENERAL_ANSWER_TEMPLATE = (
        "You are an expert and are providing relevant answers to question asked based on the DOCUMENT provided in the context. \n"
        "You should use a professional tone and provide comprehensive answers and do not leave out relevant points.\n"
        "Answer the question based only on the given context. If you do not know the answer, say that you do not know.\n"
        "Step 1. Find the relevant answer based on the DOCUMENT \n"
        "Step 2. Format in a readable, user-friendly markdown format or paragraph as appropriate.\n"
        "\n"
        "DOCUMENT:\n"
        "--------\n"
        "{context}\n"
        "\n"
        "Question:\n"
        "---------\n"
        "{question}"
    )

    WVE_ANSWER_TEMPLATE = (
        "You are an expert and are providing relevant answers to question asked based on the DOCUMENT provided in the context. \n"
        "You should use a professional tone and provide comprehensive answers and do not leave out relevant points.\n"
        "Answer the question based only on the given context. If you do not know the answer, say that you do not know.\n"
        "Step 1. Find the relevant answer based on the DOCUMENT \n"
        "Step 2. Format in a readable, user-friendly markdown format or paragraph as appropriate.\n"
        "\n"
        "DOCUMENT:\n"
        "--------\n"
        "{context}\n"
        "\n"
        "Question:\n"
        "---------\n"
        "{question}"
    )

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
