import os
import logging
import sys
import psutil
import signal
import socket
from flask import Flask
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

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr.port == port:
                    logger.info(f"Killing process {proc.pid} using port {port}")
                    os.kill(proc.pid, signal.SIGTERM)
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def create_app():
    """Application factory function"""
    try:
        logger.info("Starting application creation...")
        app = Flask(__name__)

        # Configure database URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("No DATABASE_URL found in environment variables")
            raise ValueError("DATABASE_URL is required")

        # Debug log for configuration
        logger.debug("Configuring Flask application...")

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
        logger.debug("Initializing Flask extensions...")
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        logger.info("Flask extensions initialized")

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
            from routes import bp
            app.register_blueprint(bp)
            logger.info("Blueprints registered")

            # Verify database connection
            try:
                logger.debug("Verifying database connection...")
                db.session.execute(text('SELECT 1'))
                logger.info("Database connection verified")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

        return app

    except Exception as e:
        logger.error(f"Error creating application: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        port = 5000

        # Check if port is in use and attempt to free it
        if is_port_in_use(port):
            logger.warning(f"Port {port} is already in use")
            if not kill_process_on_port(port):
                logger.error(f"Failed to kill process using port {port}")
                sys.exit(1)
            # Wait a moment for the port to be freed
            import time
            time.sleep(2)

        app = create_app()
        logger.info(f"Starting Flask application on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)