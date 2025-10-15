import os
from app import create_app

# Initialize Flask app
app = create_app()

if __name__ == "__main__":
    # Use PORT from environment (Render sets this) or default 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)