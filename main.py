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

def check_database_connection():
    try:
        from models import db
        from app import app
        with app.app_context():
            # Test database connection
            db.engine.connect()
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def init_database():
    try:
        from models import db
        from app import app

        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def main():
    try:
        logger.info("Starting application initialization...")

        # Check database connection first
        if not check_database_connection():
            logger.error("Failed to connect to database. Exiting...")
            sys.exit(1)

        # Initialize the database
        if not init_database():
            logger.error("Failed to initialize database. Exiting...")
            sys.exit(1)

        # Import Flask app
        from app import app

        # Start the Flask application
        logger.info("Starting Flask application on port 3000...")
        app.run(host="0.0.0.0", port=3000, debug=True)

    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

if __name__ == "__main__":
    main()