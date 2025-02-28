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
                             timeout=60)
        response.raise_for_status()
        data = response.json()

        # エンドポイントに応じたレスポンス処理
        if endpoint == "rankings":
            logger.info(f"Raw rankings data: {str(data)[:500]}...")  # 最初の500文字をログ出力

            # ランキングデータの配列を処理
            all_rankings = []
            if isinstance(data, list):
                all_rankings = data
            elif isinstance(data, dict) and "totalRanking" in data:
                # totalRankingがある場合はそれを使用
                all_rankings = data["totalRanking"]
            elif isinstance(data, dict):
                # 地域ごとのランキングを処理
                for area in data.values():
                    if isinstance(area, dict) and "ranking" in area:
                        area_rankings = area["ranking"]
                        for rank in area_rankings:
                            rank["areaId"] = area.get("areaId")
                        all_rankings.extend(area_rankings)

            # サンプルデータをログ出力
            for i, item in enumerate(all_rankings[:3]):
                logger.info(f"Sample ranking {i+1}: {item}")
            logger.info(f"Total rankings found: {len(all_rankings)}")
            return all_rankings

        # その他のエンドポイントの処理
        if isinstance(data, dict):
            for key in ['areas', 'brands', 'breweries', 'flavorCharts', 'tags']:
                if key in data:
                    logger.info(f"Successfully fetched {len(data[key])} items from {key}")
                    return data[key]

        return data
    except Exception as e:
        logger.error(f"Error fetching data from {endpoint}: {str(e)}")
        raise

def update_rankings():
    """Update rankings data from Sakenowa API"""
    try:
        logger.info("Starting rankings update process")
        rankings_data = fetch_data("rankings")

        if not rankings_data:
            logger.error("No rankings data received")
            return False

        # データベースの現在の状態をログ出力
        sake_count = Sake.query.count()
        logger.info(f"Current sake count in database: {sake_count}")

        # サンプルのSakeデータをログ出力
        sample_sakes = Sake.query.limit(5).all()
        logger.info("Sample sake records:")
        for sake in sample_sakes:
            logger.info(f"Sake - ID: {sake.id}, Name: {sake.name}, Sakenowa ID: {sake.sakenowa_id}")

        # 既存のランキングをクリア
        Ranking.query.delete()
        db.session.commit()
        logger.info("Cleared existing rankings")

        # ランキングデータを処理
        rankings_added = 0
        for rank_data in rankings_data:
            try:
                brand_id = str(rank_data.get("brandId", "")).strip()
                logger.info(f"Processing ranking for brand ID: {brand_id}")

                # 完全一致で検索
                sake = Sake.query.filter(
                    Sake.sakenowa_id == brand_id
                ).first()

                if sake:
                    logger.info(f"Found matching sake - ID: {sake.id}, Name: {sake.name}")
                    # ランキングを作成
                    ranking = Ranking(
                        sake_id=sake.id,
                        ranking_type='overall',
                        rank=rank_data["rank"],
                        score=rank_data.get("score", 0.0),
                        period=datetime.utcnow().strftime('%Y-%m')
                    )
                    db.session.add(ranking)
                    rankings_added += 1

                    if rankings_added % 10 == 0:
                        logger.info(f"Added {rankings_added} rankings so far")
                        db.session.commit()
                else:
                    logger.warning(f"No sake found for brand ID: {brand_id}")

            except Exception as e:
                logger.error(f"Error processing ranking for brand ID {brand_id}: {str(e)}")
                continue

        # 最終コミット
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
                    # ここでbrandIdを文字列として正規化
                    brand_id = str(brand["id"]).strip()
                    sake = Sake.query.filter_by(sakenowa_id=brand_id).first()
                    if not sake:
                        sake = Sake(
                            name=brand["name"],
                            sakenowa_id=brand_id,  # 正規化したIDを使用
                            brewery_id=brewery.id
                        )
                        db.session.add(sake)
                        db.session.flush()
                        sakes_added += 1

                        # Add flavor chart if available
                        flavor_data = flavor_chart_dict.get(brand_id)  # 正規化したIDを使用
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