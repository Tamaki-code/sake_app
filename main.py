import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler(sys.stdout)
    ])
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Starting application initialization...")

        # Import Flask app and database
        from models import db
        from app import app

        # Initialize the database
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

        # Import routes after app initialization
        import routes  # noqa: F401
        logger.info("Routes imported successfully")

        # Start the Flask application
        app.run(host="0.0.0.0", port=8080, debug=True)

    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise


if __name__ == "__main__":
    main()
