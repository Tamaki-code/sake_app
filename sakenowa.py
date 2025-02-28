import requests
import logging
import sys
from datetime import datetime
from sqlalchemy import text
from models import db
from models.sake import Sake
from models.region import Region
from models.brewery import Brewery
from models.flavor_chart import FlavorChart
from models.flavor_tag import FlavorTag
from models.ranking import Ranking
from models.brand_flavor_tag import BrandFlavorTag

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

def configure_logging():
    """Configure logging for Sakenowa API integration"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("sakenowa_update.log"),
            logging.StreamHandler(sys.stdout)
        ])
    return logging.getLogger(__name__)

logger = configure_logging()

def fetch_data(endpoint):
    """Fetch data from Sakenowa API"""
    try:
        url = f"{SAKENOWA_API_BASE}/{endpoint}"
        logger.info(f"Fetching data from {url}")

        response = requests.get(
            url,
            headers={'Accept-Charset': 'utf-8'},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        # Detailed logging of response structure
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response data structure: {list(data.keys())}")
        logger.debug(f"Sample of response data: {str(data)[:500]}")

        # Extract data based on endpoint
        if endpoint == "areas":
            items = data.get("areas", [])
            if items:
                logger.debug(f"Sample area: {items[0]}")
        elif endpoint == "breweries":
            items = data.get("breweries", [])
            if items:
                logger.debug(f"Sample brewery: {items[0]}")
        elif endpoint == "brands":
            items = data.get("brands", [])
            if items:
                logger.debug(f"Sample brand: {items[0]}")
        else:
            items = []

        return items

    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {str(e)}", exc_info=True)
        return []

def clear_database():
    """Clear all data from the database"""
    try:
        logger.info("Starting database clear")
        with db.session.begin():
            BrandFlavorTag.query.delete()
            Ranking.query.delete()
            FlavorTag.query.delete()
            FlavorChart.query.delete()
            Sake.query.delete()
            Brewery.query.delete()
            Region.query.delete()
            logger.info("All tables cleared")
        return True
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}", exc_info=True)
        return False

def update_database():
    """Update database with Sakenowa API data"""
    try:
        # Clear existing data
        if not clear_database():
            raise ValueError("Failed to clear existing data")

        # Fetch data with validation
        areas = fetch_data("areas")
        if not areas:
            raise ValueError("No areas data received")
        logger.info(f"Fetched {len(areas)} areas")

        breweries = fetch_data("breweries")
        if not breweries:
            raise ValueError("No breweries data received")
        logger.info(f"Fetched {len(breweries)} breweries")

        brands = fetch_data("brands")
        if not brands:
            raise ValueError("No brands data received")
        logger.info(f"Fetched {len(brands)} brands")

        # Process data within a transaction
        with db.session.begin():
            # Process regions
            regions_dict = {}
            for area in areas:
                try:
                    area_id = str(int(area["id"]))
                    region = Region(
                        name=area["name"],
                        sakenowa_id=area_id
                    )
                    db.session.add(region)
                    regions_dict[area_id] = region
                    logger.debug(f"Added region: {area_id} - {area['name']}")
                except Exception as e:
                    logger.error(f"Error processing area {area}: {str(e)}")
                    continue

            logger.info(f"Added {len(regions_dict)} regions")

            # Process breweries
            breweries_dict = {}
            for brewery in breweries:
                try:
                    brewery_id = str(int(brewery["id"]))
                    area_id = str(int(brewery["areaId"]))

                    if area_id in regions_dict:
                        b = Brewery(
                            name=brewery["name"],
                            sakenowa_brewery_id=brewery_id,
                            region_id=regions_dict[area_id].id
                        )
                        db.session.add(b)
                        breweries_dict[brewery_id] = b
                        logger.debug(f"Added brewery: {brewery_id} - {brewery['name']}")
                    else:
                        logger.warning(f"Region {area_id} not found for brewery {brewery['name']}")
                except Exception as e:
                    logger.error(f"Error processing brewery {brewery.get('name', 'unknown')}: {str(e)}")
                    continue

            logger.info(f"Added {len(breweries_dict)} breweries")

            # Process sakes
            sake_count = 0
            for brand in brands:
                try:
                    brand_id = str(int(brand["id"]))
                    brewery_id = str(int(brand["breweryId"]))

                    if brewery_id in breweries_dict:
                        sake = Sake(
                            name=brand["name"],
                            sakenowa_id=brand_id,
                            brewery_id=breweries_dict[brewery_id].id
                        )
                        db.session.add(sake)
                        sake_count += 1

                        if sake_count % 100 == 0:
                            logger.info(f"Processed {sake_count} sakes")
                    else:
                        logger.warning(f"Brewery {brewery_id} not found for sake {brand['name']}")
                except Exception as e:
                    logger.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                    continue

            logger.info(f"Added {sake_count} sakes")

        # Verify final counts
        logger.info("Database update completed")
        logger.info(f"Final counts:")
        logger.info(f"Regions: {Region.query.count()}")
        logger.info(f"Breweries: {Brewery.query.count()}")
        logger.info(f"Sakes: {Sake.query.count()}")

        return True

    except Exception as e:
        logger.error(f"Database update failed: {str(e)}", exc_info=True)
        db.session.rollback()
        return False

if __name__ == '__main__':
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            if update_database():
                logger.info("Database update completed successfully")
            else:
                logger.error("Database update failed")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to run database update: {str(e)}", exc_info=True)
        sys.exit(1)