import os
import logging
from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS

# --- Flask Extensions ---
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app():
    # Serve frontend from 'frontend' folder
    app = Flask(__name__, static_folder='frontend', static_url_path='/')

    # Minimal configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # --- Serve HTML ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        frontend_folder = app.static_folder
        file_path = os.path.join(frontend_folder, path)
        index_path = os.path.join(frontend_folder, 'index.html')

        if os.path.exists(file_path) and not os.path.isdir(file_path):
            return send_from_directory(frontend_folder, path)
        elif os.path.exists(index_path):
            return send_from_directory(frontend_folder, 'index.html')
        else:
            return jsonify({"message": "Fixmore Mall API is running ✅"}), 200

    # --- Health check ---
    @app.route('/health')
    def health_check():
        try:
            db.session.execute('SELECT 1')
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        return jsonify({'status': 'healthy', 'database': db_status})

    return app


def setup_logging(app):
    if not app.debug:
        logging.basicConfig(level=logging.INFO)