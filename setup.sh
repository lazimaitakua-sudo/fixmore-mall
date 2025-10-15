#!/bin/bash

echo "Setting up Fixmore Mall for Render deployment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Set up environment variables
echo "Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please update backend/.env with your actual configuration values"
fi

# Initialize database
echo "Initializing database..."
python -m flask db init
python -m flask db migrate -m "Initial migration"
python -m flask db upgrade

# Create admin user
echo "Creating admin user..."
python -c "
from app import create_app, db
from app.models import User
from app.utils.security import hash_password

app = create_app()
with app.app_context():
    if not User.query.filter_by(email='admin@fixmore.com').first():
        admin = User(
            email='admin@fixmore.com',
            password_hash=hash_password('admin123'),
            first_name='Admin',
            last_name='User',
            phone='254700000000',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: jogoonets@gmail.com / admin123')
    else:
        print('Admin user already exists')
"

echo "Setup completed successfully!"
echo "To start the backend: cd backend && python run.py"
echo "To start the frontend: cd frontend && python -m http.server 3000"