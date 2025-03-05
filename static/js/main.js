document.addEventListener('DOMContentLoaded', function() {
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
                        const decimal = score - fullStars;
                        let stars = '';

                        for (let i = 0; i < 5; i++) {
                            if (i < fullStars) {
                                stars += '<i class="bi bi-star-fill"></i>';
                            } else if (i === fullStars && decimal >= 0.1) {
                                stars += '<i class="bi bi-star-half"></i>';
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
                                                <span class="text-warning">
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
});