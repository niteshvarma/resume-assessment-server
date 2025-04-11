from pymongo import MongoClient
import logging, os, json

class MongoProxy():

    def __init__(self) -> None:
      logging.debug("Inside MongoProxy instance init")
      self.client = MongoClient(os.getenv('MONGO_URI')) # Connection to MongoDB
      self.db = self.client[os.getenv('MONGO_DB')]  # Database 
      logging.debug(f"Connected to MongoDB database: {os.getenv('MONGO_DB')}, collection: {os.getenv('MONGO_COLLECTION')}")
      #self.collection = self.db[os.getenv('MONGO_COLLECTION')]  # Collection name

    def insert_resume(self, resume_id, resume_json, tenant_id):
        # Check if a document with the same file_name exists in the collection
        coll = self.get_tenant_resume_collection(tenant_id)
        #existing_document = self.collection.find_one({"doc_id": resume_id})
        existing_document = coll.find_one({"doc_id": resume_id})

        if existing_document:
            logging.debug(f"Document with document ID '{resume_id}' already exists. Skipping insertion.")
        else:
            # Proceed to insert the file's metadata since it doesn't already exist
            resume_str = json.dumps(resume_json)
            resume_doc = {
                "_id": resume_id,
                "content": resume_str
            }
            coll.insert_one(resume_doc)
            logging.debug(f"Successfully inserted resume with id: {resume_id}")


    def delete_resume(self, resume_id, tenant_id):
        # Define the filter based on file_id
        #filter = {"namespace": namespace, "_id": resume_id}
        filter = {"_id": resume_id}

        # Attempt to delete the document
        #result = self.collection.delete_one(filter)
        result = self.get_tenant_resume_collection(tenant_id).delete_one(filter)
        if result.deleted_count == 1:
            logging.debug(f"Successfully deleted document with file_id: {resume_id}")
        else:
            logging.debug(f"No document found with file_id: {resume_id}")

    def get_resume(self, tenant_id, resume_id):
        # Define the filter based on file_id
        filter = {"_id": resume_id}
        
        # Attempt to retrieve the document
        #result = self.collection.find_one(filter)
        result = self.get_tenant_resume_collection(tenant_id).find_one(filter)
        if result:
            logging.debug(f"Successfully retrieved document with file_id: {resume_id}")
            return result.get("content")
        else:
            logging.debug(f"No document found with file_id: {resume_id}")
            return None
        
    def get_tenant_resume_collection(self, tenant_id):
        """Returns the MongoDB collection for the tenant."""
        collection_name = f"{tenant_id}_Resumes"  # Per-tenant collection
        return self.db[collection_name]


