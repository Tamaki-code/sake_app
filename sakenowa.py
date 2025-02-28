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

        response = requests.get(
            url,
            headers={'Accept': 'application/json'},
            timeout=60
        )
        response.raise_for_status()

        # Log the raw response for debugging
        logger.debug(f"Raw response content: {response.text[:1000]}")

        data = response.json()

        # Log the complete structure of the response
        logger.debug(f"Complete response structure: {data.keys()}")

        # Extract data based on endpoint
        if endpoint == "areas":
            items = data.get("areas", [])
            logger.info(f"Received {len(items)} areas")
            if items:
                logger.debug(f"First area sample: {items[0]}")
                logger.debug(f"Last area sample: {items[-1]}")
        elif endpoint == "breweries":
            items = data.get("breweries", [])
            logger.info(f"Received {len(items)} breweries")
            if items:
                logger.debug(f"First brewery sample: {items[0]}")
                logger.debug(f"Last brewery sample: {items[-1]}")
        elif endpoint == "brands":
            items = data.get("brands", [])
            logger.info(f"Received {len(items)} brands")
            if items:
                logger.debug(f"First brand sample: {items[0]}")
                logger.debug(f"Last brand sample: {items[-1]}")
        elif endpoint == "ranking":  # エンドポイントを"ranking"に修正
            logger.debug(f"Complete ranking response: {data}")  # ランキングデータの完全な構造をログ出力
            items = []
            if isinstance(data, dict):
                items = data.get("ranking", [])
            elif isinstance(data, list):
                items = data
            logger.info(f"Received {len(items)} rankings")
            if items:
                logger.debug(f"First ranking sample: {items[0]}")
                logger.debug(f"Last ranking sample: {items[-1]}")
                # ランキングデータの構造を詳しく確認
                for key in items[0].keys():
                    logger.debug(f"Ranking data key: {key}")
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

def update_database():
    """Update database with Sakenowa API data"""
    try:
        # Clear existing data
        if not clear_database():
            raise ValueError("Failed to clear existing data")

        # Fetch data with validation
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

        rankings = fetch_data("ranking")  # エンドポイントを"ranking"に修正
        if not rankings:
            logger.warning("No rankings data received")
        else:
            logger.info(f"Fetched {len(rankings)} rankings")
            # ランキングデータの詳細をログ出力
            logger.debug(f"Sample ranking data structure: {rankings[0] if rankings else 'No data'}")

        # Process data within a transaction
        with db.session.begin():
            # Process regions
            regions_dict = {}
            for area in areas:
                try:
                    area_id = area["id"]  # Keep as integer
                    region = Region(
                        name=area["name"],
                        sakenowa_id=area_id
                    )
                    db.session.add(region)
                    regions_dict[area_id] = region
                    logger.debug(f"Added region: {area_id} - {area['name']}")
                except Exception as e:
                    logger.error(f"Error processing area {area}: {str(e)}")
                    continue

            # Force flush to ensure regions are created before referenced
            db.session.flush()
            logger.info(f"Added {len(regions_dict)} regions")

            # Process breweries
            breweries_dict = {}
            for brewery in breweries:
                try:
                    brewery_id = brewery["id"]  # Keep as integer
                    area_id = brewery["areaId"]  # Keep as integer

                    if area_id in regions_dict:
                        b = Brewery(
                            name=brewery["name"],
                            sakenowa_brewery_id=brewery_id,
                            region_id=regions_dict[area_id].id
                        )
                        db.session.add(b)
                        breweries_dict[brewery_id] = b
                        logger.debug(f"Added brewery: {brewery_id} - {brewery['name']}")
                    else:
                        logger.warning(f"Region {area_id} not found for brewery {brewery['name']}")
                except Exception as e:
                    logger.error(f"Error processing brewery {brewery.get('name', 'unknown')}: {str(e)}")
                    continue

            # Force flush to ensure breweries are created before referenced
            db.session.flush()
            logger.info(f"Added {len(breweries_dict)} breweries")

            # Process sakes
            sake_dict = {}
            sake_count = 0
            for brand in brands:
                try:
                    brand_id = brand["id"]  # Keep as integer
                    brewery_id = brand["breweryId"]  # Keep as integer

                    if brewery_id in breweries_dict:
                        sake = Sake(
                            name=brand["name"],
                            sakenowa_id=brand_id,
                            brewery_id=breweries_dict[brewery_id].id
                        )
                        db.session.add(sake)
                        sake_dict[brand_id] = sake
                        sake_count += 1

                        if sake_count % 100 == 0:
                            logger.info(f"Processed {sake_count} sakes")
                            # Periodically flush to avoid memory issues with large datasets
                            db.session.flush()
                    else:
                        logger.warning(f"Brewery {brewery_id} not found for sake {brand['name']}")
                except Exception as e:
                    logger.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                    continue

            # Process rankings if available
            ranking_count = 0
            if rankings:
                for rank_data in rankings:
                    try:
                        # ランキングデータの詳細をログ出力
                        logger.debug(f"Processing ranking data: {rank_data}")
                        brand_id = rank_data["brandId"]
                        if brand_id in sake_dict:
                            ranking = Ranking(
                                sake_id=sake_dict[brand_id].id,
                                rank=rank_data.get("rank"),
                                category=rank_data.get("type"),  # rank_type を category として保存
                                created_at=datetime.utcnow()
                            )
                            db.session.add(ranking)
                            ranking_count += 1

                            if ranking_count % 100 == 0:
                                logger.info(f"Processed {ranking_count} rankings")
                                db.session.flush()
                        else:
                            logger.warning(f"Sake not found for brand_id {brand_id} in ranking")
                    except Exception as e:
                        logger.error(f"Error processing ranking for brand {brand_id}: {str(e)}")
                        continue

            logger.info(f"Added {ranking_count} rankings")

            # Verify final counts
            logger.info("Database update completed")
            logger.info(f"Final counts:")
            logger.info(f"Regions: {Region.query.count()}")
            logger.info(f"Breweries: {Brewery.query.count()}")
            logger.info(f"Sakes: {Sake.query.count()}")
            logger.info(f"Rankings: {Ranking.query.count()}")

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