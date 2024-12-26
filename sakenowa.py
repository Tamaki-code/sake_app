import requests
import logging
from app import db
from models import Sake, Region, Brewery
from datetime import datetime

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api/v1"

def fetch_sake_data():
    try:
        # Fetch brands
        logging.info(f"Fetching brands from {SAKENOWA_API_BASE}/brands")
        brands_response = requests.get(f"{SAKENOWA_API_BASE}/brands", headers={'Accept-Charset': 'utf-8'})
        brands_response.raise_for_status()
        brands_data = brands_response.json()
        logging.info(f"Successfully fetched {len(brands_data)} brands")

        if not brands_data:
            logging.error("No brands data received from API")
            return [], [], []

        logging.info("Sample brand data:")
        for brand in brands_data[:3]:
            logging.info(f"Brand ID: {brand.get('id')}")
            logging.info(f"Brand Name: {brand.get('name', '').encode('utf-8')}")
            logging.info(f"Brewery: {brand.get('brewery', '').encode('utf-8')}")
            logging.info(f"Prefecture: {brand.get('prefecture', '').encode('utf-8')}")

        # Fetch breweries
        logging.info(f"Fetching breweries from {SAKENOWA_API_BASE}/breweries")
        breweries_response = requests.get(f"{SAKENOWA_API_BASE}/breweries", headers={'Accept-Charset': 'utf-8'})
        breweries_response.raise_for_status()
        breweries_data = breweries_response.json()
        logging.info(f"Successfully fetched {len(breweries_data)} breweries")

        # Fetch flavor data
        logging.info(f"Fetching flavor data from {SAKENOWA_API_BASE}/flavor")
        flavors_response = requests.get(f"{SAKENOWA_API_BASE}/flavor", headers={'Accept-Charset': 'utf-8'})
        flavors_response.raise_for_status()
        flavors_data = flavors_response.json()
        logging.info(f"Successfully fetched flavor data")

        return brands_data, breweries_data, flavors_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from Sakenowa API: {e}")
        logging.error(f"Response status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        logging.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while fetching data: {e}")
        raise

def update_sake_database():
    try:
        logging.info("Starting sake database update process")
        brands_data, breweries_data, flavors_data = fetch_sake_data()

        if not brands_data or not breweries_data:
            logging.error("No data available to update database")
            return False

        logging.info(f"Processing {len(brands_data)} brands and {len(breweries_data)} breweries")

        # Create flavor lookup dictionary
        flavor_lookup = {f['brandId']: f for f in flavors_data}
        logging.info(f"Created flavor lookup with {len(flavor_lookup)} entries")

        # Create brewery lookup dictionary
        brewery_lookup = {b['id']: b for b in breweries_data}

        # Process regions and breweries first
        regions = {}
        for brewery in breweries_data:
            prefecture = brewery.get('prefecture', '')
            if prefecture not in regions:
                region = Region.query.filter_by(name=prefecture).first()
                if not region:
                    region = Region(
                        name=prefecture,
                        sakenowa_id=str(brewery.get('prefectureCode', ''))
                    )
                    db.session.add(region)
                    logging.info(f"Added new region: {prefecture}")
                regions[prefecture] = region

        db.session.commit()
        logging.info("Regions committed to database")

        # Process breweries
        for brewery_data in breweries_data:
            try:
                brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brewery_data['id'])).first()
                if not brewery:
                    region = regions.get(brewery_data.get('prefecture', ''))
                    if region:
                        brewery = Brewery(
                            name=brewery_data['name'],
                            sakenowa_brewery_id=str(brewery_data['id']),
                            region_id=region.id
                        )
                        db.session.add(brewery)
                        logging.info(f"Added new brewery: {brewery_data['name']}")
            except Exception as e:
                logging.error(f"Error processing brewery {brewery_data.get('name', 'unknown')}: {e}")
                continue

        db.session.commit()
        logging.info("Breweries committed to database")

        # Process sakes
        new_sakes = 0
        updated_sakes = 0

        for brand in brands_data:
            try:
                brewery_data = brewery_lookup.get(brand.get('breweryId'))
                if not brewery_data:
                    logging.warning(f"No brewery found for brand {brand.get('name')}")
                    continue

                brewery = Brewery.query.filter_by(sakenowa_brewery_id=str(brewery_data['id'])).first()
                if not brewery:
                    logging.warning(f"Brewery not found in database for brand {brand.get('name')}")
                    continue

                existing_sake = Sake.query.filter_by(sakenowa_id=str(brand['id'])).first()

                sake_data = {
                    'sakenowa_id': str(brand['id']),
                    'name': brand['name'],
                    'brewery_id': brewery.id
                }

                if existing_sake:
                    for key, value in sake_data.items():
                        setattr(existing_sake, key, value)
                    updated_sakes += 1
                    logging.debug(f"Updated sake: {brand['name']}")
                else:
                    new_sake = Sake(**sake_data)
                    db.session.add(new_sake)
                    new_sakes += 1
                    logging.debug(f"Added new sake: {brand['name']}")

                # Commit every 100 records
                if (new_sakes + updated_sakes) % 100 == 0:
                    db.session.commit()
                    logging.info(f"Committed batch of records. Total processed: {new_sakes + updated_sakes}")

            except Exception as e:
                logging.error(f"Error processing sake {brand.get('name', 'unknown')}: {e}")
                continue

        # Final commit
        db.session.commit()
        logging.info(f"Database update completed. Added {new_sakes} new sakes, updated {updated_sakes} existing ones.")
        return True

    except Exception as e:
        logging.error(f"Error updating sake database: {e}")
        db.session.rollback()
        raise