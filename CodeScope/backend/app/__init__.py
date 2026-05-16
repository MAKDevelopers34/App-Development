from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    origins = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(',')
    CORS(app, origins=[origin.strip() for origin in origins if origin.strip()])
    
    from app.routes import main
    app.register_blueprint(main)
    
    return app
