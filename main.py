import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Importing required modules...")
        from app import app, db
        import routes  # noqa: F401
        logger.info("Successfully imported app and routes")

        # Verify database connection
        with app.app_context():
            try:
                db.engine.connect()
                logger.info("Database connection verified")

                # Verify tables exist
                tables = db.session.execute(db.text("""
                    SELECT tablename 
                    FROM pg_catalog.pg_tables 
                    WHERE schemaname = 'public'
                """)).fetchall()
                logger.info(f"Available tables: {[table[0] for table in tables]}")
            except Exception as db_error:
                logger.error(f"Database connection error: {db_error}")
                raise

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