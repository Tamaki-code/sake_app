from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.sake import Sake
from models.review import Review
from models.brewery import Brewery
from models.region import Region
from models.flavor_chart import FlavorChart
from models.ranking import Ranking  # 追加: Rankingモデルのimport
import logging
from datetime import datetime
from forms import SignupForm
from sqlalchemy.orm import joinedload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('main', __name__)

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            # Log in the user after successful registration
            login_user(user)
            flash('アカウントの登録が完了しました！', 'success')
            return redirect(url_for('main.index'))

        except Exception as e:
            logger.error(f"Error in signup: {str(e)}")
            db.session.rollback()
            flash('アカウントの登録中にエラーが発生しました。', 'error')

    return render_template('signup.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('ログインに成功しました。', 'success')
                return redirect(url_for('main.index'))

            flash('ユーザー名またはパスワードが正しくありません。', 'error')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('ログイン処理中にエラーが発生しました。', 'error')

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('ログアウトしました。', 'success')
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('ログアウト処理中にエラーが発生しました。', 'error')
    return redirect(url_for('main.index'))

@bp.route('/')
def index():
    try:
        # Get top 10 overall rankings with optimized query
        top_rankings = db.session.query(Ranking, Sake)\
            .join(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region)
            )\
            .filter(Ranking.category == 'overall')\
            .order_by(Ranking.rank)\
            .limit(10)\
            .all()

        # Get latest sakes with eager loading
        search_results = db.session.query(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region)
            )\
            .order_by(Sake.created_at.desc())\
            .limit(20)\
            .all()
            
        # フレーバータグの一覧を取得（検索フォーム用）
        from models.flavor_tag import FlavorTag
        flavor_tags = FlavorTag.query.order_by(FlavorTag.name).all()
        
        # フレーバープロファイルの日本語名マッピング
        flavor_profiles = {
            '1': {'name': '華やか - 重厚', 'low': '重厚', 'high': '華やか'},
            '2': {'name': '芳醇 - 穏やか', 'low': '穏やか', 'high': '芳醇'},
            '3': {'name': '濃醇 - 淡麗', 'low': '淡麗', 'high': '濃醇'},
            '4': {'name': '甘口 - 辛口', 'low': '甘口', 'high': '辛口'},
            '5': {'name': '特性 - 個性', 'low': '特性', 'high': '個性'},
            '6': {'name': '若年 - 熟成', 'low': '若年', 'high': '熟成'},
        }

        return render_template('index.html', 
                            search_results=search_results,
                            top_rankings=top_rankings,
                            flavor_tags=flavor_tags,
                            flavor_profiles=flavor_profiles)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('エラーが発生しました。しばらくしてから再度お試しください。', 'error')
        return render_template('index.html', 
                            search_results=[],
                            top_rankings=[],
                            flavor_tags=[],
                            flavor_profiles={})

