import os
import logging
import sys
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from models import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler(sys.stdout)
    ])
logger = logging.getLogger(__name__)

# Initialize login manager
login_manager = LoginManager()

def create_app():
    """Application factory function"""
    try:
        logger.info("Starting application creation...")
        app = Flask(__name__)

        # Configure database URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.debug("No DATABASE_URL found, constructing from components...")
            try:
                database_url = (
                    f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
                    f"@{os.environ['PGHOST']}:{os.environ['PGPORT']}/{os.environ['PGDATABASE']}"
                )
                logger.info("Successfully constructed database URL")
            except KeyError as e:
                logger.error(f"Missing required environment variable: {e}")
                raise ValueError(f"Missing required database configuration: {e}")

        # Handle Heroku-style postgres:// URLs
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            logger.info("Converted postgres:// URL to postgresql://")

        # Configure Flask application
        app.config.update(
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
        )
        logger.info("Flask configuration completed")

        # Initialize extensions
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        logger.info("Flask extensions initialized")

        with app.app_context():
            # Import and configure user loader
            from models.user import User

            @login_manager.user_loader
            def load_user(id):
                try:
                    return User.query.get(int(id))
                except Exception as e:
                    logger.error(f"Error loading user {id}: {e}")
                    return None

            # Import and register blueprints
            from routes import bp
            app.register_blueprint(bp)
            logger.info("Blueprints registered")

            # Verify database connection
            try:
                db.session.execute(text('SELECT 1'))
                logger.info("Database connection verified")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

            return app

    except Exception as e:
        logger.error(f"Error creating application: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        app = create_app()
        # ALWAYS serve the app on port 5000
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)