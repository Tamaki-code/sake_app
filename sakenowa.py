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

        response = requests.get(url,
                            headers={'Accept': 'application/json'},
                            timeout=60)
        response.raise_for_status()

        # Log response details
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response content type: {response.headers.get('content-type')}")

        data = response.json()
        logger.debug(f"Response data keys: {data.keys()}")

        # Extract data based on endpoint and add detailed logging
        if endpoint == "areas":
            items = data.get("areas", [])
            logger.info(f"Received {len(items)} areas")
            if items:
                logger.debug(f"First area: {items[0]}")
        elif endpoint == "breweries":
            items = data.get("breweries", [])
            logger.info(f"Received {len(items)} breweries")
            if items:
                logger.debug(f"First brewery: {items[0]}")
        elif endpoint == "brands":
            items = data.get("brands", [])
            logger.info(f"Received {len(items)} brands")
            if items:
                logger.debug(f"First brand: {items[0]}")
        elif endpoint == "rankings":
            items = data.get("overall", [])
            logger.info(f"Received {len(items)} rankings")
            if items:
                logger.debug(f"First ranking: {items[0]}")
        else:
            items = []
            logger.warning(f"Unknown endpoint: {endpoint}")

        return items

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request failed for {endpoint}: {str(e)}", exc_info=True)
        return []
    except ValueError as e:
        logger.error(f"JSON parsing failed for {endpoint}: {str(e)}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching data from {endpoint}: {str(e)}", exc_info=True)
        return []

def process_rankings(rankings, sake_dict):
    """Process and insert ranking data"""
    ranking_count = 0
    try:
        logger.info(f"Starting to process {len(rankings)} rankings")
        for rank_data in rankings:
            try:
                brand_id = str(rank_data.get("brandId"))
                rank = rank_data.get("rank")
                score = rank_data.get("score", 0)  # デフォルト値を0に設定

                if not all([brand_id, rank is not None]):
                    logger.warning(f"Missing required ranking data: {rank_data}")
                    continue

                sake_dict_str = {str(k): v for k, v in sake_dict.items()}
                if brand_id not in sake_dict_str:
                    logger.warning(f"Sake not found for brand_id {brand_id} in ranking")
                    continue

                ranking = Ranking(
                    sake_id=sake_dict_str[brand_id].id,
                    rank=rank,
                    score=score,
                    category='overall'
                )
                db.session.add(ranking)
                ranking_count += 1

                if ranking_count % 100 == 0:
                    logger.info(f"Processed {ranking_count} rankings")
                    db.session.flush()

            except Exception as e:
                logger.error(f"Error processing ranking data: {str(e)}", exc_info=True)
                continue

        logger.info(f"Finished processing rankings. Added {ranking_count} rankings")
        return ranking_count

    except Exception as e:
        logger.error(f"Error in process_rankings: {str(e)}", exc_info=True)
        return 0

def update_database():
    """Update database with Sakenowa API data"""
    try:
        # Clear existing data
        with db.session.begin():
            logger.info("Clearing existing data...")
            BrandFlavorTag.query.delete()
            Ranking.query.delete()
            FlavorTag.query.delete()
            FlavorChart.query.delete()
            Sake.query.delete()
            Brewery.query.delete()
            Region.query.delete()
            db.session.commit()
            logger.info("Existing data cleared successfully")

        # Fetch all data
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

        rankings = fetch_data("rankings")
        if rankings:
            logger.info(f"Fetched {len(rankings)} rankings")

        # Process data within a transaction
        with db.session.begin():
            try:
                # Process regions
                regions_dict = {}
                for area in areas:
                    area_id = str(area["id"])
                    region = Region(
                        name=area["name"],
                        sakenowaId=area_id
                    )
                    db.session.add(region)
                    regions_dict[area_id] = region
                    logger.debug(f"Added region: {area_id} - {area['name']}")

                db.session.flush()
                logger.info(f"Added {len(regions_dict)} regions")

                # Process breweries
                breweries_dict = {}
                for brewery in breweries:
                    brewery_id = str(brewery["id"])
                    area_id = str(brewery["areaId"])

                    if area_id in regions_dict:
                        b = Brewery(
                            name=brewery["name"],
                            sakenowaBreweryId=brewery_id,
                            region_id=regions_dict[area_id].id
                        )
                        db.session.add(b)
                        breweries_dict[brewery_id] = b
                        logger.debug(f"Added brewery: {brewery_id} - {brewery['name']}")
                    else:
                        logger.warning(f"Region {area_id} not found for brewery {brewery['name']}")

                db.session.flush()
                logger.info(f"Added {len(breweries_dict)} breweries")

                # Process sakes
                sake_dict = {}
                for brand in brands:
                    brand_id = str(brand["id"])
                    brewery_id = str(brand["breweryId"])

                    if brewery_id in breweries_dict:
                        sake = Sake(
                            name=brand["name"],
                            sakenowaId=brand_id,
                            brewery_id=breweries_dict[brewery_id].id
                        )
                        db.session.add(sake)
                        sake_dict[brand_id] = sake
                        logger.debug(f"Added sake: {brand_id} - {brand['name']}")
                    else:
                        logger.warning(f"Brewery {brewery_id} not found for sake {brand['name']}")

                db.session.flush()
                logger.info(f"Added {len(sake_dict)} sakes")

                # Process rankings
                if rankings:
                    ranking_count = 0
                    for rank_data in rankings:
                        brand_id = str(rank_data.get("brandId"))
                        rank = rank_data.get("rank")
                        score = rank_data.get("score", 0)

                        if brand_id in sake_dict:
                            ranking = Ranking(
                                sake_id=sake_dict[brand_id].id,
                                rank=rank,
                                score=score,
                                category='overall'
                            )
                            db.session.add(ranking)
                            ranking_count += 1
                            logger.debug(f"Added ranking for sake {brand_id}: rank={rank}, score={score}")
                        else:
                            logger.warning(f"Sake not found for brand_id {brand_id} in ranking")

                    logger.info(f"Added {ranking_count} rankings")

                # Final commit
                db.session.commit()
                logger.info("All data committed successfully")

                # Log final counts
                logger.info("Final database counts:")
                logger.info(f"Regions: {Region.query.count()}")
                logger.info(f"Breweries: {Brewery.query.count()}")
                logger.info(f"Sakes: {Sake.query.count()}")
                logger.info(f"Rankings: {Ranking.query.count()}")

                return True

            except Exception as e:
                logger.error(f"Error processing data: {str(e)}", exc_info=True)
                db.session.rollback()
                return False

    except Exception as e:
        logger.error(f"Database update failed: {str(e)}", exc_info=True)
        return False

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