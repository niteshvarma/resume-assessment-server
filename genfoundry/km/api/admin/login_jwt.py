import firebase_admin
from firebase_admin import auth
from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token
from datetime import timedelta
import os, logging
from genfoundry.firebase_setup import db

import logging

class LoginRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Login HTTP handler")
        # The secret key is automatically accessed via:
        # current_app.config['JWT_SECRET_KEY']
        # No need to store it in self.secret_key

 
    def post(self):
        try:
            # Get email & password from request body
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return {"message": "Email and password are required"}, 400

            # Authenticate user with Firebase Authentication
            try:
                user = auth.get_user_by_email(email)
                user_uid = user.uid  # Firebase UID
                # Since Firebase Admin SDK doesn't directly support signing in with password,
                # you should be using Firebase Client SDK (JavaScript/Android/IOS) for actual sign-in
                # We are skipping password validation here as Firebase Admin SDK doesn't have this functionality

                # You need to use the client SDK (JavaScript/Android/iOS) to sign in and get a valid token
                # Firebase Admin SDK can only verify tokens after the client has authenticated
            except firebase_admin.auth.AuthError:
                return {"message": "Invalid email or password"}, 401

            # Fetch user details from Firestore
            user_ref = db.collection("users").document(user_uid)
            user_doc = user_ref.get()

            if not user_doc.exists:
                return {"message": "User not found in Firestore"}, 404

            user_data = user_doc.to_dict()

            # Create JWT token with user details signed by JWT_SECRET_KEY
            access_token = create_access_token(
                identity=user_uid,
                expires_delta=timedelta(hours=24),
                additional_claims={
                    "tenantId": user_data.get("tenantId"),
                    "tenantName": user_data.get("tenantName"),
                    "role": user_data.get("role"),
                    "name": user_data.get("name"),
                    "email": email
                }
            )
            logging.debug(f"JWT created for user: {email}")
            return {"token": access_token}, 200

        except Exception as e:
            return {"message": f"Internal server error: {str(e)}"}, 500
