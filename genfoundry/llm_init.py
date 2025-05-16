from genfoundry.config import get_api_key_config, get_llm_config
import os

def init_llama():
    api_config_key_dict = get_api_key_config()
    llm_config_dict = get_llm_config()
    os.environ["OPENAI_API_KEY"] = api_config_key_dict['OPENAI_API_KEY']
    os.environ["LANGCHAIN_API_KEY"] = api_config_key_dict['LANGCHAIN_API_KEY']
    os.environ["LLM_MODEL"] = llm_config_dict['LLM_MODEL']
    
