from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.settings import Settings
from llama_index.core.utils import get_tokenizer

def init_llama():
    tokenizer = get_tokenizer()
    Settings.node_parser = SentenceSplitter(tokenizer=tokenizer)
