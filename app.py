import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

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
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    database_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"

# Ensure proper postgresql:// URL format
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

logger.info("Configuring database connection...")
app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24))
)
logger.info("Database configuration loaded")

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

logger.info("SQLAlchemy initialized")

# Import models after db initialization
from models import User, Sake, Review  # noqa: E402
logger.info("Models imported successfully")

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Create tables
def init_db():
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

# Initialize database if this file is run directly
if __name__ == '__main__':
    init_db()
