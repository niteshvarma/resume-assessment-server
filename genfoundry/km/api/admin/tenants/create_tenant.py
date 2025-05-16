from flask import jsonify, request
from flask_restful import Resource, current_app
import os
import logging
from flask_jwt_extended import jwt_required
from genfoundry.middleware import role_required

from genfoundry.km.api.admin.tenants.tenant import TenantManager

class CreateTenantRunner(Resource):

    def __init__(self):
        mongo_uri = current_app.config.get('MONGO_URI') # Connection to MongoDB
        mongo_db = current_app.config.get('MONGO_DB')  # Database 
        tenant_collection = current_app.config.get('MONGO_TENANT_COLLECTION')
        self.tenant_mgr = TenantManager(mongo_uri, mongo_db, tenant_collection)

    @jwt_required()  # Ensure the user is authenticated via JWT token
    @role_required(["superadmin"])
    def post(self):
        data = request.get_json()
        tenant_name = data.get("tenantName")
        if not tenant_name:
            return {"error": "Tenant name is required"}, 400
        tenant_id = self.tenant_mgr.add_tenant(tenant_name)
        return {"id": tenant_id, "name": tenant_name}, 201
