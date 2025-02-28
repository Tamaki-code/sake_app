import requests
import logging
import sys
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
            logging.StreamHandler(sys.stdout)
        ])
    return logging.getLogger(__name__)

logger = configure_logging()

def fetch_data(endpoint):
    """Fetch data from Sakenowa API"""
    try:
        logger.info(f"Fetching data from {endpoint}")
        response = requests.get(f"{SAKENOWA_API_BASE}/{endpoint}",
                              headers={'Accept-Charset': 'utf-8'},
                              timeout=60)
        response.raise_for_status()
        data = response.json()

        # Log response data for debugging
        logger.info(f"Response data type: {type(data)}")
        logger.info(f"Response structure: {str(data)[:200]}")

        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'flavorCharts']:
                if key in data:
                    return data[key]
        return data

    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {str(e)}")
        return None

def update_database():
    """Update database with Sakenowa data"""
    try:
        # Clear existing data except regions
        Brewery.query.delete()
        Sake.query.delete()
        FlavorChart.query.delete()
        db.session.commit()
        logger.info("Cleared existing data")

        # Fetch data
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")
        flavor_charts = fetch_data("flavor-charts") or []

        if not all([areas, breweries, brands]):
            raise ValueError("Failed to fetch required data")

        logger.info(f"Fetched data counts: {len(areas)} areas, {len(breweries)} breweries, {len(brands)} brands")

        # Process regions
        regions_added = 0
        for area in areas:
            try:
                area_id = str(area["id"])
                region = Region.query.filter_by(sakenowa_id=area_id).first()
                if not region:
                    region = Region(
                        name=area["name"],
                        sakenowa_id=area_id
                    )
                    db.session.add(region)
                    regions_added += 1
                    logger.info(f"Added region: {area['name']} (ID: {area_id})")
            except Exception as e:
                logger.error(f"Error processing region: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"Added {regions_added} regions")

        # Process breweries
        breweries_added = 0
        for brewery_data in breweries:
            try:
                brewery_id = str(brewery_data["id"])
                area_id = str(brewery_data["areaId"])
                region = Region.query.filter_by(sakenowa_id=area_id).first()

                if not region:
                    logger.error(f"Region not found for brewery {brewery_data['name']}")
                    continue

                brewery = Brewery(
                    name=brewery_data["name"],
                    sakenowa_brewery_id=brewery_id,
                    region_id=region.id
                )
                db.session.add(brewery)
                breweries_added += 1

                if breweries_added % 100 == 0:
                    db.session.commit()
                    logger.info(f"Added {breweries_added} breweries")

            except Exception as e:
                logger.error(f"Error processing brewery: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"Added {breweries_added} breweries")

        # Create flavor chart lookup
        flavor_chart_dict = {str(fc["brandId"]): fc for fc in flavor_charts}

        # Process sakes
        sakes_added = 0
        flavor_charts_added = 0
        for brand in brands:
            try:
                brand_id = str(brand["id"])
                brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brand["breweryId"])).first()

                if not brewery:
                    logger.error(f"Brewery not found for sake {brand['name']}")
                    continue

                sake = Sake(
                    name=brand["name"],
                    sakenowa_id=brand_id,
                    brewery_id=brewery.id
                )
                db.session.add(sake)
                db.session.flush()
                sakes_added += 1

                # Add flavor chart
                flavor_data = flavor_chart_dict.get(brand_id)
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
                    flavor_charts_added += 1

                if sakes_added % 100 == 0:
                    db.session.commit()
                    logger.info(f"Added {sakes_added} sakes and {flavor_charts_added} flavor charts")

            except Exception as e:
                logger.error(f"Error processing sake: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"Successfully added {sakes_added} sakes and {flavor_charts_added} flavor charts")
        return True

    except Exception as e:
        logger.error(f"Database update failed: {str(e)}")
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