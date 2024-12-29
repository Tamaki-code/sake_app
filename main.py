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
    """Check if database connection is working"""
    try:
        from app import db
        with db.engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def main():
    try:
        logger.info("Starting application initialization...")

        # Import Flask app
        from app import app

        if not app:
            logger.error("Failed to create Flask application")
            sys.exit(1)

        # Check database connection
        if not check_database_connection():
            logger.error("Failed to connect to database. Exiting...")
            sys.exit(1)

        # Start the Flask application
        logger.info("Starting Flask application...")
        app.run(host="0.0.0.0", port=3000, debug=True)

    except ImportError as e:
        logger.error(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        sys.exit(1)

if __name__ == "__main__":
    main()