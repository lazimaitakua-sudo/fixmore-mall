import os
from flask import send_from_directory, jsonify
from app import create_app

# Initialize Flask app
app = create_app()

# --- Serve Frontend (React, Vue, etc.) ---
# Assume frontend build files are in ../frontend/dist or ../frontend/build
FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if not os.path.exists(FRONTEND_FOLDER):
    FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend files or return index.html for SPA routes."""
    if FRONTEND_FOLDER and os.path.exists(os.path.join(FRONTEND_FOLDER, path)):
        return send_from_directory(FRONTEND_FOLDER, path)
    elif FRONTEND_FOLDER and os.path.exists(os.path.join(FRONTEND_FOLDER, 'index.html')):
        return send_from_directory(FRONTEND_FOLDER, 'index.html')
    else:
        return jsonify({"message": "Fixmore Mall API is running"}), 200


# --- Start app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)