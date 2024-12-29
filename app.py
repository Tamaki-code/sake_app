import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler()
    ])
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

# Configure SQLAlchemy
logger.info("Configuring database connection...")
app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ECHO=True,  # Enable SQL query logging
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24))
)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
logger.info("SQLAlchemy and LoginManager initialized successfully")

# Import models after db initialization
from models import User  # noqa: E402
logger.info("Models imported successfully")

@login_manager.user_loader
def load_user(id):
    try:
        return User.query.get(int(id))
    except Exception as e:
        logger.error(f"Error loading user {id}: {e}")
        return None

def verify_database():
    """Verify database connection and schema"""
    try:
        with app.app_context():
            # Test database connection
            db.engine.connect()
            logger.info("Database connection successful")

            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Available tables: {tables}")

            return True
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

if __name__ == '__main__':
    if verify_database():
        app.run(host='0.0.0.0', port=3000, debug=True)
    else:
        logger.error("Database verification failed, cannot start application")