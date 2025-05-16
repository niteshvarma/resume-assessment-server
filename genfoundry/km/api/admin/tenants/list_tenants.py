from flask import jsonify, request
from flask_restful import Resource, current_app
import os
import logging
from flask_jwt_extended import jwt_required
from genfoundry.middleware import role_required

from genfoundry.km.api.admin.tenants.tenant import TenantManager

class ListTenantsRunner(Resource):

    def __init__(self):
        logging.debug("Inside ListTenantsRunner.__init__()")

    @jwt_required()  # Ensure the user is authenticated via JWT token
    @role_required(["superadmin"])
    def get(self):
        logging.debug("Inside ListTenantsRunner.get()")
        mongo_uri = current_app.config.get('MONGO_URI') # Connection to MongoDB
        mongo_db = current_app.config.get('MONGO_DB')  # Database 
        tenant_collection = current_app.config.get('MONGO_TENANT_COLLECTION')
        tenant_mgr = TenantManager(mongo_uri, mongo_db, tenant_collection)

        tenants = tenant_mgr.get_all_tenants()
        return tenants, 200