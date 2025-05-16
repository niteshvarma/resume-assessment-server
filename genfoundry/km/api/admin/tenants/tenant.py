from pymongo import MongoClient
import logging

class TenantManager:
    def __init__(self, uri: str, db: str, coll: str):
        client = MongoClient(uri)
        db = client[db]

        self.tenants_collection = db[coll]

    def add_tenant(self, name: str):
        tenant = {"tenantName": name}
        result = self.tenants_collection.insert_one(tenant)
        return str(result.inserted_id)

    def get_all_tenants(self):
        logging.debug("Entering get_all_tenants() method.")
        # Ensure the cursor is fully evaluated and not passed directly
        tenants_cursor = self.tenants_collection.find({}, {"tenantName": 1, "_id": 0})

        # Log the raw data from the MongoDB query
        tenants = list(tenants_cursor)  # Convert cursor to list
        logging.debug(f"Raw tenants data: {tenants}")
        
        # Extract tenant names from the list
        tenant_names = [tenant["tenantName"] for tenant in tenants]

        # Return the tenant names as a JSON response
        return tenant_names
