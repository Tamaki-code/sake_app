import requests
import logging
from app import db
from models import Sake, Region, Brewery, FlavorChart, FlavorTag
from datetime import datetime

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

# Externalize logging configuration
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("sakenowa_update.log"),
            logging.StreamHandler()
        ]
    )

def fetch_data(endpoint):
    try:
        logging.info(f"Fetching data from {SAKENOWA_API_BASE}/{endpoint}")
        response = requests.get(f"{SAKENOWA_API_BASE}/{endpoint}", 
                              headers={'Accept-Charset': 'utf-8'})
        response.raise_for_status()
        data = response.json()

        # Log the raw response data for debugging
        logging.debug(f"Raw response for {endpoint}: {data}")

        # Handle nested dictionary formats
        if isinstance(data, dict):
            logging.info(f"Response contains keys: {list(data.keys())}")
            if "areas" in data:
                data = data["areas"]
            elif "brands" in data:
                data = data["brands"]
            elif "breweries" in data:
                data = data["breweries"]
            elif "rankings" in data:
                data = data["rankings"]
            elif "flavorCharts" in data:
                data = data["flavorCharts"]
            elif "tags" in data:
                data = data["tags"]
            elif "brand_flavor_tags" in data:
                data = data["brand_flavor_tags"]
            elif "flavorTags" in data:
                data = data["flavorTags"]
            else:
                logging.error(f"Unknown format in {endpoint}: {data}")
                raise ValueError(f"Unknown data format in {endpoint}")

        if not isinstance(data, list):
            logging.error(f"Unexpected data format from {endpoint}: {data}")
            raise ValueError(f"Expected list but got {type(data)}")

        logging.info(f"Successfully fetched {len(data)} records from {endpoint}")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {endpoint}: {e}")
        raise
    except ValueError as ve:
        logging.error(f"Data format error: {ve}")
        raise

def update_database():
    try:
        logging.info("Starting database update process")

        # Fetch all required data
        data = {
            "areas": fetch_data("areas"),
            "brands": fetch_data("brands"),
            "breweries": fetch_data("breweries"),
            "flavor_charts": fetch_data("flavor-charts"),
            "flavor_tags": fetch_data("flavor-tags"),
            "brand_flavor_tags": fetch_data("brand-flavor-tags")
        }

        # Process regions (areas)
        for area in data["areas"]:
            region = Region.query.filter_by(sakenowa_id=str(area["id"])).first()
            if not region:
                region = Region(
                    name=area["name"],
                    sakenowa_id=str(area["id"])
                )
                db.session.add(region)
                logging.info(f"Added new region: {area['name']}")

        db.session.commit()

        # Process breweries with proper region relationships
        for brewery_data in data["breweries"]:
            brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brewery_data["id"])).first()
            if not brewery:
                # Find the corresponding region
                region = Region.query.filter_by(name=brewery_data["prefecture"]).first()
                if region:
                    brewery = Brewery(
                        name=brewery_data["name"],
                        sakenowa_brewery_id=str(brewery_data["id"]),
                        region_id=region.id
                    )
                    db.session.add(brewery)
                    logging.info(f"Added new brewery: {brewery_data['name']}")
                else:
                    logging.warning(f"Region not found for brewery: {brewery_data['name']}")

        db.session.commit()

        # Process sake brands with proper brewery relationships
        for brand in data["brands"]:
            brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brand["breweryId"])).first()
            if not brewery:
                logging.warning(f"Brewery not found for brand: {brand['name']}")
                continue

            sake = Sake.query.filter_by(sakenowa_id=str(brand["id"])).first()
            if not sake:
                sake = Sake(
                    name=brand["name"],
                    sakenowa_id=str(brand["id"]),
                    brewery_id=brewery.id
                )
                db.session.add(sake)
                logging.info(f"Added new sake: {brand['name']}")

        db.session.commit()
        logging.info("Database update completed successfully")
        return True

    except Exception as e:
        logging.error(f"Error updating database: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    try:
        from app import app
        configure_logging()
        with app.app_context():
            update_database()
    except Exception as e:
        logging.error(f"Failed to update database: {e}")
        exit(1)