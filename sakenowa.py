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
        logger.info(f"Successfully fetched data from {endpoint}")

        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'rankings', 'flavorCharts', 'flavorTags', 'brandFlavorTags']:
                if key in data:
                    return data[key]
        return data

    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {str(e)}")
        return None

def update_database():
    """Update database with Sakenowa data"""
    try:
        # Fetch all required data
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")
        rankings = fetch_data("rankings")
        flavor_charts = fetch_data("flavor-charts")
        flavor_tags = fetch_data("flavor-tags")
        brand_flavor_tags = fetch_data("brand-flavor-tags")

        if not all([areas, breweries, brands]):
            raise ValueError("Failed to fetch core data (areas, breweries, brands)")

        logger.info("Starting database update process")

        # Clear existing data
        BrandFlavorTag.query.delete()
        Ranking.query.delete()
        FlavorTag.query.delete()
        FlavorChart.query.delete()
        Sake.query.delete()
        Brewery.query.delete()
        Region.query.delete()
        db.session.commit()
        logger.info("Cleared existing data")

        # Process regions (areas)
        regions_dict = {}
        for area in areas:
            region = Region(
                name=area["name"],
                sakenowa_id=str(area["id"])
            )
            db.session.add(region)
            regions_dict[str(area["id"])] = region
        db.session.commit()
        logger.info(f"Added {len(regions_dict)} regions")

        # Process breweries
        breweries_dict = {}
        for brewery_data in breweries:
            brewery_id = str(brewery_data["id"])
            area_id = str(brewery_data["areaId"])

            if area_id in regions_dict:
                brewery = Brewery(
                    name=brewery_data["name"],
                    sakenowa_brewery_id=brewery_id,
                    region_id=regions_dict[area_id].id
                )
                db.session.add(brewery)
                breweries_dict[brewery_id] = brewery

        db.session.commit()
        logger.info(f"Added {len(breweries_dict)} breweries")

        # Process flavor tags
        flavor_tags_dict = {}
        if flavor_tags:
            for tag_data in flavor_tags:
                tag = FlavorTag(
                    name=tag_data["name"],
                    sakenowa_id=str(tag_data["id"])
                )
                db.session.add(tag)
                flavor_tags_dict[str(tag_data["id"])] = tag
            db.session.commit()
            logger.info(f"Added {len(flavor_tags_dict)} flavor tags")

        # Process sakes (brands)
        sakes_dict = {}
        for brand in brands:
            brewery_id = str(brand["breweryId"])
            if brewery_id in breweries_dict:
                sake = Sake(
                    name=brand["name"],
                    sakenowa_id=str(brand["id"]),
                    brewery_id=breweries_dict[brewery_id].id
                )
                db.session.add(sake)
                sakes_dict[str(brand["id"])] = sake

        db.session.commit()
        logger.info(f"Added {len(sakes_dict)} sakes")

        # Process flavor charts
        if flavor_charts:
            for fc in flavor_charts:
                brand_id = str(fc["brandId"])
                if brand_id in sakes_dict:
                    chart = FlavorChart(
                        sake_id=sakes_dict[brand_id].id,
                        f1=fc.get("f1", 0.0),
                        f2=fc.get("f2", 0.0),
                        f3=fc.get("f3", 0.0),
                        f4=fc.get("f4", 0.0),
                        f5=fc.get("f5", 0.0),
                        f6=fc.get("f6", 0.0)
                    )
                    db.session.add(chart)
            db.session.commit()
            logger.info("Added flavor charts")

        # Process brand flavor tags
        if brand_flavor_tags:
            for bft in brand_flavor_tags:
                brand_id = str(bft["brandId"])
                tag_id = str(bft["flavorTagId"])
                if brand_id in sakes_dict and tag_id in flavor_tags_dict:
                    link = BrandFlavorTag(
                        sake_id=sakes_dict[brand_id].id,
                        flavor_tag_id=flavor_tags_dict[tag_id].id
                    )
                    db.session.add(link)
            db.session.commit()
            logger.info("Added brand flavor tags")

        # Process rankings
        if rankings:
            for rank_data in rankings:
                brand_id = str(rank_data["brandId"])
                if brand_id in sakes_dict:
                    ranking = Ranking(
                        sake_id=sakes_dict[brand_id].id,
                        rank=rank_data["rank"],
                        category=rank_data.get("category", "total")
                    )
                    db.session.add(ranking)
            db.session.commit()
            logger.info("Added rankings")

        logger.info("Database update completed successfully")
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