document.addEventListener('DOMContentLoaded', function() {
    // ミニフレーバーチャートの初期化（検索結果ページ）
    const miniCharts = document.querySelectorAll('.flavor-chart-mini');
    if (miniCharts.length > 0) {
        miniCharts.forEach(chart => {
            const flavorData = {
                f1: parseFloat(chart.getAttribute('data-f1') || 0),
                f2: parseFloat(chart.getAttribute('data-f2') || 0),
                f3: parseFloat(chart.getAttribute('data-f3') || 0),
                f4: parseFloat(chart.getAttribute('data-f4') || 0),
                f5: parseFloat(chart.getAttribute('data-f5') || 0),
                f6: parseFloat(chart.getAttribute('data-f6') || 0)
            };
            createFlavorChartMini(chart, flavorData);
        });
    }
    
    // メインフレーバーチャートの初期化（詳細ページ）
    const flavorChartElement = document.getElementById('flavor-chart');
    if (flavorChartElement) {
        const flavorData = {
            f1: parseFloat(flavorChartElement.getAttribute('data-f1') || 0),
            f2: parseFloat(flavorChartElement.getAttribute('data-f2') || 0),
            f3: parseFloat(flavorChartElement.getAttribute('data-f3') || 0),
            f4: parseFloat(flavorChartElement.getAttribute('data-f4') || 0),
            f5: parseFloat(flavorChartElement.getAttribute('data-f5') || 0),
            f6: parseFloat(flavorChartElement.getAttribute('data-f6') || 0)
        };
        createFlavorChart('flavor-chart', flavorData);
    }
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Load regions into dropdown
    const regionSelect = document.getElementById('region-select');
    if (regionSelect) {
        fetch('/regions')
            .then(response => response.json())
            .then(regions => {
                regions.forEach(region => {
                    const option = document.createElement('option');
                    option.value = region.id;  // sakenowa_idを使用
                    option.textContent = region.name;
                    regionSelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading regions:', error));

        // Handle region selection
        regionSelect.addEventListener('change', function() {
            const selectedRegion = this.value;
            const areaRankingsContainer = document.getElementById('area-rankings');

            if (!selectedRegion) {
                areaRankingsContainer.innerHTML = '';
                return;
            }

            console.log('Fetching rankings for region:', selectedRegion);
            fetch(`/area_rankings/${selectedRegion}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(rankings => {
                    console.log('Received rankings:', rankings);
                    if (rankings.error) {
                        throw new Error(rankings.error);
                    }
                    let html = '';
                    rankings.forEach(ranking => {
                        const score = ranking.score;
                        const fullStars = Math.floor(score);
                        let stars = '';

                        for (let i = 0; i < 5; i++) {
                            if (i < fullStars) {
                                stars += '<i class="bi bi-star-fill"></i>';
                            } else {
                                stars += '<i class="bi bi-star"></i>';
                            }
                        }

                        html += `
                            <div class="col-md-6 col-lg-4">
                                <a href="/sake/${ranking.sake_id}" class="card-link text-decoration-none">
                                    <div class="card h-100 hover-card">
                                        <div class="card-body">
                                            <h5 class="card-title text-dark">
                                                第${ranking.rank}位: ${ranking.sake_name}
                                            </h5>
                                            <p class="card-text">
                                                <small class="text-muted">
                                                    ${ranking.brewery_name} (${ranking.region_name})
                                                </small>
                                            </p>
                                            <p class="card-text">
                                                <span class="rating">
                                                    ${stars}
                                                </span>
                                                <small class="text-muted ms-2">${ranking.score.toFixed(1)}</small>
                                            </p>
                                        </div>
                                    </div>
                                </a>
                            </div>
                        `;
                    });
                    areaRankingsContainer.innerHTML = rankings.length ? html : '<div class="col"><p class="text-muted">この地域のランキングデータはありません。</p></div>';
                })
                .catch(error => {
                    console.error('Error loading area rankings:', error);
                    areaRankingsContainer.innerHTML = '<div class="col"><p class="text-danger">ランキングの読み込み中にエラーが発生しました。</p></div>';
                });
        });
    }

    // Star rating functionality
    const ratingInputs = document.querySelectorAll('.rating-input');
    const ratingStars = document.querySelectorAll('.rating-star');

    ratingStars.forEach((star, index) => {
        star.addEventListener('click', () => {
            const rating = index + 1;
            updateRatingDisplay(rating);
            document.getElementById('rating-value').value = rating;
        });
    });

    function updateRatingDisplay(rating) {
        ratingStars.forEach((star, index) => {
            star.classList.toggle('text-warning', index < rating);
        });
    }

    // フレーバースライダーの値更新
    const flavorRanges = document.querySelectorAll('.flavor-range');
    flavorRanges.forEach(range => {
        const valueDisplay = range.parentElement.querySelector('.current-value');
        range.addEventListener('input', () => {
            valueDisplay.textContent = range.value;
        });
    });

    // Review submission
    const reviewForm = document.getElementById('review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const sakeId = reviewForm.dataset.sakeId;
            const rating = document.getElementById('rating-value').value;
            const comment = document.getElementById('review-comment').value;

            // f2の値を平均化して送信
            const f2_aroma = parseFloat(document.getElementById('f2_aroma').value) / 10;
            const f2_temp = parseFloat(document.getElementById('f2_temp').value) / 10;
            const f2_combined = (f2_aroma + f2_temp) / 2;

            // フレーバー値の取得（0-10のレンジを0-1に変換）
            const flavorData = {
                f1: document.getElementById('f1').value / 10,
                f2: f2_combined, // 平均値を使用
                f3: document.getElementById('f3').value / 10,
                f4: document.getElementById('f4').value / 10,
                f5: document.getElementById('f5').value / 10,
                f6: document.getElementById('f6').value / 10
            };

            try {
                const response = await fetch(`/review/${sakeId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        rating,
                        comment,
                        ...flavorData
                    }),
                });

                if (response.ok) {
                    location.reload();
                } else {
                    const data = await response.json();
                    alert(data.error || 'レビューの投稿中にエラーが発生しました');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('レビューの投稿中にエラーが発生しました');
            }
        });
    }

    // Search form
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = document.getElementById('search-input').value;
            const flavor = document.getElementById('flavor-select').value;
            window.location.href = `/search?q=${encodeURIComponent(query)}&flavor=${encodeURIComponent(flavor)}`;
        });
    }

    // メインのフレーバーチャートは既に初期化済み（DOMContentLoadedイベントのはじめで実装済み）
    
    // 重複コードのため削除（DOMContentLoadedイベントのはじめで既に実装済み）
});