@bp.route('/search')
def search():
    try:
        query = request.args.get('q', '').strip()
        flavor_tag_id = request.args.get('flavor_tag', '').strip()
        
        # 新しい味わいプロファイル検索パラメータを取得
        flavor_profile = request.args.get('flavor_profile', '')
        flavor_direction = request.args.get('flavor_direction', '')
        flavor_intensity = request.args.get('flavor_intensity', '')
        
        logger.info(f"Search query: {query}, Flavor tag: {flavor_tag_id}, Profile: {flavor_profile}, Direction: {flavor_direction}, Intensity: {flavor_intensity}")
        
        # フレーバータグの一覧を取得（検索フォーム用）
        from models.flavor_tag import FlavorTag
        flavor_tags = FlavorTag.query.order_by(FlavorTag.name).all()
        
        # 基本クエリを構築
        sake_query = db.session.query(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region),
                joinedload(Sake.flavor_chart)
            )
        
        # 銘柄名での検索
        if query:
            sake_query = sake_query.filter(Sake.name.ilike(f'%{query}%'))
        
        # フレーバータグでの検索
        if flavor_tag_id:
            from models.brand_flavor_tag import BrandFlavorTag
            try:
                flavor_tag = FlavorTag.query.filter_by(sakenowa_id=flavor_tag_id).first()
                if flavor_tag:
                    logger.info(f"Filtering by flavor tag: {flavor_tag.name}")
                    sake_query = sake_query.join(
                        BrandFlavorTag, Sake.id == BrandFlavorTag.sake_id
                    ).filter(
                        BrandFlavorTag.flavor_tag_id == flavor_tag.id
                    )
            except Exception as e:
                logger.error(f"Error filtering by flavor tag: {str(e)}")
        
        # 味わいプロファイルでの絞り込み（指定がある場合）
        if flavor_direction and flavor_intensity:
            from models.flavor_chart import FlavorChart
            
            # 方向によってフィールドを決定
            flavor_mapping = {
                'elegant': {'field': 'f1', 'direction': 'high'},     # 華やか
                'heavy': {'field': 'f1', 'direction': 'low'},        # 重厚
                'rich': {'field': 'f2', 'direction': 'high'},        # 芳醇
                'mild': {'field': 'f2', 'direction': 'low'},         # 穏やか
                'full': {'field': 'f3', 'direction': 'high'},        # 濃醇
                'light': {'field': 'f3', 'direction': 'low'},        # 淡麗
                'sweet': {'field': 'f4', 'direction': 'low'},        # 甘口
                'dry': {'field': 'f4', 'direction': 'high'},         # 辛口
                'individual': {'field': 'f5', 'direction': 'high'},  # 個性
                'typical': {'field': 'f5', 'direction': 'low'},      # 特性
                'aged': {'field': 'f6', 'direction': 'high'},        # 熟成
                'fresh': {'field': 'f6', 'direction': 'low'}         # 若年
            }
            
            profile_info = flavor_mapping.get(flavor_direction, {})
            if profile_info:
                flavor_field = profile_info['field']
                is_high_direction = profile_info['direction'] == 'high'
                threshold = float(flavor_intensity) / 10  # 1-10のスケールを0-1に変換
                
                logger.info(f"Filtering by flavor direction: {flavor_direction}, field: {flavor_field}, high_direction: {is_high_direction}, threshold: {threshold}")
                
                # FlavorChartとJOIN
                sake_query = sake_query.join(
                    FlavorChart, Sake.id == FlavorChart.sake_id
                )
                
                # 方向に基づいてフィルタリング
                if is_high_direction:
                    # 高い値
                    sake_query = sake_query.filter(getattr(FlavorChart, flavor_field) >= threshold)
                else:
                    # 低い値
                    sake_query = sake_query.filter(getattr(FlavorChart, flavor_field) <= threshold)
        
        search_results = sake_query.order_by(Sake.created_at.desc()).all()
        
        # フレーバープロファイルの日本語名マッピング
        flavor_profiles = {
            '1': {'name': '華やか - 重厚', 'low': '重厚', 'high': '華やか'},
            '2': {'name': '芳醇 - 穏やか', 'low': '穏やか', 'high': '芳醇'},
            '3': {'name': '濃醇 - 淡麗', 'low': '淡麗', 'high': '濃醇'},
            '4': {'name': '甘口 - 辛口', 'low': '甘口', 'high': '辛口'},
            '5': {'name': '特性 - 個性', 'low': '特性', 'high': '個性'},
            '6': {'name': '若年 - 熟成', 'low': '若年', 'high': '熟成'},
        }
        
        # 検索パラメータの表示用データを構築
        selected_flavor_profile_display = None
        # 方向性の日本語表示名を定義
        flavor_direction_display = {
            'elegant': '華やか',
            'heavy': '重厚',
            'rich': '芳醇',
            'mild': '穏やか',
            'full': '濃醇',
            'light': '淡麗',
            'sweet': '甘口',
            'dry': '辛口',
            'individual': '個性的',
            'typical': '特性的',
            'aged': '熟成感',
            'fresh': '若々しさ'
        }
        
        if flavor_direction and flavor_intensity:
            direction_term = flavor_direction_display.get(flavor_direction, flavor_direction)
            intensity_level = int(flavor_intensity)
            selected_flavor_profile_display = {
                'direction': direction_term,
                'intensity': intensity_level,
                'direction_code': flavor_direction
            }
        
        return render_template(
            'search.html', 
            search_results=search_results,
            flavor_tags=flavor_tags,
            selected_flavor_tag=flavor_tag_id,
            query=query,
            flavor_profiles=flavor_profiles,
            selected_flavor_profile=selected_flavor_profile_display,
            flavor_profile=flavor_profile,
            flavor_direction=flavor_direction,
            flavor_intensity=flavor_intensity
        )
    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        flash('エラーが発生しました。検索条件を変更してお試しください。', 'error')
        # フレーバープロファイルの日本語名マッピング (エラー時)
        flavor_profiles = {
            '1': {'name': '華やか - 重厚', 'low': '重厚', 'high': '華やか'},
            '2': {'name': '芳醇 - 穏やか', 'low': '穏やか', 'high': '芳醇'},
            '3': {'name': '濃醇 - 淡麗', 'low': '淡麗', 'high': '濃醇'},
            '4': {'name': '甘口 - 辛口', 'low': '甘口', 'high': '辛口'},
            '5': {'name': '特性 - 個性', 'low': '特性', 'high': '個性'},
            '6': {'name': '若年 - 熟成', 'low': '若年', 'high': '熟成'},
        }
        
        return render_template('search.html', 
                             search_results=[], 
                             flavor_tags=[], 
                             flavor_profiles=flavor_profiles,
                             query='',
                             selected_flavor_tag='',
                             flavor_profile='',
                             flavor_direction='',
                             flavor_intensity='',
                             selected_flavor_profile=None)

