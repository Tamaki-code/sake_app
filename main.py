import logging
import sys
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

def check_database():
    """Check database connection and initialization"""
    try:
        from models import db
        # Test database connection using SQLAlchemy with proper text() wrapper
        db.session.execute(text('SELECT 1'))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
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

        # Start Flask application
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=3000, debug=True)

    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()