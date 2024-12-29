import logging
from app import app, db
from models import User, Sake, Review, Brewery, Region, FlavorChart

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def verify_database_encoding():
    """Verify database encoding settings"""
    with app.app_context():
        try:
            # Check database encodings
            client_encoding = db.session.execute(db.text("SHOW client_encoding")).scalar()
            server_encoding = db.session.execute(db.text("SHOW server_encoding")).scalar()
            database_encoding = db.session.execute(db.text("SELECT datcollate FROM pg_database WHERE datname = current_database()")).scalar()

            logger.info(f"Database Encoding Settings:")
            logger.info(f"Client Encoding: {client_encoding}")
            logger.info(f"Server Encoding: {server_encoding}")
            logger.info(f"Database Collation: {database_encoding}")

            # Test Japanese character insertion
            test_text = "テスト日本語"
            result = db.session.execute(
                db.text("SELECT convert_to(:text, 'UTF8') <> ''::bytea as is_valid"),
                {"text": test_text}
            ).scalar()
            logger.info(f"Japanese character encoding test: {'Passed' if result else 'Failed'}")

            return True
        except Exception as e:
            logger.error(f"Error verifying database encoding: {e}")
            return False

def create_tables():
    """Create all database tables"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False

def init_db():
    """Initialize the database with proper encoding and initial data"""
    try:
        with app.app_context():
            # Verify database encoding first
            if not verify_database_encoding():
                raise Exception("Database encoding verification failed")

            # Create tables
            if not create_tables():
                raise Exception("Failed to create database tables")

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

            # Create a test region if none exists
            if not Region.query.first():
                test_region = Region(
                    name='東京都',
                    sakenowa_id='13'
                )
                db.session.add(test_region)
                db.session.commit()
                logger.info("Test region created successfully!")

            return True

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_db()