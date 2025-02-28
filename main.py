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

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    # プロセスの基本情報のみを取得
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # 各プロセスのコネクション情報を個別に取得
            connections = proc.connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr.port == port:
                    logger.info(f"Killing process {proc.pid} using port {port}")
                    os.kill(proc.pid, signal.SIGTERM)
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

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

        # Check if port 5000 is available, if not, kill the process using it
        if is_port_in_use(5000):
            logger.warning("Port 5000 is in use, attempting to kill the process...")
            if kill_process_on_port(5000):
                logger.info("Successfully killed process using port 5000")
            else:
                logger.error("Failed to kill process using port 5000")
                sys.exit(1)

        # Start Flask application
        logger.info("Starting Flask application on port 5000...")
        app.run(host='0.0.0.0', port=5000)

    except Exception as e:
        logger.error(f"Application startup error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()