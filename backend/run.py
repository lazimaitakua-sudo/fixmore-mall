import os
from flask import Flask, send_from_directory, jsonify
from app import create_app

# Initialize Flask app
app = create_app()

# Path to your static HTML folder
FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), 'frontend')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve index.html or fallback message."""
    file_path = os.path.join(FRONTEND_FOLDER, path)
    index_path = os.path.join(FRONTEND_FOLDER, 'index.html')

    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_FOLDER, path)
    elif os.path.exists(index_path):
        return send_from_directory(FRONTEND_FOLDER, 'index.html')
    else:
        return jsonify({"message": "Fixmore Mall API is running ✅"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)