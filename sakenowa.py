import requests
import logging
from app import db
from models import Sake

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api/v1"

def fetch_sake_data():
    try:
        # Fetch brands
        logging.info(f"Fetching brands from {SAKENOWA_API_BASE}/brands")
        brands_response = requests.get(f"{SAKENOWA_API_BASE}/brands")
        brands_response.raise_for_status()
        brands_data = brands_response.json()
        logging.info(f"Successfully fetched {len(brands_data)} brands")
        if not brands_data:
            logging.error("No brands data received from API")
            return [], []
        logging.debug(f"First brand data sample (with encoding info): {brands_data[0] if brands_data else 'No data'}")
        for brand in brands_data[:3]:  # Log first 3 brands for debugging
            logging.info(f"Sample brand data - Name: {brand.get('name', '').encode('utf-8')} (Brewery: {brand.get('brewery', '').encode('utf-8')})")

        # Fetch flavor data
        logging.info(f"Fetching flavor data from {SAKENOWA_API_BASE}/flavor")
        flavors_response = requests.get(f"{SAKENOWA_API_BASE}/flavor")
        flavors_response.raise_for_status()
        flavors_data = flavors_response.json()
        logging.info(f"Successfully fetched flavor data")

        return brands_data, flavors_data
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
        brands_data, flavors_data = fetch_sake_data()
        if not brands_data:
            logging.error("No data available to update database")
            return False
        logging.info(f"Processing {len(brands_data)} brands and {len(flavors_data)} flavor profiles")
        
        # Create flavor lookup dictionary
        flavor_lookup = {f['id']: f for f in flavors_data}
        logging.info(f"Created flavor lookup with {len(flavor_lookup)} entries")
        
        new_sakes = 0
        updated_sakes = 0
        
        for brand in brands_data:
            try:
                existing_sake = Sake.query.filter_by(sakenowa_id=brand['id']).first()
                
                # Get flavor profile
                flavor_profile = flavor_lookup.get(brand['id'], {})
                
                sake_data = {
                    'sakenowa_id': brand['id'],
                    'brand_name': brand['name'],
                    'brewery': brand.get('brewery', ''),
                    'area': brand.get('prefecture', ''),
                    'flavor_profile': flavor_profile
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
                
                # Commit every 100 records to avoid large transactions
                if (new_sakes + updated_sakes) % 100 == 0:
                    db.session.commit()
                    logging.info(f"Committed batch of records. Total processed: {new_sakes + updated_sakes}")
                
            except Exception as e:
                logging.error(f"Error processing sake {brand.get('name', 'unknown')}: {e}")
                continue
        
        # Final commit for remaining records
        db.session.commit()
        logging.info(f"Database update completed. Added {new_sakes} new sakes, updated {updated_sakes} existing ones.")
        return True
        
    except Exception as e:
        logging.error(f"Error updating sake database: {e}")
        db.session.rollback()
        raise
