import requests
import logging
from datetime import datetime
from models import db
from models.sake import Sake
from models.region import Region
from models.brewery import Brewery
from models.flavor_chart import FlavorChart
from models.ranking import Ranking

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

def configure_logging():
    """Configure logging for Sakenowa API integration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("sakenowa_update.log"),
            logging.StreamHandler()
        ])
    return logging.getLogger(__name__)

logger = configure_logging()

def fetch_data(endpoint):
    """Fetch data from Sakenowa API with improved error handling"""
    try:
        logger.info(f"Fetching data from {SAKENOWA_API_BASE}/{endpoint}")
        response = requests.get(f"{SAKENOWA_API_BASE}/{endpoint}",
                              headers={'Accept-Charset': 'utf-8'},
                              timeout=60)  # タイムアウトを60秒に設定
        response.raise_for_status()
        data = response.json()

        # エンドポイントに応じたレスポンス処理
        if endpoint == "rankings":
            if isinstance(data, list):
                # ランキングデータの最初の3件をログ出力
                for i, item in enumerate(data[:3]):
                    logger.info(f"Sample ranking data {i+1}: {item}")
                logger.info(f"Successfully fetched {len(data)} ranking items")
                return data
            elif isinstance(data, dict) and "rankings" in data:
                # データがdict形式で"rankings"キーがある場合
                rankings = data["rankings"]
                for i, item in enumerate(rankings[:3]):
                    logger.info(f"Sample ranking data {i+1}: {item}")
                logger.info(f"Successfully fetched {len(rankings)} ranking items from dictionary")
                return rankings
            logger.error(f"Unexpected rankings data format: {data}")
            raise ValueError("Rankings data is not in expected format")

        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'flavorCharts', 'tags']:
                if key in data:
                    logger.info(f"Successfully fetched {len(data[key])} items from {key}")
                    return data[key]

            logger.error(f"Unknown data format in {endpoint}: {data}")
            raise ValueError(f"Unknown data structure received from {endpoint}")

        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching {endpoint}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Data parsing error for {endpoint}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during API fetch: {str(e)}")
        raise

def update_rankings():
    """Update rankings data from Sakenowa API"""
    try:
        logger.info("Starting rankings update process")
        rankings_data = fetch_data("rankings")

        if not rankings_data:
            logger.error("No rankings data received")
            return False

        # Clear existing rankings before updating
        Ranking.query.delete()
        db.session.commit()
        logger.info("Cleared existing rankings")

        # サンプルのSakeデータをログ出力
        sample_sake = Sake.query.first()
        if sample_sake:
            logger.info(f"Sample sake data - ID: {sample_sake.id}, Sakenowa ID: {sample_sake.sakenowa_id}")

        rankings_added = 0
        for rank_data in rankings_data:
            try:
                brand_id = str(rank_data.get("brandId", ""))
                logger.debug(f"Processing ranking for brand ID: {brand_id}")

                sake = Sake.query.filter_by(sakenowa_id=brand_id).first()
                if sake:
                    ranking = Ranking(
                        sake_id=sake.id,
                        ranking_type='overall',  # このエンドポイントは総合ランキング
                        rank=rank_data["rank"],
                        score=rank_data.get("score", 0.0),
                        period=datetime.utcnow().strftime('%Y-%m'),  # 現在の年月を期間として設定
                        created_at=datetime.utcnow()
                    )
                    db.session.add(ranking)
                    rankings_added += 1
                    if rankings_added % 10 == 0:  # 10件ごとにログ出力
                        logger.info(f"Processed {rankings_added} rankings")
                else:
                    logger.warning(f"Sake not found for brand ID: {brand_id}")
                    # 対象の日本酒が見つからない場合のデバッグ情報
                    sake_check = Sake.query.filter(Sake.sakenowa_id.ilike(f"%{brand_id}%")).first()
                    if sake_check:
                        logger.warning(f"Similar sake found with sakenowa_id: {sake_check.sakenowa_id}")
            except Exception as e:
                logger.error(f"Error processing ranking for brand ID {rank_data.get('brandId')}: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"Successfully added {rankings_added} rankings")
        return True

    except Exception as e:
        logger.error(f"Rankings update failed: {str(e)}")
        db.session.rollback()
        return False

def update_database():
    """Update database with Sakenowa data with transaction support"""
    try:
        logger.info("Starting database update process")

        # Fetch all necessary data first
        areas = fetch_data("areas")
        breweries = fetch_data("breweries")
        brands = fetch_data("brands")
        flavor_charts = fetch_data("flavor-charts")

        # Process regions
        regions_added = 0
        for area in areas:
            try:
                region = Region.query.filter_by(sakenowa_id=str(area["id"])).first()
                if not region:
                    region = Region(name=area["name"], sakenowa_id=str(area["id"]))
                    db.session.add(region)
                    regions_added += 1
            except Exception as e:
                logger.error(f"Error processing region {area.get('name', 'unknown')}: {str(e)}")
                raise
        logger.info(f"Added {regions_added} new regions")
        db.session.commit()

        # Process breweries
        breweries_added = 0
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
                        breweries_added += 1
            except Exception as e:
                logger.error(f"Error processing brewery {brewery_data.get('name', 'unknown')}: {str(e)}")
                raise
        logger.info(f"Added {breweries_added} new breweries")
        db.session.commit()

        # Create flavor chart lookup
        flavor_chart_dict = {str(fc["brandId"]): fc for fc in flavor_charts}
        logger.info(f"Created flavor chart lookup with {len(flavor_chart_dict)} entries")

        # Process sake brands and their flavor charts
        sakes_added = 0
        flavor_charts_added = 0
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
                        db.session.flush()
                        sakes_added += 1

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
                            flavor_charts_added += 1
            except Exception as e:
                logger.error(f"Error processing sake {brand.get('name', 'unknown')}: {str(e)}")
                raise

        logger.info(f"Added {sakes_added} new sakes and {flavor_charts_added} flavor charts")
        db.session.commit()

        # Update rankings after basic data is updated
        logger.info("Starting rankings update...")
        if update_rankings():
            logger.info("Rankings update completed successfully")
        else:
            logger.warning("Rankings update failed, but basic data was updated successfully")

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
            update_database()
    except Exception as e:
        logger.error(f"Failed to run database update: {str(e)}")
        exit(1)