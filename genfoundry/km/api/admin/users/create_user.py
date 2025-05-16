from flask import request
from flask_restful import Resource
import firebase_admin
from firebase_admin import auth, firestore
from genfoundry.firebase_setup import db
from genfoundry.middleware import role_required
from flask_jwt_extended import jwt_required, get_jwt_identity

import logging

class CreateUserRunner(Resource):
    def __init__(self):
        logging.debug("Initializing CreateUser HTTP handler")

    @jwt_required()  # Ensure the user is authenticated via JWT token
    @role_required(["admin", "superadmin"])
    def post(self):
        # Get the current user identity from the JWT token
        user_id = get_jwt_identity()
        if not user_id:
            return {"error": "Unauthorized"}, 401
        
        logging.debug("CreateUserRunner ... processing request to create user.")
        try:
            data = request.json
            user_name = data.get("name", "Not_Provided")
            email = data.get('email')
            password = data.get('password')
            role = data.get('role', 'user')  # Default role = "user"
            tenant_name = data.get('tenantName')

            if not email or not password or not tenant_name:
                return {'error': 'Email, password, and tenant name are required'}, 400

            # Step 1: Check if tenant exists
            tenant_query = db.collection('tenants').where('name', '==', tenant_name).limit(1).stream()
            tenant_ref = None
            tenant_id = None

            for tenant in tenant_query:
                tenant_id = tenant.id
                tenant_ref = db.collection('tenants').document(tenant_id)

            if not tenant_id:
                # Step 2: Create new tenant
                tenant_ref = db.collection('tenants').document()  # Firestore auto-ID
                tenant_ref.set({
                    'name': tenant_name,
                    'users': []  # Initialize user list
                })
                tenant_id = tenant_ref.id  # Retrieve auto-generated tenant ID
                logging.debug(f"New tenant created with ID: {tenant_id}")

            # Step 3: Create Firebase Authentication user
            user_record = auth.create_user(
                email=email,
                password=password,
                email_verified=False,
                disabled=False
            )
            user_uid = user_record.uid  # Get the Firebase Auth UID
            logging.debug("New Firebase user successfully created.")

            # Step 4: Store user in Firestore using Firebase Auth UID
            user_ref = db.collection('users').document(user_uid)  # Use Firebase UID as document ID
            user_ref.set({
                'name': user_name,
                'email': email,
                'role': role,
                'tenantId': tenant_id,
                'tenantName': tenant_name
            })
            logging.debug("User successfully stored in Firestore.")

            # Step 5: Add user to tenant’s user list
            tenant_ref.update({"users": firestore.ArrayUnion([user_uid])})

            # Step 6: Send password reset email
            reset_link = auth.generate_password_reset_link(email)
            logging.debug("Password reset link sent successfully.")

            return {
                'message': 'User and tenant linked successfully',
                'userId': user_uid, 
                'tenantId': tenant_id,
                'tenantName': tenant_name
            }, 201

        except Exception as e:
            logging.error(f"Error creating user: {str(e)}")
            return {'error': str(e)}, 500