import os
import logging
from flask import Flask
from flask_login import LoginManager
from models import db
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# Initialize login manager
login_manager = LoginManager()

def create_app():
    """Application factory function"""
    app = Flask(__name__)

    # Configure database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Construct from individual components
        try:
            database_url = (
                f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
                f"@{os.environ['PGHOST']}:{os.environ['PGPORT']}/{os.environ['PGDATABASE']}"
            )
            logger.info("Database URL constructed from environment variables")
        except KeyError as e:
            logger.error(f"Missing required environment variable: {e}")
            raise ValueError(f"Missing required database configuration: {e}")

    # Handle Heroku-style postgres:// URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Configure Flask application
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=True,  # Enable SQL query logging
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
        DEBUG=True  # Enable debug mode
    )

    try:
        # Initialize extensions
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        logger.info("Flask extensions initialized successfully")

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
            logger.info("Blueprints registered successfully")

            # Verify database connection
            db.session.execute(text('SELECT 1'))
            logger.info("Database connection verified successfully")

            return app

    except Exception as e:
        logger.error(f"Error creating application: {e}")
        raise

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)