import requests
import logging
from app import db
from models import Sake

SAKENOWA_API_BASE = "https://muro.sakenowa.com/api"

def fetch_sake_data():
    try:
        # Fetch brands
        brands_response = requests.get(f"{SAKENOWA_API_BASE}/brands")
        brands_data = brands_response.json()

        # Fetch flavor data
        flavors_response = requests.get(f"{SAKENOWA_API_BASE}/flavor")
        flavors_data = flavors_response.json()

        return brands_data, flavors_data
    except Exception as e:
        logging.error(f"Error fetching data from Sakenowa API: {e}")
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
