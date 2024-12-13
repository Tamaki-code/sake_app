import logging
from app import app, db
from models import User, Sake, Review

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_db():
    try:
        with app.app_context():
            # Create all database tables
            db.create_all()
            logger.info("Database tables created successfully!")
            
            # Create a test user if none exists
            if not User.query.first():
                test_user = User(username='test_user', email='test@example.com')
                test_user.set_password('test123')
                db.session.add(test_user)
                db.session.commit()
                logger.info("Test user created successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_db()
