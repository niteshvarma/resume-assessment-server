from pymongo import MongoClient
import logging, os, json

class MongoProxy():

    def __init__(self) -> None:
      logging.debug("Inside MongoProxy instance init")
      self.client = MongoClient(os.getenv('MONGO_URI'))
      db = self.client[os.getenv('MONGO_DB')]  # Database 
      self.collection = db[os.getenv('MONGO_COLL')]  # Collection name

    def insert_resume(self, namespace, resume_id, resume_json):
        # Check if a document with the same file_name exists in the collection
        existing_document = self.collection.find_one({"doc_id": resume_id})

        if existing_document:
            logging.debug(f"Document with document ID '{resume_id}' already exists. Skipping insertion.")
        else:
            # Proceed to insert the file's metadata since it doesn't already exist
            resume_str = json.dumps(resume_json)
            resume_doc = {
                "namespace": namespace,
                "_id": resume_id,
                "content": resume_str
            }
            self.collection.insert_one(resume_doc)
            logging.debug(f"Successfully inserted resume with id: {resume_id}")


    def delete_resume(self, namespace, resume_id):
        # Define the filter based on file_id
        filter = {"namespace": namespace, "_id": resume_id}

        # Attempt to delete the document
        result = self.collection.delete_one(filter)
        if result.deleted_count == 1:
            logging.debug(f"Successfully deleted document with file_id: {resume_id}")
        else:
            logging.debug(f"No document found with file_id: {resume_id}")

