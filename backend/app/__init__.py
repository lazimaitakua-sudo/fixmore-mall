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
    # Resolve frontend folder relative to this file
    frontend_folder = os.path.join(os.path.dirname(__file__), '../frontend')

    app = Flask(__name__, static_folder=frontend_folder, static_url_path='/')

    # --- Minimal configurations ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

    # --- Initialize extensions ---
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # --- Favicon route ---
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(frontend_folder, 'favicon.ico')

    # --- SPA route ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        # Protect favicon route
        if path == 'favicon.ico':
            return favicon()

        requested_file = os.path.join(frontend_folder, path)
        index_file = os.path.join(frontend_folder, 'index.html')

        # Serve file if it exists, else fallback to index.html
        if os.path.exists(requested_file) and not os.path.isdir(requested_file):
            return send_from_directory(frontend_folder, path)
        elif os.path.exists(index_file):
            return send_from_directory(frontend_folder, 'index.html')
        else:
            # No frontend found, show API running message
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