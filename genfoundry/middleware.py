from flask import request, g, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
import logging
from datetime import datetime
from functools import wraps

def jwt_authentication():
    """
    Middleware function to verify JWT and extract tenant details
    """
    """
    Middleware to authenticate JWT on every request except /login
    """
    # Skip JWT authentication for login route
    if request.path == "/login":
        return
    if request.path == "/research/company":
        return

    try:
        verify_jwt_in_request()  # Ensure request has a valid JWT
        claims = get_jwt()  # Extract JWT claims

        # Attach tenant and user details to Flask's global context (g)
        g.tenant_id = claims.get("tenantId")
        g.tenant_name = claims.get("tenantName")
        g.user_id = claims.get("sub")  # The user UID from Firebase Auth
        g.user_email = claims.get("email")
        g.role = claims.get("role")

        if not g.tenant_id or not g.tenant_name:
            return jsonify({"message": "Unauthorized: Missing tenant info"}), 403

    except Exception as e:
        logging.error(f"JWT Authentication Error: {str(e)}")
        return jsonify({"message": "Invalid token"}), 401


def role_required(roles):
    """
    Decorator to enforce role-based access control (RBAC)
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if g.role not in roles:
                return jsonify({"message": "Access denied: Insufficient privileges"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper


def log_api_usage(response):
    """
    Middleware function to log API usage per tenant.
    """
    try:
        logging.info(
            f"API Access - User: {g.user_email}, Tenant: {g.tenant_name}, Endpoint: {request.path}, Time: {datetime.utcnow()}"
        )
    except Exception as e:
        logging.error(f"Logging Error: {str(e)}")
    
    return response
