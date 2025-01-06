from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from genfoundry.config import config
import os
#from app.api.user import User

def create_app(config_name):
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration based on the environment
    try:
        app.config.from_object(config[config_name])
    #    print(f"Loaded config: {config_name}")
    except KeyError:
        raise KeyError(f"Configuration '{config_name}' not found in config.py")

    #CORS(app, resources={r"/*": {"origins": app.config['CORS_ALLOWED_ORIGIN']}})
    CORS(app)
    
    # Initialize API and register routes
    from flask_restful import Api
    api = Api(app)

    from genfoundry.routes import register_routes
    register_routes(api)

    return app
