import os
import logging
import sys
from flask import Flask, jsonify
from flask_login import LoginManager
from sqlalchemy import text
from models import db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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
        logger.debug("Flask application instance created")

        # Get the database URL from environment variables
        database_url = os.environ.get('DATABASE_URL')

        # URLが 'postgres://' で始まる場合は 'postgresql://' に変換
        if database_url and database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://",
                                                1)

        if not database_url:
            logger.error("No DATABASE_URL found in environment variables")
            raise ValueError("DATABASE_URL is required")
        logger.debug(f"Database URL configuration found: {database_url}")

        # Debug log for configuration
        logger.debug("Starting Flask configuration...")

        # Generate a fixed SECRET_KEY if not set
        if not os.environ.get('SECRET_KEY'):
            os.environ['SECRET_KEY'] = 'sake-review-dev-key-2024'
            logger.info("Generated fixed SECRET_KEY for development")

        # Configure Flask application
        app.config.update(
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY=os.environ.get('SECRET_KEY'),
        )
        logger.info("Flask configuration completed")

        # Initialize extensions with debug logs
        logger.debug("Starting Flask extensions initialization...")
        try:
            db.init_app(app)
            logger.debug("Database initialization completed")

            login_manager.init_app(app)
            logger.debug("Login manager initialization completed")

            login_manager.login_view = 'main.login'
            logger.info("Flask extensions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize extensions: {str(e)}",
                         exc_info=True)
            raise

        # Add health check endpoint
        @app.route('/health')
        def health_check():
            return jsonify({"status": "healthy", "port": 5000})

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
            try:
                from routes import bp
                app.register_blueprint(bp)
                logger.info("Blueprints registered successfully")
            except Exception as e:
                logger.error(f"Failed to register blueprints: {str(e)}",
                             exc_info=True)
                raise

            # Verify database connection
            try:
                logger.debug("Verifying database connection...")
                db.session.execute(text('SELECT 1'))
                logger.info("Database connection verified successfully")
            except Exception as e:
                logger.error(f"Database connection failed: {e}", exc_info=True)
                raise

            try:
                db.create_all()
                logger.info("All tables created successfully (if not exist)")
            except Exception as e:
                logger.error(f"Failed to create tables: {e}", exc_info=True)
        logger.info("Application creation completed successfully")

        return app

    except Exception as e:
        logger.error(f"Error creating application: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    port = 5000
    try:
        app = create_app()
        logger.info(f"Starting Flask application on port {port}")
        # Always serve on 0.0.0.0 to make it accessible
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)
