import logging
from sqlalchemy import text
from app import create_app
from models import db
from models.user import User
from models.region import Region

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_database_encoding():
    """Verify database encoding settings"""
    try:
        logger.info("Verifying database encoding settings...")
        # Check database encodings using proper text() wrapper
        client_encoding = db.session.execute(text("SHOW client_encoding")).scalar()
        server_encoding = db.session.execute(text("SHOW server_encoding")).scalar()
        database_encoding = db.session.execute(
            text("SELECT datcollate FROM pg_database WHERE datname = current_database()")
        ).scalar()

        logger.info(f"Database Encoding Settings:")
        logger.info(f"Client Encoding: {client_encoding}")
        logger.info(f"Server Encoding: {server_encoding}")
        logger.info(f"Database Collation: {database_encoding}")

        # Test Japanese character insertion
        test_text = "テスト日本語"
        result = db.session.execute(
            text("SELECT convert_to(:text, 'UTF8') <> ''::bytea as is_valid"),
            {"text": test_text}
        ).scalar()
        logger.info(f"Japanese character encoding test: {'Passed' if result else 'Failed'}")

        return True
    except Exception as e:
        logger.error(f"Error verifying database encoding: {e}")
        return False

def init_db():
    """Initialize the database with proper encoding and initial data"""
    try:
        # Create the Flask app
        app = create_app()

        with app.app_context():
            # Verify database encoding first
            if not verify_database_encoding():
                raise Exception("Database encoding verification failed")

            # Create tables
            db.create_all()
            logger.info("Database tables created successfully")

            # Create initial data if needed
            from models.user import User
            from models.region import Region

            # Create a test user if none exists
            if not User.query.first():
                test_user = User(
                    username='test_user',
                    email='test@example.com'
                )
                test_user.set_password('test123')
                db.session.add(test_user)
                db.session.commit()
                logger.info("Test user created successfully!")

            return True

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_db()