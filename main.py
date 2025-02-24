import logging
import sys
from sqlalchemy import text
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sake_app.log"),
        logging.StreamHandler(sys.stdout)
    ])
logger = logging.getLogger(__name__)

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

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

        # Check if port 5000 is available
        if is_port_in_use(5000):
            logger.error("Port 5000 is already in use. Please stop other processes using this port.")
            sys.exit(1)

        # Start Flask application
        logger.info("Starting Flask application on port 5000...")
        app.run(host='0.0.0.0', port=5000)

    except Exception as e:
        logger.error(f"Application startup error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()