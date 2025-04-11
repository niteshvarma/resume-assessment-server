from flask import request, jsonify
from flask_restful import Resource
from flask import current_app
from datetime import timedelta
import requests
from firebase_admin import auth
from genfoundry.firebase_setup import db
import logging
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

class ChangePasswordRunner(Resource):
    def __init__(self):
        logging.debug("Initializing ChangePassword HTTP handler")
        self.firebase_api_key = current_app.config.get("FIREBASE_API_KEY")

 
    @jwt_required()  # Ensure the user is authenticated via JWT token
    def post(self):
        # Get the current user identity from the JWT token
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.json
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')

        # Get user from token (Assuming JWT-based authentication)
        #user_id = self.get_user_id_from_token(request)  # Implement token verification

        #if not user_id:
        #    return jsonify({"error": "Unauthorized"}), 401

        try:
            user = auth.get_user(user_id)
            
            # Re-authenticate user (Optional: Check old password in DB)
            if not self.verify_old_password(user.email, old_password):  # Implement this function
                return jsonify({"error": "Incorrect old password"}), 400

            # Update password
            auth.update_user(user_id, password=new_password)

            # Invalidate old JWT and generate a new one (Optional)
            new_token = self.generate_new_jwt(user_id)  # Implement JWT generation

            return {"message": "Password updated successfully", "token": new_token}, 200

        except Exception as e:
            return {"error": str(e)}, 400
    

    def verify_old_password(self, email, old_password):
        """
        Verifies that the provided old_password matches the user's existing password in Firebase.
        
        Returns:
            True if password is valid, False otherwise.
        Raises:
            Exception if something goes wrong.
        """
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api_key}"

        payload = {
            "email": email,
            "password": old_password,
            "returnSecureToken": True
        }

        try:
            response = requests.post(url, json=payload)
            response_data = response.json()

            if response.status_code == 200 and "idToken" in response_data:
                return True
            else:
                print(f"[verify_old_password] Firebase Error: {response_data}")
                return False

        except Exception as e:
            print(f"[verify_old_password] Exception occurred: {str(e)}")
            raise
    
    def get_user_id_from_token(self, request):
        """Extracts and verifies the Firebase ID token from the Authorization header."""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise ValueError('Missing or invalid Authorization header')

        id_token = auth_header.split('Bearer ')[1]

        try:
            # Verify the token using Firebase Admin SDK
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get('uid')
            if not uid:
                raise ValueError('Invalid token: UID not found')
            return uid
        except Exception as e:
            raise ValueError(f'Token verification failed: {str(e)}')
        
    def generate_new_jwt(self, user_id: str) -> str:
        # Retrieve user info from Firestore
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise ValueError("User not found in Firestore")

        user_data = user_doc.to_dict()
        email = user_data.get("email")

        # Create a new JWT with same claims as in /login
        access_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(hours=24),
            additional_claims={
                "tenantId": user_data.get("tenantId"),
                "tenantName": user_data.get("tenantName"),
                "role": user_data.get("role"),
                "name": user_data.get("name"),
                "email": email
            }
        )
        return access_token