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

def init_database():
    """Initialize the database and verify its state"""
    try:
        from create_tables import init_db
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialization completed")

        # Verify the database state
        from app import verify_database
        if not verify_database():
            logger.error("Database verification failed after initialization")
            return False

        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

def main():
    try:
        logger.info("Starting application initialization...")

        # Initialize database first
        if not init_database():
            logger.error("Failed to initialize database")
            sys.exit(1)

        # Import app and routes after database is ready
        from app import app
        import routes  # noqa: F401
        logger.info("Successfully imported app and routes")

        # Start the Flask application
        logger.info("Starting Flask application...")
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