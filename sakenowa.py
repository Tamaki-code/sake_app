import requests
import logging
import sys
from datetime import datetime
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
        logger.info(f"Successfully fetched data from {endpoint}")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response content type: {response.headers.get('content-type')}")
        logger.debug(f"Response keys: {list(data.keys())}")

        # Extract data based on endpoint and log sample data
        extracted_data = []
        if endpoint == "areas":
            extracted_data = data.get("areas", [])
        elif endpoint == "breweries":
            extracted_data = data.get("breweries", [])
            if extracted_data:
                logger.debug(f"Sample brewery: ID={extracted_data[0]['id']}, Name={extracted_data[0]['name']}")
        elif endpoint == "brands":
            extracted_data = data.get("brands", [])
            if extracted_data:
                logger.debug(f"Sample brand: ID={extracted_data[0]['id']}, Name={extracted_data[0]['name']}, BreweryID={extracted_data[0]['breweryId']}")
        elif endpoint == "flavor-charts":
            extracted_data = data.get("flavorCharts", [])
        elif endpoint == "flavor-tags":
            extracted_data = data.get("tags", [])
        elif endpoint == "brand-flavor-tags":
            extracted_data = data.get("flavorTags", [])

        logger.info(f"Extracted {len(extracted_data)} items from {endpoint}")
        return extracted_data

    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {str(e)}", exc_info=True)
        return []

def process_chunks(items, chunk_size=100):
    """Process items in chunks"""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

def update_database():
    """Update database with Sakenowa data"""
    try:
        logger.info("Starting database update process")

        # Fetch all required data
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")

        if not all([areas, breweries, brands]):
            raise ValueError("Failed to fetch core data (areas, breweries, brands)")

        # Process regions and create lookup dictionary
        regions_dict = {}
        for area in areas:
            region = Region.query.filter_by(sakenowa_id=str(area["id"])).first()
            if not region:
                region = Region(
                    name=area["name"],
                    sakenowa_id=str(area["id"])
                )
                db.session.add(region)
            regions_dict[str(area["id"])] = region
        db.session.commit()
        logger.info(f"Processed {len(regions_dict)} regions")

        # Process breweries in chunks
        breweries_dict = {}
        for chunk in process_chunks(breweries):
            for brewery_data in chunk:
                try:
                    brewery_id = str(int(brewery_data["id"]))  # Normalize ID
                    area_id = str(brewery_data["areaId"])

                    brewery = Brewery.query.filter_by(sakenowa_brewery_id=brewery_id).first()
                    if not brewery and area_id in regions_dict:
                        brewery = Brewery(
                            name=brewery_data["name"],
                            sakenowa_brewery_id=brewery_id,
                            region_id=regions_dict[area_id].id
                        )
                        db.session.add(brewery)
                        breweries_dict[brewery_id] = brewery
                except Exception as e:
                    logger.error(f"Error processing brewery {brewery_data.get('name', 'unknown')}: {str(e)}")
                    continue
            db.session.commit()
            logger.info(f"Processed {len(breweries_dict)} breweries so far")

        # Log brewery IDs for debugging
        logger.debug("Sample of brewery IDs in database:")
        sample_breweries = Brewery.query.limit(5).all()
        for b in sample_breweries:
            logger.debug(f"Brewery ID: {b.sakenowa_brewery_id}, Name: {b.name}")

        # Process sakes (brands) in chunks with normalized IDs
        sakes_dict = {}
        for chunk in process_chunks(brands):
            for brand in chunk:
                try:
                    brand_id = str(int(brand["id"]))  # Normalize ID
                    brewery_id = str(int(brand["breweryId"]))  # Normalize ID

                    # Debug logging for ID matching
                    logger.debug(f"Processing sake: {brand['name']}")
                    logger.debug(f"  Raw brewery ID: {brand['breweryId']}")
                    logger.debug(f"  Normalized brewery ID: {brewery_id}")

                    # Query for brewery directly
                    brewery = Brewery.query.filter_by(sakenowa_brewery_id=brewery_id).first()
                    if brewery:
                        sake = Sake.query.filter_by(sakenowa_id=brand_id).first()
                        if not sake:
                            sake = Sake(
                                name=brand["name"],
                                sakenowa_id=brand_id,
                                brewery_id=brewery.id
                            )
                            db.session.add(sake)
                            sakes_dict[brand_id] = sake

                            if len(sakes_dict) % 100 == 0:
                                db.session.commit()
                                logger.info(f"Added {len(sakes_dict)} sakes so far")
                    else:
                        logger.warning(f"Brewery not found for sake {brand['name']} (brewery_id: {brewery_id})")
                        # Debug output for brewery search
                        sample_brewery = Brewery.query.first()
                        if sample_brewery:
                            logger.debug(f"Sample brewery in DB - ID: {sample_brewery.sakenowa_brewery_id}, Name: {sample_brewery.name}")

                except Exception as e:
                    logger.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                    continue

        # Final commit and logging
        db.session.commit()
        logger.info(f"Database update completed: {len(regions_dict)} regions, {len(breweries_dict)} breweries, {len(sakes_dict)} sakes")

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