import logging
import sys
from sqlalchemy import text
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import socket
import signal
import psutil
from models import db, Ranking  # Rankingモデルを追加

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

        # Check if rankings table exists and has data
        ranking_count = db.session.query(Ranking).count()
        logger.info(f"Found {ranking_count} rankings in database")

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

    except Exception as e:
        logger.error(f"Application startup error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()