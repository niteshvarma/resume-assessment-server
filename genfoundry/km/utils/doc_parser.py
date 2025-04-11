from llama_parse import LlamaParse
from llama_index.core import SimpleDirectoryReader
import logging
import tempfile
import os
import nest_asyncio

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class DocumentParser():
    def __init__(self, llama_cloud_api_key, parsingInstruction=None) -> None:
        logging.debug("Inside DocumentParser instance init")
        self.parser = LlamaParse(
                api_key=llama_cloud_api_key,
                result_type= "text",
                parsingInstruction=parsingInstruction,
                verbose=True)
        
        nest_asyncio.apply()

    def parse_document(self, file):
        file_path = None  # Initialize file_path to handle scope issues

        try:
            logging.debug(f"Inside parse_document method. Parsing document: {file}")
            
            # Save the file to a temporary location
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, file.filename)
                
            # Save the file to the temporary location with its original name
            with open(file_path, "wb") as temp_file:
                file.save(temp_file)
                
            logging.debug(f"======> Saved {file.filename} to local disk at: {file_path}")
            assert os.path.exists(file_path), f"File {file_path} not found."
            
            # Read and parse the document
            logging.debug(f"Loading data into LlamaParser from {file_path}")
            documents = self.parser.load_data(file_path)
            logging.debug(f"=======> Document parsed by LlamaParser:{str(len(documents))}")

            # Extract the text from the first document
            docString = documents[0].text
            logging.debug(f"Document parsed successfully. Content: {docString[:5000]}...")  # Log a snippet
            return docString

        except Exception as e:
            logging.error(f"Error parsing document: {e}")
            return None

        finally:
            # Ensure the temporary file is removed
            if file_path and os.path.exists(file_path):
                logging.debug(f"Removing temporary file: {file_path}")
                os.remove(file_path)
