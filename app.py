import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
logger.info("Flask app initialized")

# Database configuration
try:
    database_url = os.environ['DATABASE_URL']
    # Ensure proper postgres:// URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.urandom(24)
    )
    logger.info("Database configuration loaded")
except Exception as e:
    logger.error(f"Error configuring database: {e}")
    raise

# Initialize SQLAlchemy
db = SQLAlchemy(app)
logger.info("SQLAlchemy initialized")

# Import models after db initialization to avoid circular imports
from models import User, Sake, Review  # noqa: E402
logger.info("Models imported successfully")

# Create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
