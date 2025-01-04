import logging
import sys
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler(sys.stdout)
    ])
logger = logging.getLogger(__name__)

def check_database():
    """Check database connection and initialization"""
    try:
        from models import db
        # Test database connection using SQLAlchemy with proper text() wrapper
        result = db.session.execute(text('SELECT 1'))
        result.scalar()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return False

def main():
    try:
        logger.info("Starting Sake Review application...")

        # Import Flask app after logging configuration
        from app import create_app
        app = create_app()

        # Verify database connection
        with app.app_context():
            if not check_database():
                logger.error("Database verification failed")
                sys.exit(1)
            logger.info("Database verification successful")

        # Start Flask application
        logger.info("Starting Flask application on port 5000...")
        app.run(host='0.0.0.0', port=5000)

    except Exception as e:
        logger.error(f"Application startup error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()