// ミニ版フレーバーチャート作成関数（検索結果一覧用）
function createFlavorChartMini(chartContainer, flavorData) {
  if (!chartContainer) return;

  const width = 150;
  const height = 150;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2.5;

  // 六角形の頂点の角度を計算（360度を6分割）
  const angles = Array.from({ length: 6 }, (_, i) => i * Math.PI / 3 - Math.PI / 2);

  // SVG要素を作成
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'flavor-chart-svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');

  // 4段階の目盛り線を描画
  for (let scale = 0.25; scale <= 1; scale += 0.25) {
    const scalePoints = angles.map(angle => {
      return `${centerX + radius * scale * Math.cos(angle)},${centerY + radius * scale * Math.sin(angle)}`;
    }).join(' ');
    const scaleLine = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    scaleLine.setAttribute('points', scalePoints);
    scaleLine.setAttribute('fill', 'none');
    scaleLine.setAttribute('stroke', '#ddd');
    scaleLine.setAttribute('stroke-width', '0.5');
    svg.appendChild(scaleLine);
  }

  // データの六角形の頂点座標を計算
  const dataPoints = angles.map((angle, i) => {
    const value = flavorData[`f${i + 1}`] || 0;
    return `${centerX + radius * value * Math.cos(angle)},${centerY + radius * value * Math.sin(angle)}`;
  }).join(' ');

  // データの六角形
  const data = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  data.setAttribute('points', dataPoints);
  data.setAttribute('fill', 'rgba(140, 147, 123, 0.6)');
  data.setAttribute('stroke', '#8c937b');
  data.setAttribute('stroke-width', '1');
  svg.appendChild(data);

  // 中心から各頂点への線を描画
  angles.forEach(angle => {
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', centerX);
    line.setAttribute('y1', centerY);
    line.setAttribute('x2', x);
    line.setAttribute('y2', y);
    line.setAttribute('stroke', '#8c937b');
    line.setAttribute('stroke-width', '0.3');
    svg.appendChild(line);
  });

  // コンテナをクリアして新しいSVGを追加
  chartContainer.innerHTML = '';
  chartContainer.appendChild(svg);
}

function createFlavorChart(containerId, flavorData) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const width = 300;
  const height = 300;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2.5;

  // 六角形の頂点の角度を計算（360度を6分割）
  const angles = Array.from({ length: 6 }, (_, i) => i * Math.PI / 3 - Math.PI / 2);

  // SVG要素を作成
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'flavor-chart');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  // 4段階の目盛り線を描画
  for (let scale = 0.25; scale <= 1; scale += 0.25) {
    const scalePoints = angles.map(angle => {
      return `${centerX + radius * scale * Math.cos(angle)},${centerY + radius * scale * Math.sin(angle)}`;
    }).join(' ');
    const scaleLine = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    scaleLine.setAttribute('points', scalePoints);
    scaleLine.setAttribute('class', 'scale-line');
    svg.appendChild(scaleLine);
  }

  // データの六角形の頂点座標を計算
  const dataPoints = angles.map((angle, i) => {
    const value = flavorData[`f${i + 1}`] || 0;
    return `${centerX + radius * value * Math.cos(angle)},${centerY + radius * value * Math.sin(angle)}`;
  }).join(' ');

  // データの六角形
  const data = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  data.setAttribute('points', dataPoints);
  data.setAttribute('class', 'data');
  // 必要に応じて fill や stroke の属性を設定してください
  svg.appendChild(data);

  // 中心から各頂点への線を描画（データの六角形の後に描画して上に表示）
  angles.forEach(angle => {
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', centerX);
    line.setAttribute('y1', centerY);
    line.setAttribute('x2', x);
    line.setAttribute('y2', y);
    line.setAttribute('class', 'center-line'); // CSSでスタイル調整可能
    // 中心線が確実に表示されるように stroke 属性を指定
    line.setAttribute('stroke', '#8c937b');//fill: rgba(140, 147, 123, 0.6)
    line.setAttribute('stroke-width', '0.3');
    svg.appendChild(line);
  });

  // コンテナをクリアして新しいSVGを追加
  container.innerHTML = '';
  container.appendChild(svg);

  // ラベルを追加
  const labels = ['華やか', '芳醇', '重厚', '穏やか', 'ドライ', '軽快'];
  labels.forEach((label, i) => {
    const div = document.createElement('div');
    div.className = `flavor-label f${i + 1}`;
    div.textContent = label;

    // ラベルの調整
    // インデックス1（芳醇）と2（重厚）は右へ、インデックス4（ドライ）と5（軽快）は左へ移動
    if (i === 1 || i === 2) {
      div.style.transform = 'translateX(20px)';
    } else if (i === 4 || i === 5) {
      div.style.transform = 'translateX(-20px)';
    }
    container.appendChild(div);
  });
}
