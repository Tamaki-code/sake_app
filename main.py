import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from app import app
    import routes  # noqa: F401
    logger.info("Successfully imported app and routes")
except Exception as e:
    logger.error(f"Error during import: {e}")
    raise

if __name__ == "__main__":
    try:
        logger.info("Starting Flask application...")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error starting Flask application: {e}")
        raise
