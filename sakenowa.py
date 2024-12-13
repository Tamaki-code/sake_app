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
    brands_data, flavors_data = fetch_sake_data()
    
    # Create flavor lookup dictionary
    flavor_lookup = {f['id']: f for f in flavors_data}
    
    for brand in brands_data:
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
        else:
            new_sake = Sake(**sake_data)
            db.session.add(new_sake)
    
    try:
        db.session.commit()
    except Exception as e:
        logging.error(f"Error updating sake database: {e}")
        db.session.rollback()
        raise
