import requests
import logging
from datetime import datetime
from models import db
from models.sake import Sake
from models.region import Region
from models.brewery import Brewery
from models.flavor_chart import FlavorChart

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

def configure_logging():
    """Configure logging for Sakenowa API integration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("sakenowa_update.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = configure_logging()

def fetch_data(endpoint):
    """Fetch data from Sakenowa API with improved error handling"""
    try:
        logger.info(f"Fetching data from {SAKENOWA_API_BASE}/{endpoint}")
        response = requests.get(
            f"{SAKENOWA_API_BASE}/{endpoint}",
            headers={'Accept-Charset': 'utf-8'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'flavorCharts', 'tags']:
                if key in data:
                    logger.info(f"Successfully fetched {len(data[key])} items from {key}")
                    return data[key]

            logger.error(f"Unknown data format in {endpoint}: {data}")
            raise ValueError(f"Unknown data structure received from {endpoint}")

        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching {endpoint}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Data parsing error for {endpoint}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during API fetch: {str(e)}")
        raise

def update_database():
    """Update database with Sakenowa data with transaction support"""
    try:
        logger.info("Starting database update process")

        # Fetch all necessary data first
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")
        flavor_charts = fetch_data("flavor-charts")

        # Start transaction
        with db.session.begin():
            # Process regions
            for area in areas:
                try:
                    region = Region.query.filter_by(sakenowa_id=str(area["id"])).first()
                    if not region:
                        region = Region(
                            name=area["name"],
                            sakenowa_id=str(area["id"])
                        )
                        db.session.add(region)
                        logger.info(f"Added new region: {area['name']}")
                except Exception as e:
                    logger.error(f"Error processing region {area.get('name', 'unknown')}: {str(e)}")
                    raise

            # Process breweries
            for brewery_data in breweries:
                try:
                    brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brewery_data["id"])).first()
                    if not brewery:
                        region = Region.query.filter_by(sakenowa_id=str(brewery_data["areaId"])).first()
                        if region:
                            brewery = Brewery(
                                name=brewery_data["name"],
                                sakenowa_brewery_id=str(brewery_data["id"]),
                                region_id=region.id
                            )
                            db.session.add(brewery)
                            logger.info(f"Added new brewery: {brewery_data['name']}")
                except Exception as e:
                    logger.error(f"Error processing brewery {brewery_data.get('name', 'unknown')}: {str(e)}")
                    raise

            # Create flavor chart lookup
            flavor_chart_dict = {str(fc["brandId"]): fc for fc in flavor_charts}

            # Process sake brands and their flavor charts
            for brand in brands:
                try:
                    brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brand["breweryId"])).first()
                    if brewery:
                        sake = Sake.query.filter_by(sakenowa_id=str(brand["id"])).first()
                        if not sake:
                            sake = Sake(
                                name=brand["name"],
                                sakenowa_id=str(brand["id"]),
                                brewery_id=brewery.id
                            )
                            db.session.add(sake)
                            db.session.flush()

                            # Add flavor chart if available
                            flavor_data = flavor_chart_dict.get(str(brand["id"]))
                            if flavor_data:
                                flavor_chart = FlavorChart(
                                    sake_id=sake.id,
                                    f1=flavor_data.get("f1", 0.0),
                                    f2=flavor_data.get("f2", 0.0),
                                    f3=flavor_data.get("f3", 0.0),
                                    f4=flavor_data.get("f4", 0.0),
                                    f5=flavor_data.get("f5", 0.0),
                                    f6=flavor_data.get("f6", 0.0)
                                )
                                db.session.add(flavor_chart)
                                logger.info(f"Added flavor chart for sake: {brand['name']}")
                except Exception as e:
                    logger.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                    raise

        logger.info("Database update completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database update failed: {str(e)}")
        return False

if __name__ == '__main__':
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            update_database()
    except Exception as e:
        logger.error(f"Failed to run database update: {str(e)}")
        exit(1)