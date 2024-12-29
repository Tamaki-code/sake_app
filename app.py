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

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    logger.info("Flask app initialized")

    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"

    # Ensure proper postgresql:// URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    logger.info(f"Database host: {os.environ.get('PGHOST')}")
    logger.info(f"Database port: {os.environ.get('PGPORT')}")
    logger.info(f"Database name: {os.environ.get('PGDATABASE')}")

    # Configure SQLAlchemy
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=True,  # Enable SQL query logging
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24))
    )

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    with app.app_context():
        try:
            # Import models
            from models import db
            from models.user import User
            from models.region import Region
            from models.brewery import Brewery
            from models.sake import Sake
            from models.review import Review
            from models.flavor_chart import FlavorChart
            from models.flavor_tag import FlavorTag

            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")

            # Setup user loader
            @login_manager.user_loader
            def load_user(id):
                try:
                    return User.query.get(int(id))
                except Exception as e:
                    logger.error(f"Error loading user {id}: {e}")
                    return None

            # Import routes
            import routes
            logger.info("Routes imported successfully")

            return app
        except Exception as e:
            logger.error(f"Error during app initialization: {e}")
            raise

# Create Flask app instance
try:
    app = create_app()
except Exception as e:
    logger.error(f"Failed to create Flask app: {e}")
    raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)