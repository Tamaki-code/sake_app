import os
import logging
from flask import Flask
from flask_login import LoginManager
from models import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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

    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
        logger.info("Using constructed database URL from environment variables")

    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    logger.info("Configuring database connection...")

    # Configure SQLAlchemy
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=True,
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24))
    )

    try:
        # Initialize extensions
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        logger.info("Flask extensions initialized successfully")

        # Register blueprints and configure user loader
        with app.app_context():
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

            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully")

            # Test database connection
            db.session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")

            return app

    except Exception as e:
        logger.error(f"Error creating application: {e}")
        raise

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)