@bp.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    try:
        logger.info(f"Fetching sake details for ID: {sake_id}")
        
        # 日本酒の基本情報とフレーバーチャートを取得（関連データを先読み）
        sake = db.session.query(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region),
                joinedload(Sake.flavor_chart)
            )\
            .filter(Sake.id == sake_id)\
            .first_or_404()

        logger.info(f"Found sake: {sake.name}")
        
        # フレーバータグを取得（get_flavor_tags()メソッドを利用する代わりに直接クエリ）
        from models.flavor_tag import FlavorTag
        from models.brand_flavor_tag import BrandFlavorTag
        
        flavor_tags = db.session.query(FlavorTag)\
            .join(BrandFlavorTag, FlavorTag.id == BrandFlavorTag.flavor_tag_id)\
            .filter(BrandFlavorTag.sake_id == sake_id)\
            .order_by(FlavorTag.name)\
            .all()
        
        logger.info(f"Found {len(flavor_tags)} flavor tags")
        
        # レビューを取得
        reviews = Review.query.filter_by(sake_id=sake_id)\
            .order_by(Review.created_at.desc())\
            .all()
            
        logger.info(f"Found {len(reviews)} reviews")

        return render_template('sake_detail.html', 
                              sake=sake, 
                              reviews=reviews,
                              flavor_tags=flavor_tags)
    except Exception as e:
        logger.error(f"Error in sake_detail route for ID {sake_id}: {str(e)}", exc_info=True)
        flash('日本酒の詳細情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

@bp.route('/regions')
def get_regions():
    try:
        # Add debug logging
        logger.debug("Fetching all regions")
        regions = Region.query.order_by(Region.name).all()
        logger.debug(f"Found {len(regions)} regions")

        # Convert to list of dictionaries
        result = [{
            'id': region.sakenowa_id,
            'name': region.name
        } for region in regions]

        logger.debug(f"Returning regions data: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_regions route: {str(e)}", exc_info=True)
        return jsonify({'error': 'エラーが発生しました'}), 500

@bp.route('/area_rankings/<string:region_id>')
def area_rankings(region_id):
    try:
        logger.info(f"Fetching area rankings for region ID: {region_id}")
        
        # 都道府県別ランキングを取得
        # カテゴリは「area_地域ID」の形式
        area_category = f'area_{region_id}'
        
        logger.info(f"Looking for rankings with category: {area_category}")
        
        area_rankings_query = db.session.query(
            Ranking, Sake, Brewery, Region
        ).join(
            Sake, Ranking.sake_id == Sake.id
        ).join(
            Brewery, Sake.brewery_id == Brewery.id
        ).join(
            Region, Brewery.region_id == Region.id
        ).filter(
            Ranking.category == area_category
        ).order_by(
            Ranking.rank
        ).limit(10)
        
        area_rankings_result = area_rankings_query.all()
        logger.info(f"Found {len(area_rankings_result)} area rankings for region {region_id}")
        
        # レスポンス用のデータを作成
        rankings_data = []
        for ranking, sake, brewery, region in area_rankings_result:
            rankings_data.append({
                'rank': ranking.rank,
                'score': ranking.score,
                'sake_id': sake.id,
                'sake_name': sake.name,
                'brewery_name': brewery.name,
                'region_name': region.name
            })
        
        return jsonify(rankings_data)
    except Exception as e:
        logger.error(f"Error in area_rankings route for region {region_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'エリアランキングの取得中にエラーが発生しました'}), 500

@bp.route('/flavor_tag/<string:flavor_tag_id>')
def flavor_tag_ranking(flavor_tag_id):
    try:
        from models.flavor_tag import FlavorTag
        from models.brand_flavor_tag import BrandFlavorTag
        
        logger.info(f"Fetching ranking for flavor tag ID: {flavor_tag_id}")
        
        # フレーバータグの情報を取得
        flavor_tag = FlavorTag.query.filter_by(sakenowa_id=flavor_tag_id).first_or_404()
        logger.info(f"Found flavor tag: {flavor_tag.name}")
        
        # このフレーバータグを持つ日本酒を取得
        sakes_with_tag_query = db.session.query(
            Sake, Brewery, Region, BrandFlavorTag
        ).join(
            BrandFlavorTag, Sake.id == BrandFlavorTag.sake_id
        ).join(
            Brewery, Sake.brewery_id == Brewery.id
        ).join(
            Region, Brewery.region_id == Region.id
        ).filter(
            BrandFlavorTag.flavor_tag_id == flavor_tag.id
        ).order_by(
            BrandFlavorTag.created_at.desc()
        ).limit(20)
        
        sakes_with_tag = sakes_with_tag_query.all()
        logger.info(f"Found {len(sakes_with_tag)} sakes with flavor tag '{flavor_tag.name}'")
        
        # 関連するフレーバータグ（その他のタグ）を取得
        flavor_tags = FlavorTag.query.order_by(FlavorTag.name).all()
        
        return render_template(
            'flavor_tag_ranking.html',
            flavor_tag=flavor_tag,
            sakes_with_tag=sakes_with_tag,
            flavor_tags=flavor_tags
        )
    except Exception as e:
        logger.error(f"Error in flavor_tag_ranking route for tag {flavor_tag_id}: {str(e)}", exc_info=True)
        flash('フレーバータグの取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))