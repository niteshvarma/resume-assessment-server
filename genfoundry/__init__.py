from flask import Flask, request, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from genfoundry.config import config
from genfoundry.firebase_setup import db  # Import Firestore setup#from app.api.user import User
from genfoundry.middleware import jwt_authentication, log_api_usage
import logging
from genfoundry.llama_init import init_llama
from genfoundry.llama_init import init_llama
from flask_caching import Cache

cache = Cache()


def create_app(config_name):
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration based on the environment
    try:
        app.config.from_object(config[config_name])
    #    print(f"Loaded config: {config_name}")
    except KeyError:
        raise KeyError(f"Configuration '{config_name}' not found in config.py")

    # --- Logging setup ---
    # Remove any existing handlers that Flask might have added
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure fresh logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),                    # log to console
            logging.FileHandler('app.log', mode='a')    # log to file
        ]
    )

    logging.debug("✅ Logging is configured and working.")

    # Disable CORS before deploying on Cloud - the below is for local testing
    #CORS(app, resources={r"/*": {"origins": app.config['CORS_ALLOWED_ORIGIN']}})
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    # Enable CORS for all routes and origins (for development purposes)
    
    # ✅ Explicitly handle OPTIONS requests globally - for local testing
    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = jsonify({"message": "CORS preflight successful"})
            response.headers.add("Access-Control-Allow-Origin", "https://localhost:4200")
            response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 200  # ✅ Ensure HTTP 200 OK for preflight

    
    # Uncomment the below before Cloud deployment
    CORS(app)

    # Initialize the JWTManager
    jwt = JWTManager(app)

    # Register Middleware
    app.before_request(jwt_authentication)  # Apply JWT Authentication globally
    #app.after_request(log_api_usage)  # Log API usage after each request
                                                                
    # Initialize API and register routes
    api = Api(app)

    from genfoundry.routes import register_routes
    register_routes(api)

    init_llama()

    init_llama()

    app.config['CACHE_TYPE'] = 'SimpleCache'
    cache.init_app(app)

    return app
