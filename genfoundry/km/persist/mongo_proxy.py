from pymongo import MongoClient
import logging, os, json, re
from genfoundry.config import Config

logger = logging.getLogger(__name__)

class MongoProxy():

    def __init__(self) -> None:
      logger.debug("Inside MongoProxy instance init")
      mongo_uri = Config.MONGO_URI
      mongo_db = Config.MONGO_DB
      #mongo_collection = Config.MONGO_COLLECTION
      self.client = MongoClient(mongo_uri) # Connection to MongoDB
      self.db = self.client[mongo_db]  # Database 
      #logging.debug(f"Connected to MongoDB database: {mongo_db}, collection: {mongo_collection}")
      #self.collection = self.db[os.getenv('MONGO_COLLECTION')]  # Collection name

    def insert_resume(self, resume_id, resume_json, tenant_id):
        # Check if a document with the same file_name exists in the collection
        coll = self.get_tenant_resume_collection(tenant_id)
        #existing_document = self.collection.find_one({"doc_id": resume_id})
        existing_document = coll.find_one({"doc_id": resume_id})

        if existing_document:
            logger.debug(f"Document with document ID '{resume_id}' already exists. Skipping insertion.")
        else:
            # Proceed to insert the file's metadata since it doesn't already exist
            resume_str = json.dumps(resume_json)
            resume_doc = {
                "_id": resume_id,
                "content": resume_str
            }
            coll.insert_one(resume_doc)
            logger.debug(f"Successfully inserted resume with id: {resume_id}")


    def delete_resume(self, resume_id, tenant_id):
        # Define the filter based on file_id
        #filter = {"namespace": namespace, "_id": resume_id}
        filter = {"_id": resume_id}

        # Attempt to delete the document
        #result = self.collection.delete_one(filter)
        result = self.get_tenant_resume_collection(tenant_id).delete_one(filter)
        if result.deleted_count == 1:
            logger.debug(f"Successfully deleted document with file_id: {resume_id}")
        else:
            logger.debug(f"No document found with file_id: {resume_id}")

    def get_resume(self, tenant_id, resume_id):
        # Define the filter based on file_id
        filter = {"_id": resume_id}
        
        # Attempt to retrieve the document
        #result = self.collection.find_one(filter)
        result = self.get_tenant_resume_collection(tenant_id).find_one(filter)
        if result:
            logger.debug(f"Successfully retrieved document with file_id: {resume_id}")
            return result.get("content")
        else:
            logger.debug(f"No document found with file_id: {resume_id}")
            return None
        
    def get_tenant_resume_collection(self, tenant_id):
        """Returns the MongoDB collection for the tenant."""
        collection_name = f"{tenant_id}_Resumes"  # Per-tenant collection
        return self.db[collection_name]
    

    def get_next_resume_id(self, tenant_id: str) -> str:
        """Gets the last valid custom-format resume ID and generates the next one."""
        coll = self.get_tenant_resume_collection(tenant_id)

        # Regex to match strictly: 2 uppercase letters + 5 digits
        regex_pattern = r"^[A-Z]{2}\d{5}$"

        # Find candidates that could match
        candidates = coll.find(
            {"resume_id": {"$regex": regex_pattern}}
        ).sort("resume_id", -1)

        # Find the actual highest valid ID
        for doc in candidates:
            resume_id = doc.get("resume_id", "")
            if re.fullmatch(regex_pattern, resume_id):
                return MongoProxy.generate_next_resume_id(resume_id)

        # No valid ID found
        return MongoProxy.generate_next_resume_id(None)

    @staticmethod
    def generate_next_resume_id(last_id: str) -> str:
        """Generate the next resume ID in the format [AA00000 to ZZ99999]."""
        if not last_id:
            return "AA00000"

        try:
            prefix, number = last_id[:2], int(last_id[2:])
        except ValueError:
            raise ValueError(f"Invalid resume ID format: {last_id}")

        number += 1

        if number > 99999:
            # Increment prefix
            first_char, second_char = prefix
            if second_char == 'Z':
                if first_char == 'Z':
                    raise ValueError("Resume ID space exhausted.")
                first_char = chr(ord(first_char) + 1)
                second_char = 'A'
            else:
                second_char = chr(ord(second_char) + 1)
            prefix = f"{first_char}{second_char}"
            number = 0

        return f"{prefix}{number:05d}"
