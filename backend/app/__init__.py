from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
import os

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app():
    # ✅ Serve frontend directly from the 'frontend' folder
    app = Flask(__name__, static_folder='frontend', static_url_path='/')

    # Configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Import and register blueprints
    from app.routes.user_routes import user_bp
    from app.routes.voucher_routes import voucher_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(voucher_bp)

    # ✅ Serve index.html or API message
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        frontend_folder = app.static_folder
        file_path = os.path.join(frontend_folder, path)
        index_path = os.path.join(frontend_folder, 'index.html')

        if os.path.exists(file_path):
            return send_from_directory(frontend_folder, path)
        elif os.path.exists(index_path):
            return send_from_directory(frontend_folder, 'index.html')
        else:
            return jsonify({"message": "Fixmore Mall API is running ✅"}), 200

    return app