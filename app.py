import os
import logging
from flask import Flask
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

def create_app():
    # Initialize Flask
    app = Flask(__name__)
    logger.info("Flask app initialized")

    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"

    logger.info(f"Database host: {os.environ.get('PGHOST')}")
    logger.info(f"Database port: {os.environ.get('PGPORT')}")
    logger.info(f"Database name: {os.environ.get('PGDATABASE')}")

    # Ensure proper postgresql:// URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Configure SQLAlchemy
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=True,  # Enable SQL query logging
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24))
    )

    return app

# Create Flask app
app = create_app()

# Initialize models and database
from models import init_models
db = init_models(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import User model after db initialization
from models.user import User

@login_manager.user_loader
def load_user(id):
    try:
        return User.query.get(int(id))
    except Exception as e:
        logger.error(f"Error loading user {id}: {e}")
        return None

# Import routes after everything is initialized
import routes

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)