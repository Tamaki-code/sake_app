import requests
import logging
from app import db
from models import Sake, Region, Brewery, FlavorChart, FlavorTag
from datetime import datetime

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

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
        response = requests.get(f"{SAKENOWA_API_BASE}/{endpoint}", headers={'Accept-Charset': 'utf-8'})
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Raw response for {endpoint}: {data}")

        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'flavorCharts', 'tags', 'brand_flavor_tags', 'flavorTags']:
                if key in data:
                    logging.info(f"Found {len(data[key])} items in {key}")
                    return data[key]
            logging.error(f"Unknown data format in {endpoint}: {data}")
            raise ValueError(f"Unknown data format in {endpoint}")

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

        # Fetch all necessary data first
        logging.info("Fetching data from Sakenowa API...")
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")
        flavor_charts = fetch_data("flavor-charts")

        # Process regions
        logging.info("Processing regions...")
        for area in areas:
            try:
                region = Region.query.filter_by(sakenowa_id=str(area["id"])).first()
                if not region:
                    region = Region(name=area["name"], sakenowa_id=str(area["id"]))
                    db.session.add(region)
                    logging.debug(f"Added new region: {area['name']}")
            except Exception as e:
                logging.error(f"Error processing region {area.get('name', 'unknown')}: {str(e)}")
                continue
        db.session.commit()
        logging.info("Regions processed successfully")

        # Process breweries
        logging.info("Processing breweries...")
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
                        logging.debug(f"Added new brewery: {brewery_data['name']}")
            except Exception as e:
                logging.error(f"Error processing brewery {brewery_data.get('name', 'unknown')}: {str(e)}")
                continue
        db.session.commit()
        logging.info("Breweries processed successfully")

        # Create flavor chart lookup
        logging.info("Creating flavor chart lookup...")
        flavor_chart_dict = {str(fc["brandId"]): fc for fc in flavor_charts}

        # Process sake brands and their flavor charts
        logging.info("Processing sake brands and flavor charts...")
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
                        db.session.flush()  # Flush to get the sake.id
                        logging.debug(f"Added new sake: {brand['name']}")

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
                            logging.debug(f"Added flavor chart for sake: {brand['name']}")
            except Exception as e:
                logging.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                continue

        db.session.commit()
        logging.info("Sake brands and flavor charts processed successfully")
        return True

    except Exception as e:
        logging.error(f"Error updating database: {str(e)}")
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